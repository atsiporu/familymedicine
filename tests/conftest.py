"""Shared fixtures. All test data is synthetic. Never use real patient data in tests."""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from django.contrib.auth.models import Group

from apps.ai import gateway
from apps.ai.client import OllamaClient
from apps.core.models import User

MakeUser = Callable[..., User]


@pytest.fixture
def make_user(db: None) -> MakeUser:
    def _make(username: str = "test.user", role: str | None = None, **extra: Any) -> User:
        user = User.objects.create_user(
            username=username, password="test-password-123", first_name="Test", **extra
        )
        if role:
            user.groups.add(Group.objects.get(name=role))
        return user

    return _make


def fake_ollama_transport(
    models: list[str] | None = None,
    tokens: list[str] | None = None,
    chat_status: int = 200,
) -> httpx.MockTransport:
    models = models if models is not None else ["test-model:1b"]
    tokens = tokens if tokens is not None else ["Hello", ", ", "world"]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": m, "size": 1} for m in models]})
        if request.url.path == "/api/chat":
            if chat_status != 200:
                return httpx.Response(chat_status, text="model failed to load")
            lines = [{"message": {"thinking": "hmm"}, "done": False}]
            lines += [{"message": {"content": t}, "done": False} for t in tokens]
            lines.append({"done": True, "prompt_eval_count": 7, "eval_count": len(tokens)})
            body = "\n".join(json.dumps(line) for line in lines) + "\n"
            return httpx.Response(200, text=body)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.fixture
def fake_ollama(monkeypatch: pytest.MonkeyPatch) -> Callable[..., OllamaClient]:
    """Route the gateway to a fake Ollama. Call the fixture to customize the fake."""

    def _install(**kwargs: object) -> OllamaClient:
        client = OllamaClient("http://ollama.test", transport=fake_ollama_transport(**kwargs))  # type: ignore[arg-type]
        monkeypatch.setattr(gateway, "get_client", lambda: client)
        return client

    _install()
    return _install


@pytest.fixture(autouse=True)
def _fresh_gpu_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    # Each test gets its own queue, bound to that test's event loop.
    monkeypatch.setattr(gateway, "_queue", None)
