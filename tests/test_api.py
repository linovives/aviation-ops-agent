from fastapi.testclient import TestClient
from api import main


def _fake_invoke_factory(captured):
    def fake_invoke(state):
        captured.append(list(state["messages"]))
        messages = list(state["messages"])
        messages.append({"role": "assistant", "content": f"reply to: {messages[-1]['content']}"})
        return {"messages": messages}

    return fake_invoke


def test_health_returns_ok():
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_creates_new_session_when_none_given(monkeypatch):
    main.sessions.clear()
    monkeypatch.setattr(main.agent_graph, "invoke", _fake_invoke_factory([]))
    client = TestClient(main.app)

    response = client.post("/chat", json={"message": "hola"})

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "reply to: hola"
    assert body["session_id"] in main.sessions


def test_chat_reuses_session_history(monkeypatch):
    main.sessions.clear()
    captured = []
    monkeypatch.setattr(main.agent_graph, "invoke", _fake_invoke_factory(captured))
    client = TestClient(main.app)

    first = client.post("/chat", json={"message": "hola", "session_id": "s1"})
    second = client.post("/chat", json={"message": "y ahora?", "session_id": "s1"})

    assert first.json()["session_id"] == "s1"
    assert second.json()["session_id"] == "s1"
    assert len(captured[1]) > len(captured[0])


def test_chat_different_sessions_do_not_share_history(monkeypatch):
    main.sessions.clear()
    captured = []
    monkeypatch.setattr(main.agent_graph, "invoke", _fake_invoke_factory(captured))
    client = TestClient(main.app)

    client.post("/chat", json={"message": "hola", "session_id": "a"})
    client.post("/chat", json={"message": "hola", "session_id": "b"})

    assert len(captured[0]) == len(captured[1])
