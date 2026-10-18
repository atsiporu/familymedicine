from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
    verbose_name = "Core"

    def ready(self) -> None:
        from apps.core import roles, signals  # noqa: F401  (signals connects auth audit hooks)

        # Not filtered by sender: runs for each app, so later apps' permissions get picked up.
        post_migrate.connect(roles.sync_roles, dispatch_uid="core.sync_roles")
