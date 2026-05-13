from __future__ import annotations

from dataclasses import dataclass

from app.utils.errors import ValidationError


@dataclass(slots=True)
class StartDebateRequest:
    topic: str
    position: str
    model: str | None = None


@dataclass(slots=True)
class StreamDebateRequest:
    session_id: str
    content: str


@dataclass(slots=True)
class EvaluateDebateRequest:
    session_id: str


def parse_start_payload(payload: dict | None) -> StartDebateRequest:
    payload = _ensure_payload(payload)
    topic = _require_text(payload, "topic", max_length=100)
    position = _require_text(payload, "position", max_length=20)
    model = _optional_text(payload, "model", max_length=120)

    if position not in {"正方", "反方"}:
        raise ValidationError("position 只允许为“正方”或“反方”。")

    return StartDebateRequest(topic=topic, position=position, model=model)


def parse_stream_payload(payload: dict | None) -> StreamDebateRequest:
    payload = _ensure_payload(payload)
    return StreamDebateRequest(
        session_id=_require_text(payload, "session_id", max_length=36),
        content=_require_text(payload, "content"),
    )


def parse_evaluate_payload(payload: dict | None) -> EvaluateDebateRequest:
    payload = _ensure_payload(payload)
    return EvaluateDebateRequest(
        session_id=_require_text(payload, "session_id", max_length=36),
    )


def _ensure_payload(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("请求体必须是 JSON 对象。")
    return payload


def _require_text(payload: dict, key: str, max_length: int | None = None) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} 不能为空。")

    cleaned = value.strip()
    if max_length is not None and len(cleaned) > max_length:
        raise ValidationError(f"{key} 长度不能超过 {max_length} 个字符。")

    return cleaned


def _optional_text(payload: dict, key: str, max_length: int | None = None) -> str | None:
    value = payload.get(key)
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValidationError(f"{key} 必须是字符串。")

    cleaned = value.strip()
    if not cleaned:
        return None

    if max_length is not None and len(cleaned) > max_length:
        raise ValidationError(f"{key} 长度不能超过 {max_length} 个字符。")

    return cleaned
