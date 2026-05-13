from __future__ import annotations

import json

import requests
from flask import current_app

from app.utils.errors import LLMClientError


class LLMClient:
    def __init__(self, config: dict):
        self.provider = config["LLM_PROVIDER"]
        self.api_base_url = config["LLM_API_BASE_URL"].rstrip("/")
        self.api_key = config["LLM_API_KEY"]
        self.model = config["LLM_MODEL"]
        self.models = [self.model, *config.get("LLM_FALLBACK_MODELS", [])]
        self.timeout_seconds = config["LLM_TIMEOUT_SECONDS"]
        self.mock_chunk_size = config["MOCK_STREAM_CHUNK_SIZE"]
        self.debate_max_tokens = config.get("LLM_DEBATE_MAX_TOKENS", 320)
        self.evaluation_max_tokens = config.get("LLM_EVALUATION_MAX_TOKENS", 500)
        self.reasoning_effort = config.get("LLM_REASONING_EFFORT", "none")
        self.openrouter_http_referer = config.get("OPENROUTER_HTTP_REFERER", "")
        self.openrouter_app_title = config.get("OPENROUTER_APP_TITLE", "AI Debate Coach")

    def stream_debate_reply(self, messages: list[dict], model: str | None = None):
        if self.provider == "mock" or not self.api_key:
            text = self._mock_debate_reply(messages)
            for index in range(0, len(text), self.mock_chunk_size):
                yield text[index : index + self.mock_chunk_size]
            return

        yield from self._chat_completion_stream(
            messages,
            temperature=0.7,
            max_tokens=self.debate_max_tokens,
            model=model,
        )

    def generate_debate_reply(self, messages: list[dict], model: str | None = None) -> str:
        if self.provider == "mock" or not self.api_key:
            return self._mock_debate_reply(messages)
        return self._chat_completion(
            messages,
            temperature=0.7,
            max_tokens=self.debate_max_tokens,
            model=model,
        )

    def generate_evaluation(self, messages: list[dict], model: str | None = None) -> str:
        if self.provider == "mock" or not self.api_key:
            return self._mock_evaluation(messages)
        return self._chat_completion(
            messages,
            temperature=0.2,
            max_tokens=self.evaluation_max_tokens,
            model=model,
        )

    def _chat_completion(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> str:
        last_error: LLMClientError | None = None
        for current_model in self._models_for(model):
            try:
                return self._chat_completion_once(
                    model=current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except LLMClientError as exc:
                current_app.logger.warning(
                    "LLM request failed for model %s: %s",
                    current_model,
                    exc.message,
                )
                last_error = exc

        if last_error is not None:
            raise last_error

        raise LLMClientError("未配置可用的大模型。")

    def _chat_completion_once(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        url = f"{self.api_base_url}/chat/completions"
        headers = self._build_headers()
        payload = self._build_payload(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"].get("content") or ""
            if not content.strip():
                raise LLMClientError("大模型没有返回有效文本内容。")
            return content.strip()
        except requests.RequestException as exc:
            current_app.logger.exception("LLM request failed: %s", exc)
            raise LLMClientError("大模型服务调用失败，请稍后重试。") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            current_app.logger.exception("Unexpected LLM response: %s", exc)
            raise LLMClientError("大模型返回格式异常。") from exc

    def _chat_completion_stream(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ):
        last_error: LLMClientError | None = None
        for current_model in self._models_for(model):
            emitted = False
            try:
                for chunk in self._chat_completion_stream_once(
                    model=current_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    emitted = True
                    yield chunk
                return
            except LLMClientError as exc:
                if emitted:
                    raise
                current_app.logger.warning(
                    "LLM stream request failed for model %s: %s",
                    current_model,
                    exc.message,
                )
                last_error = exc

        if last_error is not None:
            raise last_error

        raise LLMClientError("未配置可用的大模型。")

    def _chat_completion_stream_once(
        self,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ):
        url = f"{self.api_base_url}/chat/completions"
        payload = self._build_payload(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }
        )
        received_content = False

        try:
            with requests.post(
                url,
                headers=self._build_headers(),
                json=payload,
                stream=True,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()

                for data_text in self._iter_sse_data(response):
                    if data_text == "[DONE]":
                        break

                    data = json.loads(data_text)
                    if "error" in data:
                        message = data["error"].get("message") or "大模型流式调用失败。"
                        raise LLMClientError(message)

                    delta = data["choices"][0].get("delta", {})
                    chunk = delta.get("content") or ""
                    if chunk:
                        received_content = True
                        yield chunk

            if not received_content:
                raise LLMClientError("大模型没有返回有效反驳内容。")
        except requests.RequestException as exc:
            current_app.logger.exception("LLM stream request failed: %s", exc)
            raise LLMClientError("大模型流式调用失败，请稍后重试。") from exc
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            current_app.logger.exception("Unexpected LLM stream response: %s", exc)
            raise LLMClientError("大模型流式返回格式异常。") from exc

    def _iter_sse_data(self, response):
        buffer = ""
        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue

            buffer += chunk.decode("utf-8", errors="replace")
            buffer = buffer.replace("\r\n", "\n")

            while "\n\n" in buffer:
                raw_event, buffer = buffer.split("\n\n", maxsplit=1)
                data_lines = []
                for line in raw_event.split("\n"):
                    if line.startswith("data:"):
                        data_lines.append(line.removeprefix("data:").lstrip())

                if data_lines:
                    yield "\n".join(data_lines).strip()

    def _build_headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if "openrouter.ai" in self.api_base_url:
            if self.openrouter_http_referer:
                headers["HTTP-Referer"] = self.openrouter_http_referer
            if self.openrouter_app_title:
                headers["X-Title"] = self.openrouter_app_title

        return headers

    def _build_payload(self, payload: dict) -> dict:
        if "openrouter.ai" in self.api_base_url and self.reasoning_effort:
            payload["reasoning"] = {
                "effort": self.reasoning_effort,
                "exclude": True,
            }
            payload["include_reasoning"] = False

        return payload

    def _models_for(self, model: str | None = None) -> list[str]:
        preferred_model = (model or self.model).strip()
        ordered_models = [preferred_model, *self.models]
        unique_models: list[str] = []
        for item in ordered_models:
            if item and item not in unique_models:
                unique_models.append(item)
        return unique_models

    def _mock_debate_reply(self, messages: list[dict]) -> str:
        user_message = messages[-1]["content"].strip()
        topic = self._extract_topic(messages[0]["content"])
        snippet = user_message[:60]
        return (
            f"如果站在对方立场审视，你这段论证在“{topic}”上仍有明显缺口。"
            f"你强调了“{snippet}”，但没有证明这一判断为何必然成立，"
            "论据和因果链条之间也缺少关键连接。若核心前提无法自证，结论就更像态度表达而非完整论证。"
            "你需要补上可验证事实，并先回应最强反例。"
        )

    def _mock_evaluation(self, messages: list[dict]) -> str:
        content = {
            "logic_score": 7,
            "evidence_score": 6,
            "fluency_score": 7,
            "suggestion": "你的立场表达清楚，但论据还不够扎实。下一次训练优先补充可验证事实，并把“观点-理由-例证-结论”链条讲完整。",
        }
        return json.dumps(content, ensure_ascii=False)

    def _extract_topic(self, system_prompt: str) -> str:
        prefix = "本场辩题是："
        if prefix not in system_prompt:
            return "当前辩题"
        return system_prompt.split(prefix, maxsplit=1)[1].split("。", maxsplit=1)[0]
