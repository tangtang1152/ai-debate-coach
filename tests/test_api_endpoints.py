from __future__ import annotations


class TestHealthCheck:
    def test_health_returns_ok(self, client, app):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["service"] == app.config["APP_NAME"]
        assert data["status"] == "ok"
        assert data["environment"] == app.config["APP_ENV"]


class TestCorsHeaders:
    def test_cors_headers_on_api_request(self, client):
        response = client.post(
            "/api/debate/start",
            json={"topic": "测试辩题", "position": "正方"},
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        assert response.status_code == 201
        assert response.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:5173"

    def test_cors_rejects_unknown_origin(self, client):
        response = client.post(
            "/api/debate/start",
            json={"topic": "测试辩题", "position": "正方"},
            headers={"Origin": "http://evil.com"},
        )
        assert "Access-Control-Allow-Origin" not in response.headers

    def test_cors_vary_header(self, client):
        response = client.post(
            "/api/debate/start",
            json={"topic": "测试辩题", "position": "正方"},
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        assert response.headers.get("Vary") == "Origin"


class TestApiErrorResponses:
    def test_400_on_validation_error(self, client):
        response = client.post(
            "/api/debate/start",
            json={"topic": "", "position": "正方"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"]["code"] == "validation_error"
        assert data["error"]["message"]

    def test_404_on_nonexistent_session(self, client):
        response = client.get("/api/debate/sessions/nonexistent-id")
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "not_found"

    def test_409_on_over_round(self, client, app):
        start = client.post(
            "/api/debate/start",
            json={"topic": "测试", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        from app.extensions import db
        from app.models.session import Session

        with app.app_context():
            session = db.session.get(Session, session_id)
            session.current_round = 3
            db.session.commit()

        response = client.post(
            "/api/debate/stream",
            json={"session_id": session_id, "content": "超回合发言。"},
        )
        assert response.status_code == 409
        assert response.get_json()["error"]["code"] == "conflict"

    def test_409_on_early_evaluation(self, client):
        start = client.post(
            "/api/debate/start",
            json={"topic": "测试", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        response = client.post(
            "/api/debate/evaluate",
            json={"session_id": session_id},
        )
        assert response.status_code == 409
        assert response.get_json()["error"]["code"] == "conflict"

    def test_get_session_detail_without_evaluation(self, client):
        """Line 31: _serialize_evaluation(None) returns None."""
        start = client.post(
            "/api/debate/start",
            json={"topic": "测试", "position": "正方"},
        )
        session_id = start.get_json()["session_id"]

        response = client.get(f"/api/debate/sessions/{session_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["evaluation"] is None

    def test_500_on_unhandled_error(self, client, monkeypatch):
        from app.controllers import debate_controller

        def broken_handler(*args, **kwargs):
            raise RuntimeError("模拟未预期错误")

        monkeypatch.setattr(
            debate_controller,
            "_build_session_service",
            broken_handler,
        )

        response = client.post(
            "/api/debate/start",
            json={"topic": "测试", "position": "正方"},
        )
        assert response.status_code == 500
        data = response.get_json()
        assert data["error"]["code"] == "internal_server_error"
