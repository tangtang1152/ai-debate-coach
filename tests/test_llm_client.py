from __future__ import annotations

import pytest

from app.clients.llm_client import LLMClient
from app.utils.errors import LLMClientError


@pytest.fixture
def mock_config():
    return {
        "LLM_PROVIDER": "openrouter",
        "LLM_API_BASE_URL": "https://openrouter.ai/api/v1",
        "LLM_API_KEY": "sk-test-key",
        "LLM_MODEL": "qwen/qwen3-next-80b-a3b-instruct:free",
        "LLM_FALLBACK_MODELS": ["tencent/hy3-preview:free", "google/gemma-4-31b-it:free"],
        "LLM_TIMEOUT_SECONDS": 30,
        "MOCK_STREAM_CHUNK_SIZE": 12,
        "LLM_DEBATE_MAX_TOKENS": 320,
        "LLM_EVALUATION_MAX_TOKENS": 500,
        "LLM_REASONING_EFFORT": "none",
        "OPENROUTER_HTTP_REFERER": "http://127.0.0.1:5173",
        "OPENROUTER_APP_TITLE": "AI Debate Coach",
    }


class TestModelsFor:
    def test_returns_provided_model_first(self, mock_config):
        client = LLMClient(mock_config)
        result = client._models_for("custom/model:free")
        assert result[0] == "custom/model:free"

    def test_includes_default_and_fallback_after_provided(self, mock_config):
        client = LLMClient(mock_config)
        result = client._models_for("custom/model:free")
        assert result[1] == mock_config["LLM_MODEL"]
        assert result[2:] == mock_config["LLM_FALLBACK_MODELS"]

    def test_uses_default_model_when_none_provided(self, mock_config):
        client = LLMClient(mock_config)
        result = client._models_for(None)
        assert result[0] == mock_config["LLM_MODEL"]

    def test_empty_string_treated_as_none(self, mock_config):
        client = LLMClient(mock_config)
        result = client._models_for("")
        assert result[0] == mock_config["LLM_MODEL"]

    def test_deduplicates_models(self, mock_config):
        config = {**mock_config, "LLM_FALLBACK_MODELS": [mock_config["LLM_MODEL"]]}
        client = LLMClient(config)
        result = client._models_for(mock_config["LLM_MODEL"])
        assert result.count(mock_config["LLM_MODEL"]) == 1

    def test_filters_empty_strings(self, mock_config):
        config = {**mock_config, "LLM_FALLBACK_MODELS": ["", "valid/model:free", ""]}
        client = LLMClient(config)
        result = client._models_for(None)
        assert "" not in result
        assert "valid/model:free" in result


class TestBuildHeaders:
    def test_includes_auth_and_content_type(self, mock_config):
        client = LLMClient(mock_config)
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer sk-test-key"
        assert headers["Content-Type"] == "application/json"

    def test_adds_openrouter_headers_when_using_openrouter(self, mock_config):
        client = LLMClient(mock_config)
        headers = client._build_headers()
        assert headers["HTTP-Referer"] == "http://127.0.0.1:5173"
        assert headers["X-Title"] == "AI Debate Coach"

    def test_no_openrouter_headers_for_non_openrouter_url(self, mock_config):
        config = {**mock_config, "LLM_API_BASE_URL": "https://api.openai.com/v1"}
        client = LLMClient(config)
        headers = client._build_headers()
        assert "HTTP-Referer" not in headers
        assert "X-Title" not in headers

    def test_skips_empty_openrouter_referer(self, mock_config):
        config = {**mock_config, "OPENROUTER_HTTP_REFERER": ""}
        client = LLMClient(config)
        headers = client._build_headers()
        assert "HTTP-Referer" not in headers

    def test_skips_empty_openrouter_title(self, mock_config):
        config = {**mock_config, "OPENROUTER_APP_TITLE": ""}
        client = LLMClient(config)
        headers = client._build_headers()
        assert "X-Title" not in headers


