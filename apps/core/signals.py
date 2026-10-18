from typing import Any

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.http import HttpRequest

from apps.core import audit
from apps.core.models import User


@receiver(user_logged_in)
def _on_login(sender: Any, request: HttpRequest, user: User, **kwargs: Any) -> None:
    audit.record("auth.login", request=request, user=user)


@receiver(user_logged_out)
def _on_logout(sender: Any, request: HttpRequest, user: User | None, **kwargs: Any) -> None:
    audit.record("auth.logout", request=request, user=user)


@receiver(user_login_failed)
def _on_login_failed(
    sender: Any, credentials: dict[str, Any], request: HttpRequest | None = None, **kwargs: Any
) -> None:
    # Only the attempted username; credentials also hold the password, which is never stored.
    audit.record(
        "auth.login_failed",
        request=request,
        detail={"username": str(credentials.get("username", ""))[:150]},
    )
