from __future__ import annotations

import os

import pytest

from app.config import (
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    _as_bool,
    _as_list,
    _resolve_database_uri,
    _unique,
    get_config,
)


class TestAsBool:
    def test_true_values(self):
        for value in ("1", "true", "True", "TRUE", "yes", "YES", "on", "ON"):
            assert _as_bool(value) is True

    def test_false_values(self):
        for value in ("0", "false", "False", "no", "off", "", "other"):
            assert _as_bool(value) is False

    def test_none_returns_default(self):
        assert _as_bool(None) is False
        assert _as_bool(None, default=True) is True


class TestAsList:
    def test_splits_by_comma(self):
        assert _as_list("a,b,c", "") == ["a", "b", "c"]

    def test_strips_whitespace(self):
        assert _as_list(" a , b , c ", "") == ["a", "b", "c"]

    def test_filters_empty_items(self):
        assert _as_list("a,,b,", "") == ["a", "b"]

    def test_none_returns_default(self):
        assert _as_list(None, "x,y") == ["x", "y"]


class TestUnique:
    def test_preserves_order_and_removes_duplicates(self):
        assert _unique(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_filters_empty_strings(self):
        assert _unique(["a", "", "b", ""]) == ["a", "b"]


class TestResolveDatabaseUri:
    def test_memory_uri_unchanged(self):
        assert _resolve_database_uri("sqlite:///:memory:") == "sqlite:///:memory:"

    def test_non_sqlite_uri_unchanged(self):
        uri = "postgresql://localhost/db"
        assert _resolve_database_uri(uri) == uri


class TestConfigClasses:
    def test_testing_config(self):
        assert TestingConfig.TESTING is True
        assert TestingConfig.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"

    def test_development_config(self):
        assert DevelopmentConfig.DEBUG is True

    def test_production_config(self):
        assert ProductionConfig.DEBUG is False

    def test_base_config_defaults(self):
        assert BaseConfig.MAX_DEBATE_ROUNDS == 3
        assert BaseConfig.PROMPT_HISTORY_LIMIT == 6
        assert BaseConfig.MOCK_STREAM_CHUNK_SIZE == 24
        assert isinstance(BaseConfig.LLM_TIMEOUT_SECONDS, int)
        assert BaseConfig.LLM_TIMEOUT_SECONDS > 0
        assert BaseConfig.LLM_DEBATE_MAX_TOKENS == 320
        assert BaseConfig.LLM_EVALUATION_MAX_TOKENS == 500

    def test_get_config_returns_testing(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        config = get_config()
        assert config.TESTING is True

    def test_get_config_returns_production(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        config = get_config()
        assert config.DEBUG is False

    def test_get_config_unknown_env_defaults_to_development(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "unknown")
        config = get_config()
        assert config.DEBUG is True


class TestConfigEnvOverrides:
    def test_max_debate_rounds_from_env(self, monkeypatch):
        monkeypatch.setenv("MAX_DEBATE_ROUNDS", "5")
        from importlib import reload
        import app.config
        reload(app.config)
        assert app.config.BaseConfig.MAX_DEBATE_ROUNDS == 5
        monkeypatch.delenv("MAX_DEBATE_ROUNDS", raising=False)
        reload(app.config)

    def test_llm_timeout_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "60")
        from importlib import reload
        import app.config
        reload(app.config)
        assert app.config.BaseConfig.LLM_TIMEOUT_SECONDS == 60
        monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
        reload(app.config)
