import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.providers.base import BaseProvider
from services.providers.mock_provider import MockProvider
from services.providers.ollama_provider import OllamaProvider
from services.providers.openclaw_provider import OpenClawProvider


class LLMClient:
    """Thin client for switching provider implementations."""

    PROVIDERS: dict[str, type[BaseProvider]] = {
        "mock": MockProvider,
        "openclaw": OpenClawProvider,
        "ollama": OllamaProvider,
    }

    def __init__(self, provider: str = "mock") -> None:
        self.provider = self._create_provider(provider)

    def _create_provider(self, provider: str) -> BaseProvider:
        normalized = str(provider).strip().lower()
        provider_cls = self.PROVIDERS.get(normalized)
        if provider_cls is None:
            raise ValueError(f"Unsupported provider: {provider}")
        return provider_cls()

    def run_task(self, task_name: str, payload: dict) -> dict:
        """Run a task through the selected provider."""
        return self.provider.run_task(task_name, payload)


def _print_result(title: str, result: dict) -> None:
    """Print a compact unified result."""
    print(title)
    print("provider:", result.get("provider"))
    print("model:", result.get("model"))
    print("success:", result.get("success"))
    print("data:", json.dumps(result.get("data"), ensure_ascii=False, indent=2))
    print("error:", result.get("error"))
    print()


def main() -> None:
    """Run a minimal Ollama validation demo."""
    from services.ai_capabilities import normalize_project_case

    samples = [
        "河南南阳",
        "江西赣州",
        "潮州饶平",
        "广东省深圳市宝安区",
        "采力光明",
    ]

    for sample in samples:
        sample_case = {
            "project_name": sample,
            "business_type": "",
            "location_city": "",
            "location_district": "",
            "keywords": [],
            "custom_fields": {"source_construction_location": sample},
        }
        result = normalize_project_case(sample_case, provider="ollama")
        _print_result(f"input: {sample}", result)


if __name__ == "__main__":
    main()
