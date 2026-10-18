"""AI gateway: the single path from portal tools to the local LLM.

It serializes GPU work through a queue, enforces the model allow-list, and records every
request in AiRequest. Prompt/response text is stored only when AI_STORE_CONTENT is enabled.

The queue is per process, so run the portal with a single uvicorn worker. Async views handle
many concurrent users in one process.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from django.conf import settings
from django.utils import timezone

from apps.ai.client import ChatMessage, ModelInfo, OllamaClient, OllamaError
from apps.ai.models import AiRequest
from apps.core.models import User

logger = logging.getLogger(__name__)

EventKind = Literal["queued", "started", "thinking", "token", "done", "error"]


@dataclass(frozen=True)
class GatewayEvent:
    kind: EventKind
    text: str = ""
    position: int = 0


class GpuQueue:
    """Limits concurrent generations and tracks how many are waiting."""

    def __init__(self, slots: int) -> None:
        self._slots = slots
        self._semaphore: asyncio.Semaphore | None = None
        self.waiting = 0

    @property
    def semaphore(self) -> asyncio.Semaphore:
        # Created lazily so it binds to the server's running event loop.
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._slots)
        return self._semaphore


_queue: GpuQueue | None = None


def get_queue() -> GpuQueue:
    global _queue
    if _queue is None:
        _queue = GpuQueue(settings.AI_MAX_CONCURRENT)
    return _queue


def get_client() -> OllamaClient:
    return OllamaClient(settings.OLLAMA_URL)


async def available_models(client: OllamaClient | None = None) -> list[ModelInfo]:
    models = await (client or get_client()).list_models()
    allowed = settings.AI_ALLOWED_MODELS
    if allowed:
        models = [m for m in models if m.name in allowed]
    return sorted(models, key=lambda m: m.name)


async def stream_chat(
    *,
    user: User,
    tool: str,
    model: str,
    messages: list[ChatMessage],
    client: OllamaClient | None = None,
) -> AsyncIterator[GatewayEvent]:
    client = client or get_client()
    queue = get_queue()
    store = settings.AI_STORE_CONTENT
    record = await AiRequest.objects.acreate(
        user=user,
        tool=tool,
        model=model,
        prompt_chars=sum(len(m.content) for m in messages),
        prompt_text="\n\n".join(f"[{m.role}] {m.content}" for m in messages) if store else "",
    )
    response_parts: list[str] = []
    thinking_announced = False

    async def finish(status: AiRequest.Status, error: str = "") -> None:
        record.status = status
        record.error = error[:500]
        record.finished_at = timezone.now()
        record.response_chars = sum(len(p) for p in response_parts)
        if store:
            record.response_text = "".join(response_parts)
        await record.asave()

    try:
        model_names = {m.name for m in await available_models(client)}
        if model not in model_names:
            await finish(AiRequest.Status.ERROR, "model not allowed")
            yield GatewayEvent("error", "That model is not available.")
            return

        queue.waiting += 1
        try:
            if queue.semaphore.locked():
                yield GatewayEvent("queued", position=queue.waiting)
            await queue.semaphore.acquire()
        finally:
            queue.waiting -= 1

        try:
            record.status = AiRequest.Status.RUNNING
            record.started_at = timezone.now()
            await record.asave(update_fields=["status", "started_at"])
            yield GatewayEvent("started")

            async for chunk in client.chat_stream(model, messages):
                if chunk.message is not None:
                    if chunk.message.thinking and not thinking_announced:
                        thinking_announced = True
                        yield GatewayEvent("thinking")
                    if chunk.message.content:
                        response_parts.append(chunk.message.content)
                        yield GatewayEvent("token", chunk.message.content)
                if chunk.done:
                    record.prompt_tokens = chunk.prompt_eval_count
                    record.response_tokens = chunk.eval_count
        finally:
            queue.semaphore.release()

        await finish(AiRequest.Status.DONE)
        yield GatewayEvent("done")
    except OllamaError as exc:
        # The error text comes from Ollama/httpx, not from the prompt, so it is safe to log.
        logger.warning("AI request %s failed: %s", record.pk, exc)
        await finish(AiRequest.Status.ERROR, str(exc))
        yield GatewayEvent("error", "The AI service is unavailable right now.")
    except asyncio.CancelledError, GeneratorExit:
        # Client disconnected (closed the tab or pressed stop).
        await asyncio.shield(finish(AiRequest.Status.CANCELLED))
        raise
