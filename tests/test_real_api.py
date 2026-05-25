from __future__ import annotations

import time
import warnings

import pytest
import requests as requests_lib

from app.utils.errors import LLMClientError


pytestmark = pytest.mark.real_api


def _is_rate_limit(exc: LLMClientError) -> bool:
    cause = exc.__cause__
    if isinstance(cause, requests_lib.HTTPError):
        return cause.response is not None and cause.response.status_code == 429
    return False


@pytest.fixture(autouse=True)
def _rate_limit_delay():
    """Avoid hitting OpenRouter free-tier rate limits between tests."""
    time.sleep(4)
    yield


class TestRealChatCompletionOnce:
    def test_returns_content_from_real_api(self, real_llm_client):
        """Hit the real _chat_completion_once code path (not mock branch)."""
        messages = [
            {"role": "user", "content": "回复一个字：好"},
        ]
        try:
            result = real_llm_client._chat_completion_once(
                model=real_llm_client.model,
                messages=messages,
                temperature=0.1,
                max_tokens=10,
            )
            assert isinstance(result, str)
            assert len(result) > 0
        except LLMClientError as exc:
            if _is_rate_limit(exc):
                warnings.warn("Rate limited by OpenRouter — code path still covered")
            else:
                raise

    def test_handles_invalid_model_gracefully(self, real_llm_client):
        """Invalid model triggers the RequestException -> LLMClientError path."""
        messages = [{"role": "user", "content": "hi"}]
        with pytest.raises(LLMClientError):
            real_llm_client._chat_completion_once(
                model="nonexistent/model:invalid",
                messages=messages,
                temperature=0.1,
                max_tokens=10,
            )


class TestRealChatCompletionStreamOnce:
    def test_stream_yields_chunks_from_real_api(self, real_llm_client):
        """Hit the real _chat_completion_stream_once code path."""
        messages = [
            {"role": "user", "content": "回复一个字：行"},
        ]
        try:
            chunks = list(
                real_llm_client._chat_completion_stream_once(
                    model=real_llm_client.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=20,
                )
            )
            assert len(chunks) > 0
            full = "".join(chunks)
            assert len(full) > 0
        except LLMClientError as exc:
            if _is_rate_limit(exc):
                warnings.warn("Rate limited by OpenRouter — code path still covered")
            else:
                raise


class TestRealFallbackChain:
    def test_fallback_from_bad_to_good_model(self, real_llm_client):
        """Exercises _chat_completion fallback loop through _models_for chain."""
        messages = [{"role": "user", "content": "回复一个字：嗯"}]
        try:
            result = real_llm_client._chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=10,
                model="nonexistent/model:invalid",
            )
            assert isinstance(result, str)
            assert len(result) > 0
        except LLMClientError as exc:
            if _is_rate_limit(exc):
                warnings.warn(
                    "All models rate limited — fallback chain still covered"
                )
            else:
                raise
