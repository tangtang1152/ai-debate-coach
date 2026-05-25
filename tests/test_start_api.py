from __future__ import annotations

from app.extensions import db
from app.models.evaluation import Evaluation
from app.models.message import Message
from app.models.session import Session


def test_start_api(client, app):
    response = client.post(
        "/api/debate/start",
        json={"topic": "大学教育是否应该全面推行 AI 辅助学习", "position": "正方"},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["session_id"]
    assert data["topic"] == "大学教育是否应该全面推行 AI 辅助学习"
    assert data["position"] == "正方"
    assert data["model"] == app.config["LLM_MODEL"]
    assert data["current_round"] == 0


def test_start_api_accepts_selectable_model(client):
    response = client.post(
        "/api/debate/start",
        json={
            "topic": "大学教育是否应该全面推行 AI 辅助学习",
            "position": "正方",
            "model": "qwen/qwen3-next-80b-a3b-instruct:free",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["model"] == "qwen/qwen3-next-80b-a3b-instruct:free"


def test_start_api_rejects_unlisted_model(client):
    response = client.post(
        "/api/debate/start",
        json={
            "topic": "大学教育是否应该全面推行 AI 辅助学习",
            "position": "正方",
            "model": "unknown/provider:free",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"]["code"] == "validation_error"


def test_list_sessions_returns_recent_sessions(client):
    client.post(
        "/api/debate/start",
        json={"topic": "大学教育是否应该全面推行 AI 辅助学习", "position": "正方"},
    )

    response = client.get("/api/debate/sessions")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["topic"] == "大学教育是否应该全面推行 AI 辅助学习"
    assert data["sessions"][0]["has_evaluation"] is False


def test_get_session_detail_returns_messages_and_evaluation(client, app):
    with app.app_context():
        session = Session(
            topic="人工智能是否利大于弊",
            position="正方",
            model_name=app.config["LLM_MODEL"],
            current_round=3,
        )
        db.session.add(session)
        db.session.flush()
        db.session.add(
            Message(
                session_id=session.id,
                role="user",
                content="AI 能提升效率。",
                round_no=1,
            )
        )
        db.session.add(
            Evaluation(
                session_id=session.id,
                logic_score=7,
                evidence_score=6,
                fluency_score=8,
                suggestion="论点清晰，但需要补充具体数据和反例回应。",
            )
        )
        db.session.commit()
        session_id = session.id

    response = client.get(f"/api/debate/sessions/{session_id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["session_id"] == session_id
    assert data["messages"][0]["content"] == "AI 能提升效率。"
    assert data["evaluation"]["logic_score"] == 7
