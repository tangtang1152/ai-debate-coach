from __future__ import annotations

from app.clients.llm_client import LLMClient
from app.extensions import db
from app.models.session import Session
from app.repositories.message_repository import MessageRepository


def test_evaluate_api(client, app, monkeypatch):
    response = client.post(
        "/api/debate/start",
        json={
            "topic": "短视频平台是否提升了公共讨论质量",
            "position": "反方",
            "model": "google/gemma-4-31b-it:free",
        },
    )
    session_id = response.get_json()["session_id"]
    observed_models = []

    with app.app_context():
        session = db.session.get(Session, session_id)
        session.current_round = 3

        repository = MessageRepository()
        repository.add_message(session_id, "user", "我认为短视频压缩了议题深度。", 1)
        repository.add_message(session_id, "assistant", "信息门槛降低也会扩大参与。", 1)
        repository.add_message(session_id, "user", "参与扩大不代表讨论质量提升。", 2)
        repository.add_message(session_id, "assistant", "但它让更多人进入公共议题。", 2)
        repository.add_message(session_id, "user", "进入公共议题后仍需事实核验机制。", 3)
        repository.add_message(session_id, "assistant", "平台治理与媒介形态不能简单等同。", 3)
        db.session.commit()

    monkeypatch.setattr(
        LLMClient,
        "generate_evaluation",
        lambda self, messages, model=None: (
            observed_models.append(model)
            or '{"logic_score": 8, "evidence_score": 7, '
            '"fluency_score": 6, "suggestion": "继续补强数据支撑。"}'
        ),
    )

    evaluation_response = client.post(
        "/api/debate/evaluate",
        json={"session_id": session_id},
    )

    assert evaluation_response.status_code == 200
    data = evaluation_response.get_json()
    assert data["logic_score"] == 8
    assert data["evidence_score"] == 7
    assert data["fluency_score"] == 6
    assert data["fallback_used"] is False
    assert observed_models == ["google/gemma-4-31b-it:free"]
