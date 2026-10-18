import pytest
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.core import roles
from apps.core.models import AuditEvent
from apps.core.registry import tools_for
from tests.conftest import MakeUser

pytestmark = pytest.mark.django_db


def test_roles_are_created_with_permissions() -> None:
    assert set(Group.objects.values_list("name", flat=True)) >= set(roles.ROLE_PERMISSIONS)
    provider = Group.objects.get(name=roles.PROVIDER)
    codenames = set(provider.permissions.values_list("codename", flat=True))
    assert {"view_link", "use_ai"} <= codenames


def test_anonymous_user_is_sent_to_login(client: Client) -> None:
    response = client.get(reverse("dashboard"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


def test_login_page_is_public(client: Client) -> None:
    assert client.get(reverse("login")).status_code == 200


def test_dashboard_lists_tools_for_role(client: Client, make_user: MakeUser) -> None:
    client.force_login(make_user(role=roles.FRONT_DESK))
    response = client.get(reverse("dashboard"))
    assert response.status_code == 200
    assert b"Quick Links" in response.content
    assert b"AI Assistant" in response.content


def test_user_without_role_sees_no_tools(make_user: MakeUser) -> None:
    assert tools_for(make_user()) == []


def test_login_and_logout_are_audited(client: Client, make_user: MakeUser) -> None:
    make_user(username="test.provider", role=roles.PROVIDER)
    client.post(reverse("login"), {"username": "test.provider", "password": "test-password-123"})
    client.post(reverse("logout"))
    actions = list(AuditEvent.objects.order_by("created_at").values_list("action", flat=True))
    assert actions == ["auth.login", "auth.logout"]


def test_failed_login_audit_never_stores_password(client: Client) -> None:
    client.post(reverse("login"), {"username": "nobody", "password": "s3cret-guess"})
    event = AuditEvent.objects.get(action="auth.login_failed")
    assert event.detail == {"username": "nobody"}
    assert "s3cret-guess" not in str(event.detail)
