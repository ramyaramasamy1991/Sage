"""Shared test fixtures and Bedrock fakes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import store


@pytest.fixture(autouse=True)
def fresh_store():
    """Give each test an isolated in-memory session store."""
    store._store = store.InMemoryStore(maxlen=10)
    yield
    store._store = None


class FakeStream:
    """Mimics anthropic's streaming context manager."""

    def __init__(self, chunks, usage):
        self._chunks = chunks
        self._usage = usage

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        return iter(self._chunks)

    def get_final_message(self):
        return SimpleNamespace(usage=self._usage)


class FakeMessages:
    def __init__(self, stream):
        self._stream = stream
        self.last_kwargs = None

    def stream(self, **kwargs):
        self.last_kwargs = kwargs
        return self._stream


class FakeClient:
    def __init__(self, chunks=("Hel", "lo"), input_tokens=10, output_tokens=5):
        usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
        self.messages = FakeMessages(FakeStream(list(chunks), usage))


@pytest.fixture
def fake_client():
    return FakeClient
