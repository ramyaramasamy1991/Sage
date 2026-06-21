"""Map low-level Bedrock / AWS exceptions to friendly, actionable messages."""

from __future__ import annotations


def friendly_error(exc: Exception) -> str:
    name = type(exc).__name__
    low = str(exc).lower()

    if name == "RateLimitError" or "throttl" in low or "too many requests" in low:
        return "Sage is being rate-limited by Bedrock. Please retry in a moment."

    if (
        "accessdenied" in low
        or "not authorized" in low
        or "don't have access" in low
        or "access to the model" in low
        or "you don't have access" in low
    ):
        return (
            "Access denied. Make sure the Claude model is enabled in Bedrock → "
            "Model access, and that your IAM principal allows "
            "bedrock:InvokeModelWithResponseStream."
        )

    if (
        "inference profile" in low
        or "on-demand throughput" in low
        or "invalid model" in low
        or "could not be found" in low
        or ("model" in low and "not" in low and "support" in low)
    ):
        return (
            "Model id not usable. Newer Claude models need a cross-region "
            "inference-profile id like 'us.anthropic.claude-opus-4-8'. "
            "Check BEDROCK_MODEL_ID and AWS_REGION."
        )

    if (
        "unable to locate credentials" in low
        or "expired" in low
        or "security token" in low
        or "credential" in low
    ):
        return (
            "AWS credentials are missing or expired. Run `aws configure` or "
            "refresh your session, then try again."
        )

    if "region" in low or "endpoint" in low:
        return (
            "Couldn't reach Bedrock. Verify AWS_REGION is a region where Bedrock "
            "and Claude are enabled."
        )

    return f"Unexpected error from Bedrock ({name}): {exc}"
