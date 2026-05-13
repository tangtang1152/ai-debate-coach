from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = BASE_DIR / "storage" / "debate_coach.db"
DEFAULT_SELECTABLE_MODELS = (
    "qwen/qwen3-next-80b-a3b-instruct:free,"
    "tencent/hy3-preview:free,"
    "google/gemma-4-31b-it:free,"
    "qwen/qwen3-coder:free"
)

load_dotenv(BASE_DIR / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_database_uri(uri: str) -> str:
    if not uri.startswith("sqlite:///"):
        return uri

    sqlite_path = uri.removeprefix("sqlite:///")
    if sqlite_path == ":memory:":
        return uri

    candidate = Path(sqlite_path)
    if candidate.is_absolute():
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{candidate.as_posix()}"

    resolved = BASE_DIR / candidate
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{resolved.as_posix()}"


def _as_list(value: str | None, default: str) -> list[str]:
    source = value if value is not None else default
    return [item.strip() for item in source.split(",") if item.strip()]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


class BaseConfig:
    APP_NAME = os.getenv("APP_NAME", "ai-debate-coach-backend")
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = _as_bool(os.getenv("APP_DEBUG"), False)
    TESTING = False

    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(
        os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH.relative_to(BASE_DIR).as_posix()}")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False

    CORS_ORIGINS = _as_list(
        os.getenv("CORS_ORIGINS"),
        "http://127.0.0.1:5173,http://localhost:5173",
    )

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    MAX_DEBATE_ROUNDS = int(os.getenv("MAX_DEBATE_ROUNDS", "3"))
    PROMPT_HISTORY_LIMIT = int(os.getenv("PROMPT_HISTORY_LIMIT", "6"))
    MOCK_STREAM_CHUNK_SIZE = int(os.getenv("MOCK_STREAM_CHUNK_SIZE", "24"))

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
    LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_FALLBACK_MODELS = _as_list(os.getenv("LLM_FALLBACK_MODELS"), "")
    LLM_SELECTABLE_MODELS = _unique(
        [
            LLM_MODEL,
            *LLM_FALLBACK_MODELS,
            *_as_list(os.getenv("LLM_SELECTABLE_MODELS"), DEFAULT_SELECTABLE_MODELS),
        ]
    )
    LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    LLM_DEBATE_MAX_TOKENS = int(os.getenv("LLM_DEBATE_MAX_TOKENS", "320"))
    LLM_EVALUATION_MAX_TOKENS = int(os.getenv("LLM_EVALUATION_MAX_TOKENS", "500"))
    LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "none")
    OPENROUTER_HTTP_REFERER = os.getenv("OPENROUTER_HTTP_REFERER", "")
    OPENROUTER_APP_TITLE = os.getenv("OPENROUTER_APP_TITLE", "AI Debate Coach")


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(
        os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


def get_config():
    env = os.getenv("APP_ENV", "development").lower()
    mapping = {
        "development": DevelopmentConfig,
        "test": TestingConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    return mapping.get(env, DevelopmentConfig)
