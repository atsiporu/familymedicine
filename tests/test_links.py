import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from apps.core import roles
from apps.links.models import Link
from tests.conftest import MakeUser

pytestmark = pytest.mark.django_db


def test_links_grouped_by_category(client: Client, make_user: MakeUser) -> None:
    Link.objects.create(title="Test EMR", url="https://emr.example.com", category="EMR")
    Link.objects.create(title="Hidden", url="https://hidden.example.com", is_active=False)
    client.force_login(make_user(role=roles.BILLING))
    response = client.get(reverse("links:list"))
    assert response.status_code == 200
    assert b"Test EMR" in response.content
    assert b"Hidden" not in response.content


def test_links_require_permission(client: Client, make_user: MakeUser) -> None:
    client.force_login(make_user())
    assert client.get(reverse("links:list")).status_code == 403


def test_seed_links_is_idempotent() -> None:
    call_command("seed_links")
    count = Link.objects.count()
    call_command("seed_links")
    assert Link.objects.count() == count > 0
