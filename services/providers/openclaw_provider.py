from services.providers.base import BaseProvider


class OpenClawProvider(BaseProvider):
    """Placeholder provider for a future OpenClaw integration."""

    provider_name = "openclaw"
    model_name = "openclaw-placeholder"

    def run_task(self, task_name: str, payload: dict) -> dict:
        return self.build_response(
            task_name,
            False,
            data={"payload_preview": payload},
            error="OpenClaw provider not configured yet",
        )
