import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.llm_client import LLMClient


DEFAULT_PROVIDER = "mock"


class AICapabilities:
    """Capability layer exposed to upper-level modules."""

    def __init__(self, provider: str = DEFAULT_PROVIDER) -> None:
        self.client = LLMClient(provider=provider)

    def normalize_project_case(self, case: dict, provider: str | None = None) -> dict:
        if provider:
            return LLMClient(provider=provider).run_task("normalize_project_case", {"case": case})
        return self.client.run_task("normalize_project_case", {"case": case})

    def generate_followup_tasks(self, context: dict) -> dict:
        return self.client.run_task("generate_followup_tasks", {"context": context})

    def extract_visit_insights(self, raw_text: str) -> dict:
        return self.client.run_task("extract_visit_insights", {"raw_text": raw_text})

    def generate_visit_recommendation(
        self,
        opportunity: dict,
        top_k_cases: list[dict],
        provider: str | None = None,
    ) -> dict:
        payload = {
            "opportunity": opportunity,
            "top_k_cases": top_k_cases,
        }
        if provider:
            return LLMClient(provider=provider).run_task("generate_visit_recommendation", payload)
        return self.client.run_task("generate_visit_recommendation", payload)


_default_capability = AICapabilities()



def normalize_project_case(case: dict, provider: str | None = None) -> dict:
    """Normalize a project case via the configured provider."""
    return _default_capability.normalize_project_case(case, provider=provider)



def generate_followup_tasks(context: dict) -> dict:
    """Generate follow-up tasks via the configured provider."""
    return _default_capability.generate_followup_tasks(context)



def extract_visit_insights(raw_text: str) -> dict:
    """Extract visit insights via the configured provider."""
    return _default_capability.extract_visit_insights(raw_text)



def generate_visit_recommendation(
    opportunity: dict,
    top_k_cases: list[dict],
    provider: str = "ollama",
) -> dict:
    """Generate a structured visit recommendation via the configured provider."""
    return _default_capability.generate_visit_recommendation(
        opportunity,
        top_k_cases,
        provider=provider,
    )
