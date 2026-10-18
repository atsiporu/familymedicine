from collections.abc import AsyncIterator, Callable

import pytest
from asgiref.sync import sync_to_async
from django.db import connections
from django.test import AsyncClient
from django.test.utils import override_settings
from django.urls import reverse

from apps.ai import gateway
from apps.ai.client import ChatMessage, OllamaClient
from apps.ai.models import AiRequest
from apps.core import roles
from tests.conftest import MakeUser

# Async ORM calls run in another thread, so these tests need real transactions.
pytestmark = pytest.mark.django_db(transaction=True)

FakeOllama = Callable[..., OllamaClient]


@pytest.fixture(autouse=True)
async def _close_async_db_connections() -> AsyncIterator[None]:
    # Async ORM calls open a connection in asgiref's worker thread. Close it so the test
    # database can be dropped at teardown.
    yield
    await sync_to_async(connections.close_all)()
PROMPT = [ChatMessage(role="user", content="What is the adult flu vaccine schedule?")]


async def _collect(**kwargs: object) -> list[gateway.GatewayEvent]:
    return [event async for event in gateway.stream_chat(**kwargs)]  # type: ignore[arg-type]


async def test_stream_records_metadata_but_not_content(
    make_user: MakeUser, fake_ollama: FakeOllama
) -> None:
    user = await sync_to_async(make_user)()
    events = await _collect(user=user, tool="chat", model="test-model:1b", messages=PROMPT)

    kinds = [e.kind for e in events]
    assert kinds[0] == "started" and kinds[1] == "thinking" and kinds[-1] == "done"
    assert "".join(e.text for e in events if e.kind == "token") == "Hello, world"

    record = await AiRequest.objects.aget()
    assert record.status == AiRequest.Status.DONE
    assert record.prompt_chars == len(PROMPT[0].content)
    assert record.response_chars == len("Hello, world")
    assert (record.prompt_tokens, record.response_tokens) == (7, 3)
    assert record.prompt_text == "" and record.response_text == ""


@override_settings(AI_STORE_CONTENT=True)
async def test_content_stored_only_when_enabled(
    make_user: MakeUser, fake_ollama: FakeOllama
) -> None:
    user = await sync_to_async(make_user)()
    await _collect(user=user, tool="chat", model="test-model:1b", messages=PROMPT)
    record = await AiRequest.objects.aget()
    assert "flu vaccine" in record.prompt_text
    assert record.response_text == "Hello, world"


async def test_unknown_model_is_rejected(make_user: MakeUser, fake_ollama: FakeOllama) -> None:
    user = await sync_to_async(make_user)()
    events = await _collect(user=user, tool="chat", model="not-installed", messages=PROMPT)
    assert [e.kind for e in events] == ["error"]
    assert (await AiRequest.objects.aget()).status == AiRequest.Status.ERROR


@override_settings(AI_ALLOWED_MODELS=["allowed:1b"])
async def test_allow_list_filters_models(fake_ollama: FakeOllama) -> None:
    fake_ollama(models=["allowed:1b", "other:70b"])
    assert [m.name for m in await gateway.available_models()] == ["allowed:1b"]


async def test_ollama_failure_is_reported(make_user: MakeUser, fake_ollama: FakeOllama) -> None:
    fake_ollama(chat_status=500)
    user = await sync_to_async(make_user)()
    events = await _collect(user=user, tool="chat", model="test-model:1b", messages=PROMPT)
    assert events[-1].kind == "error"
    record = await AiRequest.objects.aget()
    assert record.status == AiRequest.Status.ERROR
    assert "500" in record.error


async def test_chat_endpoint_streams_sse(make_user: MakeUser, fake_ollama: FakeOllama) -> None:
    user = await sync_to_async(make_user)(role=roles.PROVIDER)
    client = AsyncClient()
    await client.aforce_login(user)
    response = await client.post(
        reverse("chat:stream"),
        {"model": "test-model:1b", "messages": [{"role": "user", "content": "Hi"}]},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "text/event-stream"
    body = b"".join([chunk async for chunk in response.streaming_content]).decode()  # type: ignore[attr-defined]
    assert "event: token" in body and "event: done" in body


async def test_chat_endpoint_requires_permission(make_user: MakeUser) -> None:
    user = await sync_to_async(make_user)()
    client = AsyncClient()
    await client.aforce_login(user)
    response = await client.post(
        reverse("chat:stream"), {"model": "x", "messages": []}, content_type="application/json"
    )
    assert response.status_code == 403


async def test_chat_endpoint_validates_payload(make_user: MakeUser) -> None:
    user = await sync_to_async(make_user)(role=roles.PROVIDER)
    client = AsyncClient()
    await client.aforce_login(user)
    response = await client.post(
        reverse("chat:stream"), {"model": "x", "messages": []}, content_type="application/json"
    )
    assert response.status_code == 400
