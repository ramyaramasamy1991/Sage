"""Retrieval against a Bedrock Knowledge Base."""

from __future__ import annotations

from dataclasses import dataclass

import boto3

from .config import settings


@dataclass
class Passage:
    text: str
    source: str
    score: float | None


_client = None


def _agent_runtime():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-agent-runtime", region_name=settings.aws_region)
    return _client


def _source_label(result: dict) -> str:
    """Best-effort human-readable origin for a retrieved passage."""
    loc = result.get("location", {}) or {}
    loc_type = loc.get("type", "")
    # Each location type nests its uri/id under a type-specific key.
    for key in ("s3Location", "webLocation", "confluenceLocation",
                "salesforceLocation", "sharePointLocation", "customDocumentLocation"):
        sub = loc.get(key)
        if isinstance(sub, dict):
            return sub.get("uri") or sub.get("url") or sub.get("id") or loc_type
    return loc_type or "knowledge-base"


def retrieve(query: str) -> list[Passage]:
    """Return the top-k passages for `query`, or [] if RAG is not configured."""
    if not settings.rag_enabled:
        return []

    resp = _agent_runtime().retrieve(
        knowledgeBaseId=settings.knowledge_base_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": settings.rag_top_k}
        },
    )

    passages: list[Passage] = []
    for result in resp.get("retrievalResults", []):
        text = (result.get("content", {}) or {}).get("text", "").strip()
        if not text:
            continue
        score = result.get("score")
        if score is not None and score < settings.rag_min_score:
            continue
        passages.append(
            Passage(text=text, source=_source_label(result), score=score)
        )
    return passages
