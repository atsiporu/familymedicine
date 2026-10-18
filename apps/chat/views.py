import json
from collections.abc import AsyncIterator

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from pydantic import BaseModel, Field, ValidationError

from apps.ai import gateway
from apps.ai.client import ChatMessage, OllamaError
from apps.core.models import User

MAX_MESSAGES = 50
MAX_TOTAL_CHARS = 100_000


class ChatPayload(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)


@permission_required("ai.use_ai", raise_exception=True)
def chat_page(request: HttpRequest) -> HttpResponse:
    return render(request, "chat/chat.html", {"default_model": settings.AI_DEFAULT_MODEL})


@require_GET
@permission_required("ai.use_ai", raise_exception=True)
async def model_list(request: HttpRequest) -> JsonResponse:
    try:
        models = await gateway.available_models()
    except OllamaError:
        return JsonResponse({"error": "The AI service is unavailable right now."}, status=503)
    return JsonResponse(
        {
            "models": [m.name for m in models],
            "default": settings.AI_DEFAULT_MODEL,
        }
    )


def _sse(event: gateway.GatewayEvent) -> str:
    data = json.dumps({"text": event.text, "position": event.position})
    return f"event: {event.kind}\ndata: {data}\n\n"


@require_POST
@permission_required("ai.use_ai", raise_exception=True)
async def chat_stream(request: HttpRequest) -> HttpResponseBase:
    try:
        payload = ChatPayload.model_validate_json(request.body)
    except ValidationError:
        return JsonResponse({"error": "Invalid request."}, status=400)
    if sum(len(m.content) for m in payload.messages) > MAX_TOTAL_CHARS:
        return JsonResponse({"error": "Conversation is too long. Start a new chat."}, status=400)

    user = await request.auser()
    assert isinstance(user, User)

    async def events() -> AsyncIterator[str]:
        async for event in gateway.stream_chat(
            user=user, tool="chat", model=payload.model, messages=payload.messages
        ):
            yield _sse(event)

    response = StreamingHttpResponse(events(), content_type="text/event-stream")
    response["Cache-Control"] = "no-store"
    response["X-Accel-Buffering"] = "no"
    return response
