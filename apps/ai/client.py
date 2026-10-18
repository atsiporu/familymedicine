"""Thin async client for the local Ollama server. Only the gateway should use it directly."""

import json
from collections.abc import AsyncIterator
from typing import Literal

import httpx
from pydantic import BaseModel


class OllamaError(Exception):
    pass


class ModelInfo(BaseModel):
    name: str
    size: int = 0


class _TagsResponse(BaseModel):
    models: list[ModelInfo]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class _ChunkMessage(BaseModel):
    content: str = ""
    thinking: str | None = None


class ChatChunk(BaseModel):
    message: _ChunkMessage | None = None
    done: bool = False
    error: str | None = None
    eval_count: int | None = None
    prompt_eval_count: int | None = None


class OllamaClient:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    def _client(self, read_timeout: float | None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            transport=self._transport,
            timeout=httpx.Timeout(10.0, read=read_timeout),
        )

    async def list_models(self) -> list[ModelInfo]:
        try:
            async with self._client(read_timeout=10.0) as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama unavailable: {exc.__class__.__name__}") from exc
        return _TagsResponse.model_validate(response.json()).models

    async def chat_stream(
        self, model: str, messages: list[ChatMessage]
    ) -> AsyncIterator[ChatChunk]:
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "stream": True,
        }
        try:
            # Large models can take minutes to load and think: no read timeout while streaming.
            async with (
                self._client(read_timeout=None) as client,
                client.stream("POST", "/api/chat", json=payload) as response,
            ):
                if response.status_code != 200:
                    body = (await response.aread()).decode(errors="replace")[:300]
                    raise OllamaError(f"Ollama returned {response.status_code}: {body}")
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = ChatChunk.model_validate(json.loads(line))
                    if chunk.error:
                        raise OllamaError(chunk.error)
                    yield chunk
                    if chunk.done:
                        return
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama unavailable: {exc.__class__.__name__}") from exc