class TestBuildPayload:
    def test_basic_payload_structure(self, mock_config):
        client = LLMClient(mock_config)
        base = {"model": "test-model", "messages": [], "temperature": 0.7}
        payload = client._build_payload(base)
        assert payload["model"] == "test-model"
        assert payload["temperature"] == 0.7

    def test_adds_reasoning_for_openrouter(self, mock_config):
        client = LLMClient(mock_config)
        payload = client._build_payload({"model": "test", "messages": []})
        assert "reasoning" in payload
        assert payload["reasoning"]["effort"] == "none"
        assert payload["reasoning"]["exclude"] is True
        assert payload["include_reasoning"] is False

    def test_skips_reasoning_for_non_openrouter(self, mock_config):
        config = {**mock_config, "LLM_API_BASE_URL": "https://api.openai.com/v1"}
        client = LLMClient(config)
        payload = client._build_payload({"model": "test", "messages": []})
        assert "reasoning" not in payload

    def test_skips_reasoning_when_effort_is_empty(self, mock_config):
        config = {**mock_config, "LLM_REASONING_EFFORT": ""}
        client = LLMClient(config)
        payload = client._build_payload({"model": "test", "messages": []})
        assert "reasoning" not in payload


class TestIterSseData:
    def test_single_event(self, mock_config, monkeypatch):
        client = LLMClient(mock_config)

        class FakeResponse:
            def iter_content(self, chunk_size):
                yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'

        chunks = list(client._iter_sse_data(FakeResponse()))
        assert len(chunks) == 1
        assert "hello" in chunks[0]

    def test_multiple_events(self, mock_config):
        client = LLMClient(mock_config)

        class FakeResponse:
            def iter_content(self, chunk_size):
                yield (
                    b'data: {"choices":[{"delta":{"content":"chunk1"}}]}\n\n'
                    b'data: {"choices":[{"delta":{"content":"chunk2"}}]}\n\n'
                )

        chunks = list(client._iter_sse_data(FakeResponse()))
        assert len(chunks) == 2

    def test_done_event(self, mock_config):
        client = LLMClient(mock_config)

        class FakeResponse:
            def iter_content(self, chunk_size):
                yield b"data: [DONE]\n\n"

        chunks = list(client._iter_sse_data(FakeResponse()))
        assert len(chunks) == 1
        assert chunks[0] == "[DONE]"

    def test_splits_chunks_across_iterations(self, mock_config):
        client = LLMClient(mock_config)

        class FakeResponse:
            def iter_content(self, chunk_size):
                yield b'data: {"choices":[{"delt'
                yield b'a":{"content":"partial"}}]}\n\n'

        chunks = list(client._iter_sse_data(FakeResponse()))
        assert len(chunks) == 1
        assert "partial" in chunks[0]

    def test_carriage_return_normalization(self, mock_config):
        client = LLMClient(mock_config)

        class FakeResponse:
            def iter_content(self, chunk_size):
                yield b'data: {"content":"test"}\r\n\r\n'

        chunks = list(client._iter_sse_data(FakeResponse()))
        assert len(chunks) == 1

    def test_empty_chunk_skipped(self, mock_config):
        client = LLMClient(mock_config)

        class FakeResponse:
            def iter_content(self, chunk_size):
                yield b""
                yield b'data: {"content":"test"}\n\n'

        chunks = list(client._iter_sse_data(FakeResponse()))
        assert len(chunks) == 1

    def test_event_without_data_skipped(self, mock_config):
        client = LLMClient(mock_config)

        class FakeResponse:
            def iter_content(self, chunk_size):
                yield b"event: ping\n\n"

        chunks = list(client._iter_sse_data(FakeResponse()))
        assert len(chunks) == 0

    def test_multi_line_data(self, mock_config):
        client = LLMClient(mock_config)

        class FakeResponse:
            def iter_content(self, chunk_size):
                yield b"data: line1\ndata: line2\n\n"

        chunks = list(client._iter_sse_data(FakeResponse()))
        assert len(chunks) == 1
        assert "line1\nline2" == chunks[0]


