from __future__ import annotations

from app.clients.llm_client import LLMClient
from app.extensions import db
from app.models.message import Message
from app.models.session import Session


def test_stream_api_persists_messages_and_updates_round(client, app, monkeypatch):
    start_response = client.post(
        "/api/debate/start",
        json={
            "topic": "Should AI-assisted learning be widely adopted in universities?",
            "position": "\u6b63\u65b9",
            "model": "qwen/qwen3-coder:free",
        },
    )
    session_id = start_response.get_json()["session_id"]
    observed_models = []

    def fake_stream(self, messages, model=None):
        observed_models.append(model)
        yield "First chunk. "
        yield "Second chunk."

    monkeypatch.setattr(LLMClient, "stream_debate_reply", fake_stream)

    response = client.post(
        "/api/debate/stream",
        json={
            "session_id": session_id,
            "content": "AI can tailor pace and feedback to each student.",
        },
    )

    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert "event: chunk" in body
    assert "event: done" in body
    assert '"round_no": 1' in body
    assert '"is_final_round": false' in body

    with app.app_context():
        session = db.session.get(Session, session_id)
        messages = (
            db.session.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.id.asc())
            .all()
        )

        assert session.current_round == 1
        assert session.model_name == "qwen/qwen3-coder:free"
        assert observed_models == ["qwen/qwen3-coder:free"]
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "AI can tailor pace and feedback to each student."
        assert messages[0].round_no == 1
        assert messages[1].role == "assistant"
        assert messages[1].content == "First chunk. Second chunk."
        assert messages[1].round_no == 1


def test_stream_api_rejects_after_max_rounds(client, app):
    start_response = client.post(
        "/api/debate/start",
        json={
            "topic": "Should short videos improve public discussion quality?",
            "position": "\u53cd\u65b9",
        },
    )
    session_id = start_response.get_json()["session_id"]

    with app.app_context():
        session = db.session.get(Session, session_id)
        session.current_round = 3
        db.session.commit()

    response = client.post(
        "/api/debate/stream",
        json={
            "session_id": session_id,
            "content": "This extra round should be rejected.",
        },
    )

    assert response.status_code == 409
    data = response.get_json()
    assert data["error"]["code"] == "conflict"
