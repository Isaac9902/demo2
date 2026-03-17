import json
from pathlib import Path

from pipeline.init_app_db import DB_FILE, get_connection, init_app_db
from pipeline.manage_opportunity_records import create_opportunity

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT_DIR))

from pipeline.generate_visit_recommendation import generate_visit_recommendation
from services.ai_capabilities import normalize_project_case as normalize_project_case_via_ai
from pipeline.parse_opportunity_note import parse_opportunity_note
from pipeline.retrieve_similar_projects import retrieve_similar_projects



def _t(value: str) -> str:
    if "\\u" in value:
        return value.encode("ascii").decode("unicode_escape")
    return value



def generate_talking_points(opportunity: dict, retrieved_cases: list[dict]) -> list[str]:
    """Generate 2-4 minimal rule-based talking points."""
    talking_points: list[str] = []
    core_needs = opportunity.get("core_needs", [])
    if not isinstance(core_needs, list):
        core_needs = []

    if core_needs:
        talking_points.append(
            _t("\u4f18\u5148\u56f4\u7ed5\u5ba2\u6237\u5f53\u524d\u6838\u5fc3\u9700\u6c42\u5c55\u5f00\uff1a") + _t("\u3001").join(core_needs[:3])
        )

    if retrieved_cases:
        top_case = retrieved_cases[0]
        talking_points.append(
            _t("\u5efa\u8bae\u5148\u8bb2\u6848\u4f8b\u300a") + f"{top_case.get('project_name', '')}" + _t("\u300b\uff0c\u56e0\u4e3a\u5b83\u5f53\u524d\u5339\u914d\u5ea6\u6700\u9ad8\u3002")
        )

        top_reasons = top_case.get("matched_reasons", [])
        if isinstance(top_reasons, list) and top_reasons:
            talking_points.append(
                _t("\u5efa\u8bae\u5f3a\u8c03\u5339\u914d\u70b9\uff1a") + _t("\uff1b").join(str(reason) for reason in top_reasons[:2])
            )

        if len(retrieved_cases) > 1:
            second_case = retrieved_cases[1]
            talking_points.append(
                _t("\u53ef\u8865\u5145\u5bf9\u6bd4\u6848\u4f8b\u300a") + f"{second_case.get('project_name', '')}" + _t("\u300b\uff0c\u589e\u5f3a\u5ba2\u6237\u5bf9\u4ea4\u4ed8\u573a\u666f\u7684\u4fe1\u5fc3\u3002")
            )
    else:
        if core_needs:
            talking_points.append(_t("\u5f53\u524d\u672a\u68c0\u7d22\u5230\u9ad8\u5339\u914d\u6848\u4f8b\uff0c\u5efa\u8bae\u5148\u56f4\u7ed5\u9700\u6c42\u6f84\u6e05\u548c\u5b9e\u65bd\u8fb9\u754c\u5c55\u5f00\u6c9f\u901a\u3002"))
        else:
            talking_points.append(_t("\u5f53\u524d\u9879\u76ee\u4fe1\u606f\u8f83\u5f31\uff0c\u5efa\u8bae\u5148\u8865\u5145\u9700\u6c42\u7ec6\u8282\uff0c\u518d\u8fdb\u5165\u6848\u4f8b\u8bb2\u89e3\u3002"))

    deduped: list[str] = []
    for point in talking_points:
        cleaned = str(point).strip()
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
    return deduped[:4]



def suggest_followup_timing(opportunity: dict) -> tuple[str, str]:
    """Generate a minimal follow-up timing suggestion from opportunity fields."""
    concerns = opportunity.get("concerns", [])
    if not isinstance(concerns, list):
        concerns = []
    core_needs = opportunity.get("core_needs", [])
    if not isinstance(core_needs, list):
        core_needs = []

    current_stage = str(opportunity.get("current_stage", "new")).strip() or "new"
    budget_hint = str(opportunity.get("budget_hint", "")).strip()
    needs_review = bool(opportunity.get("needs_review"))

    if needs_review:
        return _t("\u8865\u5168\u4fe1\u606f\u540e\u518d\u8ddf\u8fdb"), _t("\u5f53\u524d\u673a\u4f1a\u8bb0\u5f55\u4ecd\u9700\u8865\u5145\u5173\u952e\u5b57\u6bb5\uff0c\u5efa\u8bae\u5148\u8865\u5168\u518d\u8fdb\u5165\u6b63\u5f0f\u63a8\u8fdb\u3002")

    if any(item in concerns for item in [_t("\u4ea4\u4ed8\u5468\u671f"), _t("\u5de5\u671f"), _t("\u5b89\u88c5\u914d\u5408")]):
        return _t("3\u5929\u5185"), _t("\u5ba2\u6237\u5bf9\u65f6\u95f4\u548c\u4ea4\u4ed8\u8282\u594f\u654f\u611f\uff0c\u9002\u5408\u5c3d\u5feb\u8ddf\u8fdb\u3002")

    if current_stage == "new" and (core_needs or budget_hint):
        return _t("1\u5468\u5185"), _t("\u5f53\u524d\u5df2\u5177\u5907\u521d\u6b65\u9879\u76ee\u9700\u6c42\u548c\u9884\u7b97\u7ebf\u7d22\uff0c\u9002\u5408\u4e00\u5468\u5185\u63a8\u8fdb\u4e0b\u4e00\u8f6e\u6c9f\u901a\u3002")

    return _t("1\u5468\u5185"), _t("\u5f53\u524d\u5904\u4e8e\u65e9\u671f\u7ebf\u7d22\u9636\u6bb5\uff0c\u5efa\u8bae\u4fdd\u6301\u8f7b\u91cf\u8282\u594f\u8ddf\u8fdb\u3002")



