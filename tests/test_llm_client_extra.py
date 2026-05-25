from __future__ import annotations

import pytest

from app.clients.llm_client import LLMClient
from app.utils.errors import LLMClientError


@pytest.fixture
def live_config():
    return {
        "LLM_PROVIDER": "openrouter",
        "LLM_API_BASE_URL": "https://openrouter.ai/api/v1",
        "LLM_API_KEY": "sk-test-key",
        "LLM_MODEL": "qwen/qwen3-next-80b-a3b-instruct:free",
        "LLM_FALLBACK_MODELS": [],
        "LLM_TIMEOUT_SECONDS": 30,
        "MOCK_STREAM_CHUNK_SIZE": 12,
        "LLM_DEBATE_MAX_TOKENS": 320,
        "LLM_EVALUATION_MAX_TOKENS": 500,
        "LLM_REASONING_EFFORT": "none",
        "OPENROUTER_HTTP_REFERER": "",
        "OPENROUTER_APP_TITLE": "",
    }


class TestLLMClientNonMockPublicMethods:
    def test_stream_debate_reply_non_mock(self, live_config, monkeypatch, app):
        """Line 33: stream_debate_reply yields from _chat_completion_stream."""
        client = LLMClient(live_config)

        def fake_stream(self, messages, temperature, max_tokens, model):
            yield "chunk1"
            yield "chunk2"

        monkeypatch.setattr(
            LLMClient, "_chat_completion_stream", fake_stream
        )

        with app.app_context():
            chunks = list(
                client.stream_debate_reply(
                    [{"role": "user", "content": "hi"}]
                )
            )
        assert chunks == ["chunk1", "chunk2"]

    def test_generate_debate_reply_non_mock(self, live_config, monkeypatch, app):
        """Line 43: generate_debate_reply calls _chat_completion."""
        client = LLMClient(live_config)

        monkeypatch.setattr(
            LLMClient,
            "_chat_completion",
            lambda self, messages, temperature, max_tokens, model: "辩论回复内容",
        )

        with app.app_context():
            result = client.generate_debate_reply(
                [{"role": "user", "content": "hi"}]
            )
        assert result == "辩论回复内容"

    def test_generate_evaluation_non_mock(self, live_config, monkeypatch, app):
        """Line 53: generate_evaluation calls _chat_completion."""
        client = LLMClient(live_config)

        monkeypatch.setattr(
            LLMClient,
            "_chat_completion",
            lambda self, messages, temperature, max_tokens, model: '{"score":8}',
        )

        with app.app_context():
            result = client.generate_evaluation(
                [{"role": "user", "content": "hi"}]
            )
        assert '{"score":8}' == result


class TestLLMClientNoModels:
    def test_no_models_configured_raises(self, live_config, app):
        """Line 87: raise when no models configured at all."""
        config = {**live_config, "LLM_MODEL": "", "LLM_FALLBACK_MODELS": []}
        client = LLMClient(config)

        with app.app_context():
            with pytest.raises(LLMClientError, match="未配置可用的大模型"):
                client._chat_completion(
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.7,
                    max_tokens=100,
                )

    def test_no_models_for_stream_raises(self, live_config, app):
        """Line 160: stream raises when no models configured."""
        config = {**live_config, "LLM_MODEL": "", "LLM_FALLBACK_MODELS": []}
        client = LLMClient(config)

        with app.app_context():
            with pytest.raises(LLMClientError, match="未配置可用的大模型"):
                list(
                    client._chat_completion_stream(
                        messages=[{"role": "user", "content": "hi"}],
                        temperature=0.7,
                        max_tokens=100,
                    )
                )


class TestLLMClientStreamSuccessPath:
    def test_stream_once_success_path(self, live_config, monkeypatch, app):
        """Cover stream success path (lines 197-207) via monkeypatch."""
        import requests

        client = LLMClient(live_config)

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def iter_content(self, chunk_size):
                yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
                yield b"data: [DONE]\n\n"

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            chunks = list(
                client._chat_completion_stream_once(
                    model="test/model",
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.7,
                    max_tokens=100,
                )
            )
        assert chunks == ["hello"]

    def test_stream_once_no_content_raises(self, live_config, monkeypatch, app):
        """Line 206-207: stream with no content raises LLMClientError."""
        import requests

        client = LLMClient(live_config)

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def iter_content(self, chunk_size):
                yield b"data: [DONE]\n\n"

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            with pytest.raises(LLMClientError, match="没有返回有效反驳内容"):
                list(
                    client._chat_completion_stream_once(
                        model="test/model",
                        messages=[{"role": "user", "content": "hi"}],
                        temperature=0.7,
                        max_tokens=100,
                    )
                )

    def test_stream_once_error_in_data(self, live_config, monkeypatch, app):
        """Line 197-198: stream data contains error key."""
        import json
        import requests

        client = LLMClient(live_config)
        error_data = json.dumps(
            {"error": {"message": "model overloaded"}}
        ).encode("utf-8")

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def iter_content(self, chunk_size):
                yield b"data: " + error_data + b"\n\n"

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            with pytest.raises(LLMClientError, match="model overloaded"):
                list(
                    client._chat_completion_stream_once(
                        model="test/model",
                        messages=[{"role": "user", "content": "hi"}],
                        temperature=0.7,
                        max_tokens=100,
                    )
                )

    def test_stream_once_json_decode_error(self, live_config, monkeypatch, app):
        """Lines 212-213: JSON decode error in SSE data."""
        import requests

        client = LLMClient(live_config)

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def iter_content(self, chunk_size):
                yield b"data: {this is not valid json]\n\n"

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            with pytest.raises(LLMClientError, match="格式异常"):
                list(
                    client._chat_completion_stream_once(
                        model="test/model",
                        messages=[{"role": "user", "content": "hi"}],
                        temperature=0.7,
                        max_tokens=100,
                    )
                )

    def test_stream_once_missing_choices_key(self, live_config, monkeypatch, app):
        """Lines 212-213: KeyError when SSE data missing 'choices'."""
        import json
        import requests

        client = LLMClient(live_config)
        bad_data = json.dumps({"no_choices_here": True}).encode("utf-8")

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def iter_content(self, chunk_size):
                yield b"data: " + bad_data + b"\n\n"

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            with pytest.raises(LLMClientError, match="格式异常"):
                list(
                    client._chat_completion_stream_once(
                        model="test/model",
                        messages=[{"role": "user", "content": "hi"}],
                        temperature=0.7,
                        max_tokens=100,
                    )
                )


class TestLLMClientStreamReturn:
    def test_chat_completion_stream_success_return(self, live_config, monkeypatch, app):
        """Line 146: return after successful stream iteration completes."""
        client = LLMClient(live_config)

        def fake_stream_once(self, model, messages, temperature, max_tokens):
            yield "chunk1"
            yield "chunk2"

        monkeypatch.setattr(
            LLMClient, "_chat_completion_stream_once", fake_stream_once
        )

        with app.app_context():
            chunks = list(
                client._chat_completion_stream(
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.7,
                    max_tokens=100,
                )
            )
        assert chunks == ["chunk1", "chunk2"]
