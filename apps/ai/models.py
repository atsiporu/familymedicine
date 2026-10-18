from django.conf import settings
from django.db import models


class AiRequest(models.Model):
    """One LLM generation. Metadata only unless settings.AI_STORE_CONTENT is on."""

    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        DONE = "done"
        ERROR = "error"
        CANCELLED = "cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    tool = models.CharField(max_length=50)
    model = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    queued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    prompt_chars = models.PositiveIntegerField(default=0)
    response_chars = models.PositiveIntegerField(default=0)
    prompt_tokens = models.PositiveIntegerField(null=True, blank=True)
    response_tokens = models.PositiveIntegerField(null=True, blank=True)
    error = models.CharField(max_length=500, blank=True)
    # Only filled when AI_STORE_CONTENT is enabled. May contain PHI.
    prompt_text = models.TextField(blank=True)
    response_text = models.TextField(blank=True)

    class Meta:
        ordering = ["-queued_at"]
        permissions = [("use_ai", "Can use AI tools")]

    def __str__(self) -> str:
        return f"{self.tool}/{self.model} {self.status}"