def generate_llm_assisted_insights(raw_input: str, opportunity: dict, provider: str = "ollama") -> dict:
    """Generate lightweight LLM-assisted recognition hints for the result view."""
    payload = {
        "project_name": str(raw_input).strip(),
        "business_type": str(opportunity.get("business_type_guess", "")).strip(),
        "location_province": str(opportunity.get("location_province", "")).strip(),
        "location_city": str(opportunity.get("location_city", "")).strip(),
        "location_district": str(opportunity.get("location_district", "")).strip(),
        "keywords": [str(item).strip() for item in opportunity.get("core_needs", []) if str(item).strip()],
        "custom_fields": {"source_construction_location": str(raw_input).strip()},
    }

    try:
        result = normalize_project_case_via_ai(payload, provider=provider)
    except Exception as exc:
        return {
            "success": False,
            "provider": provider,
            "model": "",
            "business_type": "",
            "keywords": [],
            "location_city": "",
            "location_district": "",
            "notes": [],
            "error": str(exc),
        }

    data = result.get("data", {})
    if not isinstance(data, dict):
        data = {}

    notes = data.get("notes", [])
    if not isinstance(notes, list):
        notes = []
    notes = [str(item).strip() for item in notes if str(item).strip()]

    normalized_case = data.get("normalized_case")
    if not isinstance(normalized_case, dict):
        normalized_case = data

    return {
        "success": bool(result.get("success")),
        "provider": str(result.get("provider", "")).strip(),
        "model": str(result.get("model", "")).strip(),
        "business_type": str(normalized_case.get("business_type", "")).strip(),
        "keywords": [str(item).strip() for item in normalized_case.get("keywords", []) if str(item).strip()] if isinstance(normalized_case.get("keywords", []), list) else [],
        "location_city": str(normalized_case.get("location_city", "")).strip(),
        "location_district": str(normalized_case.get("location_district", "")).strip(),
        "notes": notes[:3],
        "error": "" if result.get("error") in (None, "None") else str(result.get("error", "")).strip(),
    }



def run_opportunity_flow(raw_input: str, top_k: int = 3, source_mode: str = "manual", user_id: str = "") -> dict:
    """Run the minimal end-to-end opportunity orchestration flow."""
    opportunity = parse_opportunity_note(raw_input)
    opportunity["source_mode"] = str(source_mode).strip() or "manual"
    opportunity["user_id"] = str(user_id).strip()
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        opportunity["id"] = create_opportunity(conn, opportunity)

    try:
        top_k_cases = retrieve_similar_projects(raw_input, top_k=top_k)
    except (FileNotFoundError, ValueError, OSError):
        top_k_cases = []

    talking_points = generate_talking_points(opportunity, top_k_cases)
    followup_time_suggestion, followup_time_reason = suggest_followup_timing(opportunity)
    llm_assisted_insights = generate_llm_assisted_insights(raw_input, opportunity)

    try:
        visit_recommendation = generate_visit_recommendation(opportunity, top_k_cases)
    except Exception as exc:
        visit_recommendation = {
            "questions_to_ask": [],
            "suggested_focus_points": [],
            "next_actions": [],
            "risk_notes": [],
            "error": f"Failed to generate visit recommendation: {exc}",
        }

    return {
        "opportunity": opportunity,
        "top_k_cases": top_k_cases,
        "visit_recommendation": visit_recommendation,
        "recommended_talking_points": talking_points,
        "followup_time_suggestion": followup_time_suggestion,
        "followup_time_reason": followup_time_reason,
        "llm_assisted_insights": llm_assisted_insights,
    }



def main() -> None:
    """Run a built-in sample through the minimal opportunity flow."""
    sample_input = (
        _t("\u6df1\u5733\u5b9d\u5b89\u4e00\u4e2a\u81ea\u52a8\u5316\u8bbe\u5907\u5ba2\u6237\uff0c\u8054\u7cfb\u4eba\u738b\u5de5\uff0c\u7535\u8bdd13800138000\uff0c\u6700\u8fd1\u65b0\u589e\u4ea7\u7ebf\uff0c")
        + _t("\u9700\u8981\u4f4e\u538b\u914d\u7535\u67dc\uff0c\u62c5\u5fc3\u4ea4\u4ed8\u5468\u671f\u3002")
    )
    result = run_opportunity_flow(sample_input, top_k=3)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"{_t('\\u673a\\u4f1a\\u8bb0\\u5f55\\u5df2\\u5199\\u5165')} : {OPPORTUNITY_FILE}")


if __name__ == "__main__":
    main()
