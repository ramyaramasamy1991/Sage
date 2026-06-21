"""Chat orchestration: retrieve context, build the prompt, stream the answer."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from .bedrock_client import get_client
from .config import settings
from .errors import friendly_error
from .rag import Passage, retrieve
from .store import get_store

log = logging.getLogger("sage.chat")

# Sage's persona / behavior. Kept first in the prompt so prompt caching can
# reuse it across turns.
SYSTEM_PROMPT = (
    "You are Sage, a knowledgeable and concise AI assistant. "
    "Answer clearly and helpfully, using Markdown for structure when useful. "
    "When the user's question relates to the provided context, ground your "
    "answer in it and cite the source labels in square brackets, e.g. "
    "[source: ...]. If the context does not contain the answer, say so plainly "
    "and answer from general knowledge only if you are confident — never invent "
    "facts or citations."
)


def _context_block(passages: list[Passage]) -> str:
    return "\n\n".join(
        f"[{i}] (source: {p.source})\n{p.text}" for i, p in enumerate(passages, 1)
    )


def _build_system(passages: list[Passage]) -> list[dict]:
    blocks = [{"type": "text", "text": SYSTEM_PROMPT}]
    if passages:
        blocks.append(
            {
                "type": "text",
                "text": "Retrieved context for the current question:\n\n"
                + _context_block(passages),
            }
        )
    return blocks


def _estimate_cost(model_id: str, usage) -> float:
    in_price, out_price = settings.price_for(model_id)
    return (
        (usage.input_tokens or 0) * in_price
        + (usage.output_tokens or 0) * out_price
    ) / 1_000_000


def stream_reply(
    session_id: str,
    user_message: str,
    model: str | None = None,
    enable_thinking: bool | None = None,
) -> Iterator[dict]:
    """Yield events for a single user turn.

    Event shapes:
      {"type": "sources", "sources": [...]}
      {"type": "delta", "text": "..."}
      {"type": "done", "usage": {...}}
      {"type": "error", "message": "..."}
    """
    store = get_store()
    model_id = settings.resolve_model(model)
    thinking = settings.enable_thinking if enable_thinking is None else enable_thinking

    try:
        passages = retrieve(user_message)
    except Exception as exc:  # retrieval failure shouldn't kill the chat
        log.warning("Retrieval failed: %s", exc)
        passages = []

    if passages:
        yield {
            "type": "sources",
            "sources": [{"source": p.source, "score": p.score} for p in passages],
        }

    messages = store.history(session_id) + [
        {"role": "user", "content": user_message}
    ]

    kwargs: dict = {
        "model": model_id,
        "max_tokens": settings.max_tokens,
        "system": _build_system(passages),
        "messages": messages,
    }
    if thinking:
        kwargs["thinking"] = {"type": "adaptive"}

    answer_parts: list[str] = []
    try:
        client = get_client()
        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                answer_parts.append(text)
                yield {"type": "delta", "text": text}
            final = stream.get_final_message()
    except Exception as exc:
        log.exception("Generation failed")
        yield {"type": "error", "message": friendly_error(exc)}
        return

    answer = "".join(answer_parts)
    store.append(
        session_id,
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": answer},
    )

    usage = final.usage
    cost = _estimate_cost(model_id, usage)
    log.info(
        "session=%s model=%s in=%s out=%s est_cost=$%.4f",
        session_id, model_id, usage.input_tokens, usage.output_tokens, cost,
    )
    yield {
        "type": "done",
        "usage": {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "est_cost_usd": round(cost, 4),
            "model": model_id,
        },
    }


def reset_session(session_id: str) -> None:
    get_store().reset(session_id)
