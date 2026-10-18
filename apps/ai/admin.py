from django.contrib import admin
from django.http import HttpRequest

from apps.ai.models import AiRequest


@admin.register(AiRequest)
class AiRequestAdmin(admin.ModelAdmin[AiRequest]):
    list_display = [
        "queued_at",
        "user",
        "tool",
        "model",
        "status",
        "prompt_tokens",
        "response_tokens",
    ]
    list_filter = ["status", "tool", "model"]
    date_hierarchy = "queued_at"
    exclude = ["prompt_text", "response_text"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: AiRequest | None = None) -> bool:
        return False
