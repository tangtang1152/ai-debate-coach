from __future__ import annotations

from app.extensions import db
from app.models.session import Session


class SessionRepository:
    def create(self, topic: str, position: str, model_name: str) -> Session:
        session = Session(topic=topic, position=position, model_name=model_name)
        db.session.add(session)
        return session

    def get_by_id(self, session_id: str) -> Session | None:
        return Session.query.filter_by(id=session_id).first()

    def list_recent(self, limit: int = 8) -> list[Session]:
        return Session.query.order_by(Session.updated_at.desc()).limit(limit).all()

    def save(self, session: Session) -> Session:
        db.session.add(session)
        return session
