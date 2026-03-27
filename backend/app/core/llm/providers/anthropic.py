import json
import logging
from typing import Any, AsyncGenerator, Dict, List

import httpx

from app.core.llm.base import BaseLLMProvider, LLMRequest, LLMResponse, LLMStreamChunk

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider, including Anthropic-compatible endpoints."""

    def _resolve_messages_url(self) -> str:
        """Allow callers to pass either a root URL or the full messages endpoint."""
        if not self.base_url:
            return "https://api.anthropic.com/v1/messages"

        url = self.base_url.rstrip("/")
        if url.endswith("/messages"):
            return url
        if url.endswith("/v1"):
            return f"{url}/messages"
        return f"{url}/v1/messages"

    def _build_text_content(self, content: str) -> List[Dict[str, str]]:
        return [{"type": "text", "text": content}]

    def _build_payload(self, request: LLMRequest) -> Dict[str, Any]:
        system_prompt = ""
        messages: List[Dict[str, Any]] = []

        for message in request.messages:
            if message.role == "system":
                system_prompt = f"{system_prompt}\n{message.content}".strip() if system_prompt else message.content
                continue

            messages.append({
                "role": message.role,
                "content": self._build_text_content(message.content),
            })

        payload: Dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": False,
            **request.extra_params,
        }

        if system_prompt:
            payload["system"] = system_prompt
        if request.stop:
            payload["stop_sequences"] = request.stop

        return payload

    async def chat(self, request: LLMRequest) -> LLMResponse:
        url = self._resolve_messages_url()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version or "2023-06-01",
            "content-type": "application/json",
        }
        payload = self._build_payload(request)

        timeout = httpx.Timeout(timeout=120.0, connect=30.0, read=60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        content = ""
        reasoning_content = ""
        for item in data.get("content", []):
            item_type = item.get("type")
            if item_type == "text":
                content += item.get("text", "")
            elif item_type == "thinking":
                reasoning_content += item.get("thinking", "")

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            role="assistant",
            model=data.get("model", request.model),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            reasoning_content=reasoning_content or None,
            finish_reason=data.get("stop_reason"),
            raw_response=data,
        )

    async def chat_stream(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        url = self._resolve_messages_url()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version or "2023-06-01",
            "content-type": "application/json",
        }
        payload = self._build_payload(request)
        payload["stream"] = True

        timeout = httpx.Timeout(timeout=120.0, connect=30.0, read=60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].lstrip()
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = data.get("type")
                    if event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield LLMStreamChunk(content_delta=delta.get("text", ""))
                        elif delta.get("type") == "thinking_delta":
                            yield LLMStreamChunk(reasoning_delta=delta.get("thinking", ""))
                    elif event_type == "message_delta":
                        yield LLMStreamChunk(
                            finish_reason=data.get("delta", {}).get("stop_reason"),
                            usage=data.get("usage"),
                        )

    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        raise NotImplementedError("AnthropicProvider does not implement embedding requests")

    async def rerank(self, query: str, texts: List[str], model: str, top_n: int) -> List[Dict[str, Any]]:
        raise NotImplementedError("AnthropicProvider does not implement rerank requests")

    def get_token_count(self, text: str) -> int:
        return len(text) // 2 + (len(text.encode("utf-8")) - len(text)) // 3
