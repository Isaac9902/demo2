import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.ai_capabilities import generate_visit_recommendation as generate_visit_recommendation_via_ai


RECOMMENDATION_KEYS = (
    "questions_to_ask",
    "suggested_focus_points",
    "next_actions",
    "risk_notes",
)


def build_recommendation_prompt(opportunity: dict, top_k_cases: list[dict]) -> str:
    """Build a readable local preview of the LLM input payload."""
    return json.dumps(
        {
            "opportunity": opportunity,
            "top_k_cases": top_k_cases[:3],
        },
        ensure_ascii=False,
        indent=2,
    )


def empty_recommendation() -> dict:
    """Return the conservative fallback recommendation shape."""
    return {key: [] for key in RECOMMENDATION_KEYS}


def normalize_recommendation_output(data: dict) -> dict:
    """Normalize a recommendation payload into the fixed schema."""
    normalized = empty_recommendation()
    if not isinstance(data, dict):
        return normalized

    for key in RECOMMENDATION_KEYS:
        values = data.get(key, [])
        if not isinstance(values, list):
            continue

        cleaned_values: list[str] = []
        for item in values:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if cleaned:
                cleaned_values.append(cleaned)
        normalized[key] = cleaned_values[:4]

    return normalized


def _append_unique(target: list[str], value: str, limit: int = 4) -> None:
    cleaned = str(value).strip()
    if not cleaned or cleaned in target or len(target) >= limit:
        return
    target.append(cleaned)


def augment_recommendation_with_load(opportunity: dict, recommendation: dict) -> dict:
    power_load_requirement = str(opportunity.get("power_load_requirement", "")).strip()
    estimated_load_kw = opportunity.get("estimated_load_kw")

    if not power_load_requirement and estimated_load_kw is None:
        return recommendation

    load_label = power_load_requirement or f"约{estimated_load_kw}kW"

    questions = recommendation.setdefault("questions_to_ask", [])
    focus_points = recommendation.setdefault("suggested_focus_points", [])
    risk_notes = recommendation.setdefault("risk_notes", [])

    _append_unique(questions, f"当前提到负载需求为{load_label}，需要确认峰值负载、持续负载分别是多少。")
    _append_unique(questions, "需要确认本次是一次性到位，还是分阶段扩容，并明确扩容范围和预留容量。")

    _append_unique(focus_points, f"重点强调团队处理过接近{load_label}规模的配电或扩容项目经验。")
    _append_unique(focus_points, "沟通中优先展示负载测算、配电回路规划和扩容边界的梳理能力。")

    _append_unique(risk_notes, f"负载需求达到{load_label}时，容量校核和配电方案复杂度需要提前评估。")
    _append_unique(risk_notes, "如果客户后续扩容范围继续变化，可能影响变压器容量、柜体配置和实施排期。")
    return recommendation


def generate_visit_recommendation(
    opportunity: dict,
    top_k_cases: list[dict],
    provider: str = "ollama",
) -> dict:
    """Generate a structured visit recommendation with safe fallback."""
    try:
        result = generate_visit_recommendation_via_ai(
            opportunity,
            top_k_cases,
            provider=provider,
        )
    except Exception as exc:
        fallback = empty_recommendation()
        fallback["error"] = f"Failed to generate visit recommendation: {exc}"
        return augment_recommendation_with_load(opportunity, fallback)

    if not isinstance(result, dict):
        fallback = empty_recommendation()
        fallback["error"] = "Invalid AI response envelope"
        return augment_recommendation_with_load(opportunity, fallback)

    if not bool(result.get("success")):
        fallback = empty_recommendation()
        fallback["error"] = str(result.get("error") or "Unknown provider error")
        return augment_recommendation_with_load(opportunity, fallback)

    recommendation = normalize_recommendation_output(result.get("data", {}))
    recommendation["provider"] = str(result.get("provider", "")).strip()
    recommendation["model"] = str(result.get("model", "")).strip()
    return augment_recommendation_with_load(opportunity, recommendation)


def main() -> None:
    """Run a minimal local demo for LLM-generated visit recommendations."""
    opportunity = {
        "company_name": "深圳某自动化设备公司",
        "industry": "自动化设备",
        "business_type_guess": "配电安装工程",
        "power_load_requirement": "预计新增负载约800kW",
        "estimated_load_kw": 800,
        "core_needs": ["低压配电柜", "新增产线"],
        "concerns": ["交付周期", "预算"],
        "current_stage": "new",
        "needs_review": True,
        "review_reasons": ["company_name missing"],
    }
    top_k_cases = [
        {
            "project_name": "华强创意产业园高低压配电柜采购",
            "business_type": "高低压配电工程",
            "matched_reasons": [
                "location_city matched in request text: 深圳 (+2)",
                "keyword matched: 低压配电柜 (+1)",
            ],
            "keywords": ["低压配电柜", "产业园", "配电柜采购"],
            "project_scale": "large",
            "risk_notes": ["项目体量偏大，需避免过度类比。"],
        },
        {
            "project_name": "南山智造基地变配电工程",
            "business_type": "变配电工程",
            "matched_reasons": [
                "location_city matched in request text: 深圳 (+2)",
                "project_name core term matched 1 item(s) (+1)",
            ],
            "keywords": ["变配电", "产线配套"],
            "project_scale": "medium",
        },
    ]

    print("Prompt preview:")
    print(build_recommendation_prompt(opportunity, top_k_cases))
    print()

    recommendation = generate_visit_recommendation(
        opportunity,
        top_k_cases,
        provider="ollama",
    )
    print(json.dumps(recommendation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
