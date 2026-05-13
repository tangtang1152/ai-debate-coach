from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    topic = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(20), nullable=False)
    model_name = db.Column(db.String(120), nullable=False)
    current_round = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    messages = db.relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.id.asc()",
    )
    evaluation = db.relationship(
        "Evaluation",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def status(self) -> str:
        if self.current_round <= 0:
            return "created"
        if self.current_round >= 3:
            return "ready_for_evaluation"
        return "debating"
