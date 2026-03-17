from abc import ABC, abstractmethod
from typing import Any


ProviderResponse = dict[str, Any]


class BaseProvider(ABC):
    """Base interface for all AI providers."""

    provider_name: str = "base"
    model_name: str = ""

    @abstractmethod
    def run_task(self, task_name: str, payload: dict) -> ProviderResponse:
        """Run a named task and return a unified response."""

    def build_response(
        self,
        task_name: str,
        success: bool,
        data: dict | None = None,
        error: str | None = None,
    ) -> ProviderResponse:
        """Build the common response envelope."""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "task": task_name,
            "success": success,
            "data": data or {},
            "error": error,
        }
