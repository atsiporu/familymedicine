from django.http import HttpRequest

from apps.core.registry import Tool, tools_for


def tools(request: HttpRequest) -> dict[str, list[Tool]]:
    return {"nav_tools": tools_for(request.user)}
