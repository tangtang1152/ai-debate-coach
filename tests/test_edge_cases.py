from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from app.models.session import Session
from app.schemas.debate import parse_start_payload
from app.utils.errors import ValidationError
from app.config import _resolve_database_uri


class TestIsoformatNone:
    def test_isoformat_none_returns_none(self, client, app):
        """controller _isoformat(None) path."""
        from app.controllers.debate_controller import _isoformat

        assert _isoformat(None) is None


class TestSessionStatus:
    def test_status_created(self, app):
        """status == 'created' when current_round == 0."""
        with app.app_context():
            session = Session(
                topic="测试",
                position="正方",
                model_name="test/model",
                current_round=0,
            )
            assert session.status == "created"

    def test_status_debating(self, app):
        """status == 'debating' when 1 <= current_round < 3."""
        with app.app_context():
            session = Session(
                topic="测试",
                position="正方",
                model_name="test/model",
                current_round=2,
            )
            assert session.status == "debating"

    def test_status_ready_for_evaluation(self, app):
        """status == 'ready_for_evaluation' when current_round >= 3."""
        with app.app_context():
            session = Session(
                topic="测试",
                position="正方",
                model_name="test/model",
                current_round=3,
            )
            assert session.status == "ready_for_evaluation"


class TestCorsWildcard:
    def test_cors_wildcard_allows_any_origin(self):
        """Line 71: CORS with '*' allows any origin."""
        app = create_app(
            {
                "TESTING": True,
                "APP_ENV": "test",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "LLM_PROVIDER": "mock",
                "CORS_ORIGINS": ["*"],
            }
        )

        with app.app_context():
            db.create_all()

        client = app.test_client()
        response = client.post(
            "/api/debate/start",
            json={"topic": "测试", "position": "正方"},
            headers={"Origin": "http://any-origin.com"},
        )

        assert response.headers.get("Access-Control-Allow-Origin") == "http://any-origin.com"

        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def test_cors_wildcard_no_origin_header_uses_star(self):
        """CORS with '*' and no Origin header uses '*'."""
        app = create_app(
            {
                "TESTING": True,
                "APP_ENV": "test",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "LLM_PROVIDER": "mock",
                "CORS_ORIGINS": ["*"],
            }
        )

        with app.app_context():
            db.create_all()

        client = app.test_client()
        response = client.get("/health")

        assert response.headers.get("Access-Control-Allow-Origin") == "*"

        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


class TestConfigDbPath:
    def test_resolve_absolute_sqlite_path(self, tmp_path):
        """Lines 37-38: resolve absolute sqlite path creates parent dir."""
        import os

        db_dir = tmp_path / "custom_db"
        db_file = db_dir / "test.db"
        uri = _resolve_database_uri(f"sqlite:///{db_file.as_posix()}")
        assert db_dir.exists()
        assert "sqlite:///" in uri
        assert "test.db" in uri


class TestOptionalTextNonString:
    def test_non_string_model_raises(self):
        """Line 77: _optional_text with non-string value raises."""
        with pytest.raises(ValidationError, match="必须是字符串"):
            parse_start_payload(
                {"topic": "AI", "position": "正方", "model": 12345}
            )


class TestRepositorySave:
    def test_evaluation_repository_save(self, app):
        """Cover save() on evaluation repository."""
        from app.repositories.evaluation_repository import EvaluationRepository

        with app.app_context():
            repo = EvaluationRepository()
            eval_obj = repo.create(
                session_id="fake-session-id",
                logic_score=5,
                evidence_score=5,
                fluency_score=5,
                suggestion="测试。",
            )
            saved = repo.save(eval_obj)
            assert saved is eval_obj
