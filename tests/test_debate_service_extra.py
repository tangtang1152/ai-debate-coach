from __future__ import annotations

from app.clients.llm_client import LLMClient
from app.extensions import db
from app.models.message import Message
from app.models.session import Session
from app.utils.errors import AppError, LLMClientError


class TestDebateServiceStreamErrorPaths:
    def test_skips_empty_chunk(self, client, app, monkeypatch):
        """Line 51: empty chunk is skipped, valid chunks are collected."""
        start = client.post(
            "/api/debate/start",
            json={"topic": "测试辩题", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        def fake_stream(self, messages, model=None):
            yield ""
            yield "有效内容。"
            yield ""

        monkeypatch.setattr(LLMClient, "stream_debate_reply", fake_stream)

        response = client.post(
            "/api/debate/stream",
            json={"session_id": session_id, "content": "测试论点。"},
        )
        body = response.get_data(as_text=True)
        assert "event: done" in body
        assert '"content": "有效内容。"' in body

    def test_empty_reply_raises_and_yields_error_event(self, client, app, monkeypatch):
        """Lines 64 + 91-99 + 93-94: empty assistant reply triggers LLMClientError
        which is caught as AppError and yields SSE error event."""
        start = client.post(
            "/api/debate/start",
            json={"topic": "测试辩题", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        def fake_stream(self, messages, model=None):
            if False:
                yield

        monkeypatch.setattr(LLMClient, "stream_debate_reply", fake_stream)

        response = client.post(
            "/api/debate/stream",
            json={"session_id": session_id, "content": "测试论点。"},
        )
        body = response.get_data(as_text=True)
        assert "event: error" in body
        assert "大模型没有返回有效反驳内容" in body
        assert response.status_code == 200

    def test_non_app_error_yields_generic_error_event(self, client, app, monkeypatch):
        """Lines 95-97: non-AppError exception triggers generic error message."""
        start = client.post(
            "/api/debate/start",
            json={"topic": "测试辩题", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        def fake_stream(self, messages, model=None):
            raise RuntimeError("模拟意外崩溃")

        monkeypatch.setattr(LLMClient, "stream_debate_reply", fake_stream)

        response = client.post(
            "/api/debate/stream",
            json={"session_id": session_id, "content": "测试论点。"},
        )
        body = response.get_data(as_text=True)
        assert "event: error" in body
        assert "流式生成失败，请重试当前回合" in body


class TestDebateServiceStreamEdgeCases:
    def test_stream_rejects_over_max_rounds(self, client, app):
        """Line 32-33: ConflictError when round >= max_rounds."""
        start = client.post(
            "/api/debate/start",
            json={"topic": "测试", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        with app.app_context():
            session = db.session.get(Session, session_id)
            session.current_round = 3
            db.session.commit()

        response = client.post(
            "/api/debate/stream",
            json={"session_id": session_id, "content": "超额发言。"},
        )
        assert response.status_code == 409

    def test_rollback_on_stream_error(self, client, app, monkeypatch):
        """Line 92: db.session.rollback() is called on exception."""
        start = client.post(
            "/api/debate/start",
            json={"topic": "测试辩题", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        def fake_stream(self, messages, model=None):
            yield "第一块。"
            raise AppError("模拟 App 层错误")

        monkeypatch.setattr(LLMClient, "stream_debate_reply", fake_stream)

        response = client.post(
            "/api/debate/stream",
            json={"session_id": session_id, "content": "测试论点。"},
        )
        body = response.get_data(as_text=True)
        assert "event: error" in body
        assert "模拟 App 层错误" in body

        with app.app_context():
            messages = (
                db.session.query(Message)
                .filter(Message.session_id == session_id)
                .all()
            )
            assert len(messages) == 0