class TestMockDebateReply:
    def test_returns_chinese_text(self, mock_config):
        client = LLMClient(mock_config)
        messages = [
            {"role": "system", "content": "本场辩题是：AI 是否利大于弊。用户持方是：正方"},
            {"role": "user", "content": "AI 可以提升生产效率降低人力成本。"},
        ]
        reply = client._mock_debate_reply(messages)
        assert isinstance(reply, str)
        assert len(reply) > 50
        assert "AI 是否利大于弊" in reply

    def test_fallback_topic_when_no_prefix(self, mock_config):
        client = LLMClient(mock_config)
        messages = [
            {"role": "system", "content": "没有辩题的 system prompt"},
            {"role": "user", "content": "测试观点。"},
        ]
        reply = client._mock_debate_reply(messages)
        assert "当前辩题" in reply


class TestMockEvaluation:
    def test_returns_valid_json_with_required_fields(self, mock_config):
        import json

        client = LLMClient(mock_config)
        result = client._mock_evaluation([{"role": "user", "content": "test"}])
        data = json.loads(result)
        assert "logic_score" in data
        assert "evidence_score" in data
        assert "fluency_score" in data
        assert "suggestion" in data
        assert 0 <= data["logic_score"] <= 10
        assert 0 <= data["evidence_score"] <= 10
        assert 0 <= data["fluency_score"] <= 10


class TestExtractTopic:
    def test_extracts_topic_from_system_prompt(self, mock_config):
        client = LLMClient(mock_config)
        prompt = "本场辩题是：AI 是否利大于弊。用户持方是：正方，你必须坚定扮演反方。"
        topic = client._extract_topic(prompt)
        assert topic == "AI 是否利大于弊"

    def test_fallback_when_no_prefix(self, mock_config):
        client = LLMClient(mock_config)
        topic = client._extract_topic("用户持方是：反方。")
        assert topic == "当前辩题"


class TestMockMode:
    def test_stream_debate_reply_in_mock_mode(self, mock_config):
        config = {**mock_config, "LLM_PROVIDER": "mock"}
        client = LLMClient(config)
        messages = [
            {"role": "system", "content": "本场辩题是：测试辩题。用户持方是：正方"},
            {"role": "user", "content": "这是一个测试论点。"},
        ]
        chunks = list(client.stream_debate_reply(messages))
        assert len(chunks) > 0
        full = "".join(chunks)
        assert len(full) > 50

    def test_generate_debate_reply_in_mock_mode(self, mock_config):
        config = {**mock_config, "LLM_PROVIDER": "mock"}
        client = LLMClient(config)
        messages = [
            {"role": "system", "content": "辩题：测试。"},
            {"role": "user", "content": "测试。"},
        ]
        reply = client.generate_debate_reply(messages)
        assert isinstance(reply, str)
        assert len(reply) > 20

    def test_generate_evaluation_in_mock_mode(self, mock_config):
        config = {**mock_config, "LLM_PROVIDER": "mock"}
        client = LLMClient(config)
        result = client.generate_evaluation([{"role": "user", "content": "test"}])
        assert "logic_score" in result

    def test_mock_mode_when_api_key_empty(self, mock_config):
        config = {**mock_config, "LLM_API_KEY": "", "LLM_PROVIDER": "openrouter"}
        client = LLMClient(config)
        chunks = list(
            client.stream_debate_reply(
                [{"role": "system", "content": "辩题：测试。用户持方：正方"}]
            )
        )
        assert len(chunks) > 0


