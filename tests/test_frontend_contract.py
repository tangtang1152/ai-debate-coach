from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_uses_backend_api_contract(app):
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    for endpoint in (
        "/api/debate/start",
        "/api/debate/stream",
        "/api/debate/evaluate",
        "/api/debate/sessions",
    ):
        assert endpoint in app_js

    for response_field in (
        "session_id",
        "current_round",
        "is_final_round",
        "logic_score",
        "evidence_score",
        "fluency_score",
        "suggestion",
    ):
        assert response_field in app_js

    assert app.config["LLM_MODEL"] in app_js


def test_frontend_handles_sse_event_contract():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "response.body.getReader()" in app_js
    assert 'eventName === "chunk"' in app_js
    assert 'eventName === "done"' in app_js
    assert 'eventName === "error"' in app_js
    assert "TextDecoder" in app_js


def test_frontend_has_required_dom_targets_for_core_workflow():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    for element_id in (
        "setupForm",
        "topicInput",
        "modelSelect",
        "messageForm",
        "messageInput",
        "messageList",
        "evaluateButton",
        "logicScore",
        "evidenceScore",
        "fluencyScore",
        "suggestionText",
    ):
        assert f'id="{element_id}"' in index_html
