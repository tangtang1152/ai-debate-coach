from __future__ import annotations

from app.utils.errors import (
    AppError,
    ConflictError,
    LLMClientError,
    NotFoundError,
    ValidationError,
)


class TestAppError:
    def test_default_status_code_and_code(self):
        error = AppError("通用错误")
        assert error.status_code == 400
        assert error.error_code == "app_error"
        assert error.message == "通用错误"
        assert error.details is None

    def test_with_details(self):
        error = AppError("带详情的错误", details={"field": "name"})
        assert error.details == {"field": "name"}

    def test_str_representation(self):
        error = AppError("测试消息")
        assert str(error) == "测试消息"


class TestValidationError:
    def test_status_code_and_code(self):
        error = ValidationError("参数非法")
        assert error.status_code == 400
        assert error.error_code == "validation_error"


class TestNotFoundError:
    def test_status_code_and_code(self):
        error = NotFoundError("资源不存在")
        assert error.status_code == 404
        assert error.error_code == "not_found"


class TestConflictError:
    def test_status_code_and_code(self):
        error = ConflictError("状态冲突")
        assert error.status_code == 409
        assert error.error_code == "conflict"


class TestLLMClientError:
    def test_status_code_and_code(self):
        error = LLMClientError("上游服务异常")
        assert error.status_code == 502
        assert error.error_code == "llm_upstream_error"
