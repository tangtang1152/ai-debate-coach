from __future__ import annotations

import os

import pytest

from app import create_app
from app.clients.llm_client import LLMClient
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "LLM_PROVIDER": "mock",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def real_app():
    """Flask app with real-world config (non-mock) for integration tests."""
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")

    app = create_app(
        {
            "TESTING": True,
            "APP_ENV": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "LLM_PROVIDER": os.getenv("LLM_PROVIDER", "openrouter"),
            "LLM_API_KEY": os.getenv("LLM_API_KEY", ""),
            "LLM_API_BASE_URL": os.getenv("LLM_API_BASE_URL", "https://openrouter.ai/api/v1"),
            "LLM_MODEL": os.getenv("LLM_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free"),
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture()
def real_llm_client(real_app):
    """LLMClient configured with real OpenRouter credentials from .env."""
    ctx = real_app.app_context()
    ctx.push()

    api_key = real_app.config.get("LLM_API_KEY", "")
    if not api_key:
        ctx.pop()
        pytest.skip("LLM_API_KEY not set — skipping real API test")

    client = LLMClient(dict(real_app.config))
    yield client
    ctx.pop()