class TestChatCompletionOnceError:
    def test_raises_llm_client_error_on_connection_failure(self, mock_config, monkeypatch, app):
        import requests

        client = LLMClient(mock_config)

        def fake_post(*args, **kwargs):
            raise requests.ConnectionError("Connection refused")

        monkeypatch.setattr(requests, "post", fake_post)

        with app.app_context():
            with pytest.raises(LLMClientError, match="大模型服务调用失败"):
                client._chat_completion_once(
                    model="test/model",
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.7,
                    max_tokens=100,
                )

    def test_raises_on_empty_response_content(self, mock_config, monkeypatch, app):
        import requests

        client = LLMClient(mock_config)

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": ""}}]}

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            with pytest.raises(LLMClientError, match="没有返回有效文本内容"):
                client._chat_completion_once(
                    model="test/model",
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.7,
                    max_tokens=100,
                )

    def test_raises_on_malformed_response(self, mock_config, monkeypatch, app):
        import requests

        client = LLMClient(mock_config)

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"unexpected": "structure"}

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            with pytest.raises(LLMClientError, match="返回格式异常"):
                client._chat_completion_once(
                    model="test/model",
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.7,
                    max_tokens=100,
                )


class TestStreamFallback:
    def test_stream_tries_fallback_models(self, mock_config, monkeypatch, app):
        import requests

        config = {
            **mock_config,
            "LLM_FALLBACK_MODELS": ["fallback/model:free"],
        }
        client = LLMClient(config)
        call_order = []

        def fake_post(url, headers, json, stream, timeout):
            call_order.append(json["model"])
            raise requests.ConnectionError("fail")

        monkeypatch.setattr(requests, "post", fake_post)

        with app.app_context():
            generator = client._chat_completion_stream(
                messages=[{"role": "user", "content": "hi"}],
                temperature=0.7,
                max_tokens=100,
                model="primary/model:free",
            )

            with pytest.raises(LLMClientError):
                list(generator)

        assert call_order[0] == "primary/model:free"
        assert "fallback/model:free" in call_order
        assert len(call_order) >= 3

    def test_stream_does_not_fallback_after_emitting(self, mock_config, monkeypatch, app):
        import requests

        config = {
            **mock_config,
            "LLM_FALLBACK_MODELS": ["fallback/model:free"],
        }
        client = LLMClient(config)
        attempts = []

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def iter_content(self, chunk_size):
                attempts.append("called")
                yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
                raise requests.ConnectionError("mid-stream failure")

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            generator = client._chat_completion_stream(
                messages=[{"role": "user", "content": "hi"}],
                temperature=0.7,
                max_tokens=100,
                model="primary/model:free",
            )

            chunks = []
            with pytest.raises(LLMClientError):
                for chunk in generator:
                    chunks.append(chunk)

        assert len(chunks) == 1
        assert len(attempts) == 1  # No fallback attempted after emitting


class TestCompletionFallback:
    def test_completion_tries_all_models_then_raises(self, mock_config, monkeypatch, app):
        import requests

        config = {
            **mock_config,
            "LLM_FALLBACK_MODELS": ["fb1/model:free", "fb2/model:free"],
        }
        client = LLMClient(config)
        call_order = []

        def fake_post(*args, **kwargs):
            call_order.append(kwargs.get("json", {}).get("model", "unknown"))
            raise requests.ConnectionError("fail")

        monkeypatch.setattr(requests, "post", fake_post)

        with app.app_context():
            with pytest.raises(LLMClientError):
                client._chat_completion(
                    messages=[{"role": "user", "content": "hi"}],
                    temperature=0.7,
                    max_tokens=100,
                    model="primary/model:free",
                )

        assert call_order[0] == "primary/model:free"
        assert "fb1/model:free" in call_order
        assert "fb2/model:free" in call_order
        assert len(call_order) >= 4

    def test_completion_returns_first_success(self, mock_config, monkeypatch, app):
        import requests

        config = {
            **mock_config,
            "LLM_FALLBACK_MODELS": ["fb1/model:free"],
        }
        client = LLMClient(config)
        call_count = {"count": 0}

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                call_count["count"] += 1
                return {
                    "choices": [{"message": {"content": "success from model " + str(call_count["count"])}}]
                }

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            result = client._chat_completion(
                messages=[{"role": "user", "content": "hi"}],
                temperature=0.7,
                max_tokens=100,
                model="primary/model:free",
            )

        assert "success from model 1" == result
        assert call_count["count"] == 1
