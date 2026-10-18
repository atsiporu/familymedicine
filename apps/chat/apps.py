from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = "apps.chat"
    label = "chat"
    verbose_name = "AI chat"

    def ready(self) -> None:
        from apps.core.registry import Tool, register

        register(
            Tool(
                slug="chat",
                name="AI Assistant",
                description="Chat with the practice's local AI model. Nothing leaves this server.",
                url_name="chat:page",
                icon="💬",
                permission="ai.use_ai",
                order=20,
            )
        )
