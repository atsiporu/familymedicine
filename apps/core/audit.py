"""Audit logging helpers.

Usage:
    audit.record("links.opened", request=request, target=str(link.pk))
    await audit.arecord("ai.request", user=user, detail={"model": model})
"""

from typing import Any

from django.http import HttpRequest

from apps.core.models import AuditEvent, User


def _client_ip(request: HttpRequest | None) -> str | None:
    if request is None:
        return None
    # Caddy sets X-Forwarded-For; it is the only thing allowed to reach the app.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    return ip or None


def _build(
    action: str,
    request: HttpRequest | None,
    user: User | None,
    target: str,
    detail: dict[str, Any] | None,
) -> AuditEvent:
    if user is None and request is not None and request.user.is_authenticated:
        assert isinstance(request.user, User)
        user = request.user
    return AuditEvent(
        actor=user,
        actor_username=user.username if user else "",
        action=action,
        target=target,
        detail=detail or {},
        ip_address=_client_ip(request),
    )


def record(
    action: str,
    *,
    request: HttpRequest | None = None,
    user: User | None = None,
    target: str = "",
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    event = _build(action, request, user, target, detail)
    event.save()
    return event


async def arecord(
    action: str,
    *,
    request: HttpRequest | None = None,
    user: User | None = None,
    target: str = "",
    detail: dict[str, Any] | None = None,
) -> AuditEvent:
    event = _build(action, request, user, target, detail)
    await event.asave()
    return event
