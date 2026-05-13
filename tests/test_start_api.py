from __future__ import annotations


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
