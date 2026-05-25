from __future__ import annotations

import pytest

from app.schemas.debate import (
    parse_evaluate_payload,
    parse_start_payload,
    parse_stream_payload,
)
from app.utils.errors import ValidationError


class TestParseStartPayload:
    def test_valid_minimal_payload(self):
        result = parse_start_payload({"topic": "AI 是否利大于弊", "position": "正方"})
        assert result.topic == "AI 是否利大于弊"
        assert result.position == "正方"
        assert result.model is None

    def test_valid_payload_with_model(self):
        result = parse_start_payload(
            {
                "topic": "AI 是否利大于弊",
                "position": "反方",
                "model": "qwen/qwen3-coder:free",
            }
        )
        assert result.model == "qwen/qwen3-coder:free"

    def test_strips_whitespace_from_fields(self):
        result = parse_start_payload(
            {"topic": "  AI 伦理  ", "position": "  正方  "}
        )
        assert result.topic == "AI 伦理"
        assert result.position == "正方"

    def test_none_model_is_accepted(self):
        result = parse_start_payload(
            {"topic": "AI 伦理", "position": "正方", "model": None}
        )
        assert result.model is None

    def test_empty_model_string_becomes_none(self):
        result = parse_start_payload(
            {"topic": "AI 伦理", "position": "正方", "model": ""}
        )
        assert result.model is None

    def test_empty_topic_raises_validation_error(self):
        with pytest.raises(ValidationError, match="topic"):
            parse_start_payload({"topic": "", "position": "正方"})

    def test_whitespace_topic_raises_validation_error(self):
        with pytest.raises(ValidationError, match="topic"):
            parse_start_payload({"topic": "   ", "position": "正方"})

    def test_missing_topic_raises_validation_error(self):
        with pytest.raises(ValidationError, match="topic"):
            parse_start_payload({"position": "正方"})

    def test_topic_too_long_raises_validation_error(self):
        with pytest.raises(ValidationError, match="topic"):
            parse_start_payload({"topic": "x" * 101, "position": "正方"})

    def test_topic_at_max_length_accepted(self):
        result = parse_start_payload({"topic": "x" * 100, "position": "正方"})
        assert len(result.topic) == 100

    def test_invalid_position_raises_validation_error(self):
        with pytest.raises(ValidationError, match="position"):
            parse_start_payload({"topic": "AI 伦理", "position": "中立方"})

    def test_missing_position_raises_validation_error(self):
        with pytest.raises(ValidationError, match="position"):
            parse_start_payload({"topic": "AI 伦理"})

    def test_position_too_long_raises_validation_error(self):
        with pytest.raises(ValidationError, match="position"):
            parse_start_payload({"topic": "AI 伦理", "position": "x" * 21})

    def test_model_too_long_raises_validation_error(self):
        with pytest.raises(ValidationError, match="model"):
            parse_start_payload(
                {"topic": "AI 伦理", "position": "正方", "model": "x" * 121}
            )

    def test_none_payload_raises_validation_error(self):
        with pytest.raises(ValidationError, match="JSON 对象"):
            parse_start_payload(None)

    def test_non_dict_payload_raises_validation_error(self):
        with pytest.raises(ValidationError, match="JSON 对象"):
            parse_start_payload(["topic", "AI"])


class TestParseStreamPayload:
    def test_valid_payload(self):
        result = parse_stream_payload(
            {"session_id": "abc-123", "content": "我认为 AI 有益。"}
        )
        assert result.session_id == "abc-123"
        assert result.content == "我认为 AI 有益。"

    def test_missing_session_id_raises_validation_error(self):
        with pytest.raises(ValidationError, match="session_id"):
            parse_stream_payload({"content": "我认为 AI 有益。"})

    def test_empty_session_id_raises_validation_error(self):
        with pytest.raises(ValidationError, match="session_id"):
            parse_stream_payload({"session_id": "", "content": "内容"})

    def test_session_id_too_long_raises_validation_error(self):
        with pytest.raises(ValidationError, match="session_id"):
            parse_stream_payload({"session_id": "x" * 37, "content": "内容"})

    def test_missing_content_raises_validation_error(self):
        with pytest.raises(ValidationError, match="content"):
            parse_stream_payload({"session_id": "abc-123"})

    def test_empty_content_raises_validation_error(self):
        with pytest.raises(ValidationError, match="content"):
            parse_stream_payload({"session_id": "abc-123", "content": ""})


class TestParseEvaluatePayload:
    def test_valid_payload(self):
        result = parse_evaluate_payload({"session_id": "abc-123"})
        assert result.session_id == "abc-123"

    def test_missing_session_id_raises_validation_error(self):
        with pytest.raises(ValidationError, match="session_id"):
            parse_evaluate_payload({})

    def test_empty_session_id_raises_validation_error(self):
        with pytest.raises(ValidationError, match="session_id"):
            parse_evaluate_payload({"session_id": ""})

    def test_session_id_too_long_raises_validation_error(self):
        with pytest.raises(ValidationError, match="session_id"):
            parse_evaluate_payload({"session_id": "x" * 37})
