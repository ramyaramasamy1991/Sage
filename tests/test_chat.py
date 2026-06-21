from app import chat
from app.rag import Passage


def test_stream_reply_basic(monkeypatch, fake_client):
    monkeypatch.setattr(chat, "retrieve", lambda q: [])
    monkeypatch.setattr(chat, "get_client", lambda: fake_client())

    events = list(chat.stream_reply("s1", "hi"))
    types = [e["type"] for e in events]

    assert types[-1] == "done"
    text = "".join(e["text"] for e in events if e["type"] == "delta")
    assert text == "Hello"
    assert events[-1]["usage"]["input_tokens"] == 10

    # The turn is persisted to memory.
    hist = chat.get_store().history("s1")
    assert hist[-1] == {"role": "assistant", "content": "Hello"}


def test_stream_reply_emits_sources(monkeypatch, fake_client):
    passages = [Passage(text="ctx", source="s3://bucket/doc.txt", score=0.9)]
    monkeypatch.setattr(chat, "retrieve", lambda q: passages)
    monkeypatch.setattr(chat, "get_client", lambda: fake_client())

    events = list(chat.stream_reply("s2", "hi"))
    sources_events = [e for e in events if e["type"] == "sources"]
    assert sources_events
    assert sources_events[0]["sources"][0]["source"] == "s3://bucket/doc.txt"


def test_context_injected_into_system(monkeypatch):
    passages = [Passage(text="THE ANSWER IS 42", source="doc", score=1.0)]
    monkeypatch.setattr(chat, "retrieve", lambda q: passages)
    client = None

    def make_client():
        nonlocal client
        from tests.conftest import FakeClient

        client = FakeClient()
        return client

    monkeypatch.setattr(chat, "get_client", make_client)
    list(chat.stream_reply("s3", "hi"))

    system_blocks = client.messages.last_kwargs["system"]
    assert any("THE ANSWER IS 42" in b["text"] for b in system_blocks)


def test_error_is_reported(monkeypatch):
    monkeypatch.setattr(chat, "retrieve", lambda q: [])

    def boom():
        raise RuntimeError("AccessDeniedException: no model access")

    monkeypatch.setattr(chat, "get_client", boom)
    events = list(chat.stream_reply("s4", "hi"))
    assert events[-1]["type"] == "error"
    assert "Access denied" in events[-1]["message"]
    # Failed turn is not persisted.
    assert chat.get_store().history("s4") == []


def test_model_allowlist(monkeypatch, fake_client):
    monkeypatch.setattr(chat, "retrieve", lambda q: [])
    client = fake_client()
    monkeypatch.setattr(chat, "get_client", lambda: client)

    list(chat.stream_reply("s5", "hi", model="evil-model"))
    # Unknown model falls back to the configured default, not the injected one.
    assert client.messages.last_kwargs["model"] != "evil-model"
