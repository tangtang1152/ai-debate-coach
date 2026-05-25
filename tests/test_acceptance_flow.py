from __future__ import annotations

from app.clients.llm_client import LLMClient
from app.extensions import db
from app.models.message import Message


def test_three_round_debate_acceptance_flow(client, app, monkeypatch):
    """Covers the MVP acceptance path: start -> 3 rounds -> evaluate -> restore."""
    observed_stream_models = []
    observed_evaluation_models = []

    def fake_stream(self, messages, model=None):
        observed_stream_models.append(model)
        yield "反驳要点："
        yield "请补充事实依据。"

    def fake_evaluation(self, messages, model=None):
        observed_evaluation_models.append(model)
        return (
            '{"logic_score": 8, "evidence_score": 7, "fluency_score": 9, '
            '"suggestion": "结构清楚，继续补充数据和反例回应。"}'
        )

    monkeypatch.setattr(LLMClient, "stream_debate_reply", fake_stream)
    monkeypatch.setattr(LLMClient, "generate_evaluation", fake_evaluation)

    start = client.post(
        "/api/debate/start",
        json={
            "topic": "人工智能是否会提升大学生学习效率",
            "position": "正方",
            "model": "qwen/qwen3-coder:free",
        },
    )
    assert start.status_code == 201
    session = start.get_json()
    session_id = session["session_id"]
    assert session["status"] == "created"

    for round_no in range(1, 4):
        response = client.post(
            "/api/debate/stream",
            json={
                "session_id": session_id,
                "content": f"第 {round_no} 轮观点：AI 可以提升反馈效率。",
            },
        )
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert response.mimetype == "text/event-stream"
        assert "event: chunk" in body
        assert "event: done" in body
        assert f'"round_no": {round_no}' in body
        assert f'"current_round": {round_no}' in body
        assert f'"is_final_round": {str(round_no == 3).lower()}' in body

    evaluation = client.post(
        "/api/debate/evaluate",
        json={"session_id": session_id},
    )
    assert evaluation.status_code == 200
    evaluation_data = evaluation.get_json()
    assert evaluation_data["logic_score"] == 8
    assert evaluation_data["evidence_score"] == 7
    assert evaluation_data["fluency_score"] == 9
    assert evaluation_data["cached"] is False

    detail = client.get(f"/api/debate/sessions/{session_id}")
    assert detail.status_code == 200
    detail_data = detail.get_json()
    assert detail_data["status"] == "ready_for_evaluation"
    assert detail_data["current_round"] == 3
    assert len(detail_data["messages"]) == 6
    assert detail_data["evaluation"]["suggestion"] == "结构清楚，继续补充数据和反例回应。"

    with app.app_context():
        persisted_messages = (
            db.session.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.round_no.asc(), Message.id.asc())
            .all()
        )
        assert [message.round_no for message in persisted_messages] == [1, 1, 2, 2, 3, 3]

    assert observed_stream_models == ["qwen/qwen3-coder:free"] * 3
    assert observed_evaluation_models == ["qwen/qwen3-coder:free"]
