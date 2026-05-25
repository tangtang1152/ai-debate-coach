from __future__ import annotations

import time

import pytest

from app.clients.llm_client import LLMClient


@pytest.mark.performance
def test_start_api_local_performance_baseline(client):
    """Lightweight local baseline for repeated session creation."""
    iterations = 30

    started_at = time.perf_counter()
    for index in range(iterations):
        response = client.post(
            "/api/debate/start",
            json={
                "topic": f"性能基线测试辩题 {index}",
                "position": "正方",
            },
        )
        assert response.status_code == 201
    elapsed = time.perf_counter() - started_at

    assert elapsed < 5.0
    assert elapsed / iterations < 0.2


@pytest.mark.performance
def test_stream_api_mock_performance_baseline(client, monkeypatch):
    """Checks the local API path without external LLM latency."""
    iterations = 12

    def fake_stream(self, messages, model=None):
        yield "快速反驳。"

    monkeypatch.setattr(LLMClient, "stream_debate_reply", fake_stream)

    session_ids = []
    for index in range(iterations):
        start = client.post(
            "/api/debate/start",
            json={
                "topic": f"流式性能基线测试辩题 {index}",
                "position": "反方",
            },
        )
        session_ids.append(start.get_json()["session_id"])

    started_at = time.perf_counter()
    for session_id in session_ids:
        response = client.post(
            "/api/debate/stream",
            json={
                "session_id": session_id,
                "content": "本轮观点用于性能基线测试。",
            },
        )
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "event: done" in body
    elapsed = time.perf_counter() - started_at

    assert elapsed < 5.0
    assert elapsed / iterations < 0.3
