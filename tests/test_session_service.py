from __future__ import annotations

import pytest

from app.repositories.session_repository import SessionRepository
from app.services.session_service import SessionService
from app.utils.errors import NotFoundError, ValidationError


class TestSessionService:
    @pytest.fixture
    def service(self, app):
        with app.app_context():
            yield SessionService(SessionRepository())

    def test_create_session_with_default_model(self, app, service):
        with app.app_context():
            session = service.create_session(
                topic="测试辩题", position="正方"
            )
            assert session.topic == "测试辩题"
            assert session.position == "正方"
            assert session.model_name == app.config["LLM_MODEL"]

    def test_create_session_with_custom_model(self, app, service):
        model = "google/gemma-4-31b-it:free"
        with app.app_context():
            session = service.create_session(
                topic="测试辩题", position="反方", model_name=model
            )
            assert session.model_name == model

    def test_create_session_rejects_unlisted_model(self, app, service):
        with app.app_context(), pytest.raises(ValidationError, match="model"):
            service.create_session(
                topic="测试辩题",
                position="正方",
                model_name="unknown/model:free",
            )

    def test_get_session_or_raise_returns_session(self, app, service):
        with app.app_context():
            created = service.create_session(
                topic="查找测试", position="正方"
            )
            found = service.get_session_or_raise(created.id)
            assert found.id == created.id
            assert found.topic == "查找测试"

    def test_get_session_or_raise_not_found(self, app, service):
        with app.app_context():
            with pytest.raises(NotFoundError, match="会话"):
                service.get_session_or_raise("nonexistent-id")
