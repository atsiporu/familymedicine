from django.apps import AppConfig


class LinksConfig(AppConfig):
    name = "apps.links"
    label = "links"
    verbose_name = "Quick links"

    def ready(self) -> None:
        from apps.core.registry import Tool, register

        register(
            Tool(
                slug="links",
                name="Quick Links",
                description="CureMD, payer portals, labs and other sites the practice uses.",
                url_name="links:list",
                icon="🔗",
                permission="links.view_link",
                order=10,
            )
        )
