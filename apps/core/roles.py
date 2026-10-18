"""Staff roles, implemented as Django groups.

sync_roles() runs after every migrate. It only adds groups and permissions and never removes
them, so permissions an admin grants in the admin UI are kept.
"""

from typing import Any

from django.contrib.auth.models import Group, Permission

ADMIN = "admin"
PROVIDER = "provider"
FRONT_DESK = "front_desk"
BILLING = "billing"

_EVERYONE = ["links.view_link", "ai.use_ai"]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    ADMIN: [
        *_EVERYONE,
        "links.add_link",
        "links.change_link",
        "links.delete_link",
        "core.view_auditevent",
        "ai.view_airequest",
    ],
    PROVIDER: [*_EVERYONE],
    FRONT_DESK: [*_EVERYONE],
    BILLING: [*_EVERYONE],
}


def sync_roles(**_kwargs: Any) -> None:
    for role, perms in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        for perm in perms:
            app_label, codename = perm.split(".", 1)
            permission = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            # Permissions for apps not migrated yet appear on a later post_migrate pass.
            if permission is not None:
                group.permissions.add(permission)
