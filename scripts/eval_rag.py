"""Smoke-test Knowledge Base retrieval quality.

Reads scripts/evalset.json — a list of {"question", "expect_sources"} where
expect_sources are substrings expected to appear in a retrieved passage's
source label. Requires live AWS creds + a configured KNOWLEDGE_BASE_ID.

Usage:  python -m scripts.eval_rag
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.rag import retrieve

EVALSET = Path(__file__).resolve().parent / "evalset.json"


def main() -> None:
    if not settings.rag_enabled:
        raise SystemExit("KNOWLEDGE_BASE_ID is not set — nothing to evaluate.")

    cases = json.loads(EVALSET.read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        question = case["question"]
        expected = case.get("expect_sources", [])
        passages = retrieve(question)
        sources = [p.source for p in passages]

        hit = all(
            any(exp in src for src in sources) for exp in expected
        ) if expected else bool(passages)

        passed += hit
        mark = "PASS" if hit else "FAIL"
        print(f"[{mark}] {question}")
        print(f"        retrieved: {sources or '(none)'}")

    print(f"\n{passed}/{len(cases)} cases passed")


if __name__ == "__main__":
    main()
