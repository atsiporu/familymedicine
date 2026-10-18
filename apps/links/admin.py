from django.contrib import admin

from apps.links.models import Link


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin[Link]):
    list_display = ["title", "category", "url", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["title", "url", "description"]
