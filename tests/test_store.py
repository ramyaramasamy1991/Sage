from app.store import InMemoryStore


def test_append_and_history():
    s = InMemoryStore(maxlen=4)
    s.append("a", {"role": "user", "content": "hi"})
    s.append("a", {"role": "assistant", "content": "hello"})
    hist = s.history("a")
    assert [m["role"] for m in hist] == ["user", "assistant"]


def test_trims_to_maxlen():
    s = InMemoryStore(maxlen=2)
    for i in range(5):
        s.append("a", {"role": "user", "content": str(i)})
    hist = s.history("a")
    assert len(hist) == 2
    assert hist[-1]["content"] == "4"


def test_reset():
    s = InMemoryStore(maxlen=4)
    s.append("a", {"role": "user", "content": "hi"})
    s.reset("a")
    assert s.history("a") == []


def test_sessions_isolated():
    s = InMemoryStore(maxlen=4)
    s.append("a", {"role": "user", "content": "x"})
    assert s.history("b") == []
