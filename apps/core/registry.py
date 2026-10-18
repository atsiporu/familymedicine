"""Tool registry: each tool app registers itself here from its AppConfig.ready().

The dashboard and navigation are built from the registered tools, filtered by permission.
"""

from dataclasses import dataclass

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.urls import reverse

from apps.core.models import User


@dataclass(frozen=True)
class Tool:
    slug: str
    name: str
    description: str
    url_name: str
    icon: str
    # "app_label.codename"; None means any signed-in user.
    permission: str | None = None
    order: int = 100

    @property
    def url(self) -> str:
        return reverse(self.url_name)


_tools: dict[str, Tool] = {}


def register(tool: Tool) -> None:
    if tool.slug in _tools and _tools[tool.slug] != tool:
        raise ValueError(f"Tool slug already registered: {tool.slug}")
    _tools[tool.slug] = tool


def all_tools() -> list[Tool]:
    return sorted(_tools.values(), key=lambda t: (t.order, t.name))


def tools_for(user: AbstractBaseUser | AnonymousUser) -> list[Tool]:
    if not isinstance(user, User) or not user.is_active:
        return []
    return [t for t in all_tools() if t.permission is None or user.has_perm(t.permission)]
