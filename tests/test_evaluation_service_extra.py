from __future__ import annotations

import pytest

from app.extensions import db
from app.models.evaluation import Evaluation
from app.models.message import Message
from app.models.session import Session


class TestEvaluationCaching:
    def test_second_evaluate_returns_cached(self, client, app, monkeypatch):
        """Line 43: existing evaluation is returned with cached=True."""
        from app.clients.llm_client import LLMClient

        start = client.post(
            "/api/debate/start",
            json={"topic": "缓存测试", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        with app.app_context():
            session = db.session.get(Session, session_id)
            session.current_round = 3
            db.session.add(
                Message(
                    session_id=session_id,
                    role="user",
                    content="第1轮。",
                    round_no=1,
                )
            )
            db.session.add(
                Message(
                    session_id=session_id,
                    role="assistant",
                    content="回复1。",
                    round_no=1,
                )
            )
            db.session.commit()

        call_count = 0

        def fake_eval(self, messages, model=None):
            nonlocal call_count
            call_count += 1
            return '{"logic_score":7,"evidence_score":6,"fluency_score":7,"suggestion":"首次生成。"}'

        monkeypatch.setattr(LLMClient, "generate_evaluation", fake_eval)

        first = client.post(
            "/api/debate/evaluate",
            json={"session_id": session_id},
        )
        assert first.status_code == 200
        first_data = first.get_json()
        assert first_data["cached"] is False
        assert first_data["suggestion"] == "首次生成。"

        second = client.post(
            "/api/debate/evaluate",
            json={"session_id": session_id},
        )
        assert second.status_code == 200
        second_data = second.get_json()
        assert second_data["cached"] is True
        assert second_data["logic_score"] == first_data["logic_score"]
        assert call_count == 1


class TestEvaluationEmptyHistory:
    def test_empty_history_raises_conflict(self, client, app):
        """Line 47: ConflictError when session has no messages."""
        start = client.post(
            "/api/debate/start",
            json={"topic": "空历史测试", "position": "反方"},
        )
        session_id = start.get_json()["session_id"]

        with app.app_context():
            session = db.session.get(Session, session_id)
            session.current_round = 3
            db.session.commit()

        response = client.post(
            "/api/debate/evaluate",
            json={"session_id": session_id},
        )
        assert response.status_code == 409
        data = response.get_json()
        assert data["error"]["code"] == "conflict"
        assert "没有可用于评分" in data["error"]["message"]
