from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Staff account. Roles are Django groups (see apps.core.roles)."""

    class Meta:
        ordering = ["username"]


class AuditEvent(models.Model):
    """Append-only record of who did what. Never store patient data or prompt text here."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    # Kept separately so the record survives if the account is deleted.
    actor_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=100, db_index=True)
    target = models.CharField(max_length=255, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.actor_username or '-'} {self.action}"
