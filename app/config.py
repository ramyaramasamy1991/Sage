"""Application settings, loaded from environment variables / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

# Models offered in the UI picker. `id` must be a valid Bedrock inference-profile
# id for your account/region (confirm in the Bedrock console).
MODEL_CHOICES: list[dict] = [
    {"id": "us.anthropic.claude-opus-4-8", "label": "Claude Opus 4.8"},
    {"id": "us.anthropic.claude-sonnet-4-6", "label": "Claude Sonnet 4.6"},
    {"id": "us.anthropic.claude-haiku-4-5", "label": "Claude Haiku 4.5"},
]

# Approximate list prices (USD per 1M tokens) keyed by a substring of the model
# id, used only for rough cost logging. Bedrock pricing may differ slightly.
PRICES: dict[str, tuple[float, float]] = {
    "opus": (5.0, 25.0),
    "sonnet": (3.0, 15.0),
    "haiku": (1.0, 5.0),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # AWS / Bedrock
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "us.anthropic.claude-opus-4-8"

    # RAG / Knowledge Base
    knowledge_base_id: str = ""
    rag_top_k: int = 5
    rag_min_score: float = 0.0  # drop passages below this relevance score

    # Generation
    max_tokens: int = 4096
    enable_thinking: bool = False

    # Auth — if set, /api/chat and /api/reset require this key via X-API-Key.
    api_key: str = ""

    # Persistence — set a redis url to share session memory across workers /
    # survive restarts; empty falls back to in-process memory.
    redis_url: str = ""
    max_turns: int = 12  # turns kept per session (a turn = user + assistant)

    # App
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"

    @property
    def rag_enabled(self) -> bool:
        return bool(self.knowledge_base_id.strip())

    @property
    def auth_required(self) -> bool:
        return bool(self.api_key.strip())

    def resolve_model(self, requested: str | None) -> str:
        """Return a valid model id, honoring the picker allow-list."""
        if requested and any(m["id"] == requested for m in MODEL_CHOICES):
            return requested
        return self.bedrock_model_id

    def price_for(self, model_id: str) -> tuple[float, float]:
        for key, price in PRICES.items():
            if key in model_id:
                return price
        return (0.0, 0.0)


settings = Settings()
