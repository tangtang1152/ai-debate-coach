from __future__ import annotations

from flask import current_app

from app.extensions import db
from app.repositories.session_repository import SessionRepository
from app.utils.errors import NotFoundError, ValidationError


class SessionService:
    def __init__(self, session_repository: SessionRepository):
        self.session_repository = session_repository

    def create_session(self, topic: str, position: str, model_name: str | None = None):
        resolved_model = self._resolve_model(model_name)
        session = self.session_repository.create(
            topic=topic,
            position=position,
            model_name=resolved_model,
        )
        db.session.commit()
        return session

    def get_session_or_raise(self, session_id: str):
        session = self.session_repository.get_by_id(session_id)
        if session is None:
            raise NotFoundError("未找到对应的辩论会话。")
        return session

    def _resolve_model(self, model_name: str | None) -> str:
        selected_model = (model_name or current_app.config["LLM_MODEL"]).strip()
        selectable_models = current_app.config.get("LLM_SELECTABLE_MODELS") or [
            current_app.config["LLM_MODEL"]
        ]

        if selected_model not in selectable_models:
            raise ValidationError("model 不在当前可选模型范围内。")

        return selected_model
