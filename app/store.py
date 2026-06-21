"""Conversation memory backends: in-process or Redis."""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque

from .config import settings

log = logging.getLogger("sage.store")

Message = dict[str, str]  # {"role": ..., "content": ...}


class InMemoryStore:
    """Per-process session memory. Lost on restart; not shared across workers."""

    def __init__(self, maxlen: int):
        self._maxlen = maxlen
        self._data: dict[str, deque] = defaultdict(lambda: deque(maxlen=maxlen))

    def history(self, session_id: str) -> list[Message]:
        return list(self._data[session_id])

    def append(self, session_id: str, *messages: Message) -> None:
        self._data[session_id].extend(messages)

    def reset(self, session_id: str) -> None:
        self._data.pop(session_id, None)


class RedisStore:
    """Session memory in Redis: one list per session, trimmed to maxlen."""

    def __init__(self, url: str, maxlen: int):
        import redis  # imported lazily so redis is optional

        self._r = redis.Redis.from_url(url, decode_responses=True)
        self._maxlen = maxlen

    def _key(self, session_id: str) -> str:
        return f"sage:session:{session_id}"

    def history(self, session_id: str) -> list[Message]:
        raw = self._r.lrange(self._key(session_id), 0, -1)
        return [json.loads(item) for item in raw]

    def append(self, session_id: str, *messages: Message) -> None:
        key = self._key(session_id)
        pipe = self._r.pipeline()
        for m in messages:
            pipe.rpush(key, json.dumps(m))
        pipe.ltrim(key, -self._maxlen, -1)
        pipe.expire(key, 60 * 60 * 24)  # 24h TTL
        pipe.execute()

    def reset(self, session_id: str) -> None:
        self._r.delete(self._key(session_id))


_store = None


def get_store():
    """Return the shared store, choosing Redis when REDIS_URL is set."""
    global _store
    if _store is None:
        maxlen = settings.max_turns * 2
        if settings.redis_url.strip():
            try:
                _store = RedisStore(settings.redis_url, maxlen)
                log.info("Using Redis session store")
            except Exception as exc:  # fall back rather than crash on boot
                log.warning("Redis unavailable (%s); using in-memory store", exc)
                _store = InMemoryStore(maxlen)
        else:
            _store = InMemoryStore(maxlen)
    return _store
