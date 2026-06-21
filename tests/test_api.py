from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_config_lists_models():
    data = client.get("/api/config").json()
    assert len(data["models"]) >= 1
    assert "default_model" in data


def test_chat_streams(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")  # no auth
    monkeypatch.setattr(
        main, "stream_reply",
        lambda *a, **k: iter([{"type": "delta", "text": "hi"}, {"type": "done"}]),
    )
    r = client.post("/api/chat", json={"session_id": "s", "message": "hi"})
    assert r.status_code == 200
    assert "data:" in r.text


def test_auth_enforced(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    monkeypatch.setattr(main, "stream_reply", lambda *a, **k: iter([{"type": "done"}]))

    assert client.post("/api/chat", json={"session_id": "s", "message": "hi"}).status_code == 401

    ok = client.post(
        "/api/chat",
        json={"session_id": "s", "message": "hi"},
        headers={"X-API-Key": "secret"},
    )
    assert ok.status_code == 200
