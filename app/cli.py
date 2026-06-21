"""Terminal chatbot for Sage — streams tokens to stdout over stdio.

Reuses the same retrieval + generation pipeline as the web app.

Usage:
    python -m app.cli
    python -m app.cli --model us.anthropic.claude-sonnet-4-6 --thinking
"""

from __future__ import annotations

import argparse
import sys
import uuid

from .chat import reset_session, stream_reply
from .config import settings

HELP = "Commands:  /reset  clear memory   ·   /exit (or Ctrl-D)  quit"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sage terminal chatbot")
    parser.add_argument("--model", default=None, help="Bedrock model id override")
    parser.add_argument(
        "--thinking", action="store_true", help="Enable adaptive thinking"
    )
    args = parser.parse_args(argv)

    session_id = str(uuid.uuid4())
    model = settings.resolve_model(args.model)
    print(f"Sage  model={model}  rag={'on' if settings.rag_enabled else 'off'}")
    print(HELP + "\n")

    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not message:
            continue
        if message == "/exit":
            break
        if message == "/reset":
            reset_session(session_id)
            print("(memory cleared)\n")
            continue

        sources: list[dict] = []
        print("Sage> ", end="", flush=True)
        for event in stream_reply(
            session_id, message, model=args.model, enable_thinking=args.thinking
        ):
            if event["type"] == "delta":
                print(event["text"], end="", flush=True)
            elif event["type"] == "sources":
                sources = event["sources"]
            elif event["type"] == "error":
                print(f"\n[error] {event['message']}", end="")
            elif event["type"] == "done":
                u = event.get("usage", {})
                if u:
                    tag = f"  [{u['input_tokens']}+{u['output_tokens']} tok, ~${u['est_cost_usd']}]"
                    print(tag, end="", file=sys.stderr)
        if sources:
            labels = ", ".join(s["source"] for s in sources)
            print(f"\n  sources: {labels}", file=sys.stderr)
        print("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
