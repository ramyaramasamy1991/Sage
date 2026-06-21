"""Thin wrapper around the Anthropic Bedrock client."""

from __future__ import annotations

from anthropic import AnthropicBedrock

from .config import settings

_client: AnthropicBedrock | None = None


def get_client() -> AnthropicBedrock:
    """Return a shared AnthropicBedrock client.

    Credentials are resolved by boto3's standard chain (env vars, shared
    profile, IAM role), so nothing is hard-coded here.
    """
    global _client
    if _client is None:
        _client = AnthropicBedrock(aws_region=settings.aws_region)
    return _client
