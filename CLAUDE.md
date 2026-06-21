# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Sage is a chatbot on **Amazon Bedrock** with **Claude** models: a FastAPI
backend with a streaming web chat UI (and a CLI), plus optional RAG over a
Bedrock Knowledge Base.

## Commands

This is Windows. The bare `python.exe` on PATH is the Windows Store stub and
won't run — use the `py` launcher or the project venv (`.venv\Scripts\...`).

```powershell
# Setup
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
copy .env.example .env            # then edit AWS_REGION / BEDROCK_MODEL_ID / KNOWLEDGE_BASE_ID

# Run the web app (http://127.0.0.1:8000)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Run the CLI
.\.venv\Scripts\python.exe -m app.cli [--model <id>] [--thinking]

# Tests (mock Bedrock — no AWS needed)
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest tests/test_chat.py::test_error_is_reported   # single test

# RAG retrieval eval (needs live AWS + KNOWLEDGE_BASE_ID)
.\.venv\Scripts\python.exe -m scripts.eval_rag

# Regenerate the architecture PNG from docs/architecture.svg layout
.\.venv\Scripts\python.exe docs/render_png.py

# Docker (app + Redis)
docker compose up --build
```

There is no linter configured.

## Architecture

The core is **transport-agnostic orchestration**. `app/chat.py:stream_reply()`
is a generator that yields plain event dicts — `{"type": "sources"|"delta"|
"done"|"error", ...}`. Two frontends consume the same generator:

- `app/main.py` frames each event as a **Server-Sent Event** (`/api/chat`).
- `app/cli.py` prints deltas to **stdout**.

So new frontends (e.g. a Slack bot) should consume `stream_reply()` rather than
re-implementing the pipeline. There are **two streaming hops**: Bedrock→server
over HTTPS (the Anthropic SDK's `messages.stream()`), then server→client over
SSE or stdio.

**Generation vs. retrieval use different SDKs on purpose:**
- Generation: the Anthropic SDK's `AnthropicBedrock` client (`app/bedrock_client.py`).
- Retrieval: boto3 `bedrock-agent-runtime.retrieve` (`app/rag.py`) — Knowledge
  Bases aren't in the Anthropic SDK.

RAG is **retrieve-then-generate** (not Bedrock's `retrieve_and_generate`): `chat.py`
fetches passages, injects them as a second `system` block, and streams Claude's
answer itself — so the prompt, citation format, and streaming stay under app
control. If `KNOWLEDGE_BASE_ID` is unset, `retrieve()` returns `[]` and the bot
answers without RAG.

**Session memory** is pluggable via `app/store.py`: `InMemoryStore` by default,
`RedisStore` when `REDIS_URL` is set (with automatic fallback). In-memory is
per-process, so multi-instance deploys need Redis. A `session_id` keys each
conversation; the web UI uses one per sidebar chat (persisted in browser
localStorage), so chat history lives in two places — the browser (for re-render)
and the backend store (for model context).

**Config** is a single pydantic-settings singleton (`app/config.py:settings`),
loaded from `.env`. It also holds `MODEL_CHOICES` (the UI picker allow-list) and
`PRICES` (approximate, for cost logging). Per-request model overrides are
validated against `MODEL_CHOICES` in `settings.resolve_model()` so a client
can't inject an arbitrary model id. `app/errors.py:friendly_error()` maps raw
Bedrock/AWS exceptions to actionable messages surfaced to the user.

See `ARCHITECTURE.md` for diagrams.

## Bedrock specifics

- `BEDROCK_MODEL_ID` must be a **cross-region inference-profile** id (note the
  `us.` prefix, e.g. `us.anthropic.claude-opus-4-8`), not a bare model id —
  confirm the exact id in the Bedrock console. Wrong ids surface via
  `errors.py` as an inference-profile message.
- Adaptive thinking is off by default (latency); `ENABLE_THINKING` /
  the UI toggle / `--thinking` turns it on (`thinking={"type": "adaptive"}`).
- Bedrock does **not** support Anthropic server-side tools or refusal
  fallbacks — don't add those code paths here.

## Testing notes

Tests mock Bedrock and retrieval (see `tests/conftest.py`'s `FakeClient` /
`fresh_store` fixture) so the suite runs with no AWS credentials. When adding
features that call Bedrock, follow that pattern — monkeypatch `chat.get_client`
and `chat.retrieve` rather than hitting the network.

## Status

Not yet run against live Bedrock — pending AWS credentials. All verification so
far is via the mocked test suite.
