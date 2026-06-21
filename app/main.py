"""FastAPI app: serves the chat UI and a streaming chat endpoint."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .chat import reset_session, stream_reply
from .config import MODEL_CHOICES, settings

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Sage", version="0.1.0")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Gate protected endpoints when API_KEY is configured."""
    if settings.auth_required and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class ChatRequest(BaseModel):
    session_id: str
    message: str
    model: str | None = None
    enable_thinking: bool | None = None


class ResetRequest(BaseModel):
    session_id: str


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": settings.bedrock_model_id}


@app.get("/api/config")
def config() -> dict:
    """Public config the UI needs to render controls."""
    return {
        "models": MODEL_CHOICES,
        "default_model": settings.bedrock_model_id,
        "thinking_default": settings.enable_thinking,
        "rag_enabled": settings.rag_enabled,
        "auth_required": settings.auth_required,
    }


@app.post("/api/chat", dependencies=[Depends(require_api_key)])
def chat(req: ChatRequest) -> StreamingResponse:
    def event_stream():
        for event in stream_reply(
            req.session_id, req.message, req.model, req.enable_thinking
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/reset", dependencies=[Depends(require_api_key)])
def reset(req: ResetRequest) -> dict:
    reset_session(req.session_id)
    return {"status": "reset"}
