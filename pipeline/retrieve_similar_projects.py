import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CLEANED_DATA_FILE = BASE_DIR / "data" / "project_cases_cleaned.jsonl"
RAW_DATA_FILE = BASE_DIR / "data" / "project_cases.jsonl"


def get_data_file() -> Path:
    """Prefer cleaned data for retrieval while keeping raw data untouched."""
    if CLEANED_DATA_FILE.exists():
        return CLEANED_DATA_FILE
    return RAW_DATA_FILE


SMALL_HINTS = ("\u5c0f\u9879\u76ee", "\u9884\u7b97\u4e0d\u5927", "\u51e0\u5341\u4e07")
MEDIUM_HINTS = ("\u4e2d\u7b49\u4f53\u91cf", "\u51e0\u767e\u4e07\u4ee5\u5185")
LARGE_HINTS = ("\u5927\u9879\u76ee", "\u4e0a\u767e\u4e07", "\u767e\u4e07\u7ea7")


def normalize_text(text: str) -> str:
    """Normalize text for simple rule matching."""
    if text is None:
        return ""
    return str(text).strip().lower()



def _parse_json_objects(text: str, file_path: str, line_number: int) -> list[dict]:
    """Parse one or more JSON objects from a JSONL line."""
    decoder = json.JSONDecoder()
    index = 0
    items: list[dict] = []

    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            break
        try:
            item, next_index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON on line {line_number} in {file_path}: {exc}"
            ) from exc
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid record on line {line_number} in {file_path}: expected object"
            )
        items.append(item)
        index = next_index

    return items



def load_project_cases(file_path: str) -> list[dict]:
    """Load project cases from the JSONL file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Project cases file not found: {file_path}")

    cases: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            content = line.strip()
            if not content:
                continue
            cases.extend(_parse_json_objects(content, file_path, line_number))
    return cases



def infer_project_scale(project_amount: int) -> str:
    """Infer a simple scale label from project amount."""
    if project_amount <= 300000:
        return "small"
    if project_amount <= 1000000:
        return "medium"
    return "large"



def infer_requested_scale(raw_customer_text: str) -> str | None:
    """Infer requested scale from customer wording."""
    text = normalize_text(raw_customer_text)
    if any(normalize_text(item) in text for item in LARGE_HINTS):
        return "large"
    if any(normalize_text(item) in text for item in MEDIUM_HINTS):
        return "medium"
    if any(normalize_text(item) in text for item in SMALL_HINTS):
        return "medium"
    return None



def extract_fragments(raw_customer_text: str) -> list[str]:
    """Extract simple fragments from customer text."""
    separators = "，。；：、,.!?！？;:\n\r\t()（）/ "
    text = raw_customer_text
    for separator in separators:
        text = text.replace(separator, "|")

    fragments: list[str] = []
    seen: set[str] = set()
    for part in text.split("|"):
        fragment = normalize_text(part)
        if len(fragment) < 2 or fragment in seen:
            continue
        seen.add(fragment)
        fragments.append(fragment)
    return fragments



def _extract_core_terms(text: str) -> list[str]:
    """Extract short core terms for weak matching."""
    terms = extract_fragments(text)
    return [term for term in terms if 2 <= len(term) <= 6]



def _parse_project_amount(value: object) -> int:
    """Parse project amount into int for sorting and scale inference."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0



def score_project(case: dict, raw_customer_text: str) -> dict:
    """Score one project case using simple, explainable rules."""
    text = normalize_text(raw_customer_text)
    fragments = extract_fragments(raw_customer_text)
    requested_scale = infer_requested_scale(raw_customer_text)

    score = 0
    matched_reasons: list[str] = []

    location_city = normalize_text(case.get("location_city", ""))
    if location_city and location_city in text:
        score += 2
        matched_reasons.append(
            f"location_city matched in request text: {case.get('location_city', '')} (+2)"
        )

    location_district = normalize_text(case.get("location_district", ""))
    if location_district and location_district in text:
        score += 2
        matched_reasons.append(
            f"location_district matched in request text: {case.get('location_district', '')} (+2)"
        )

    business_type = str(case.get("business_type", "") or "")
    business_parts = [part.strip() for part in business_type.split("/")]
    for part in business_parts:
        normalized_part = normalize_text(part)
        if normalized_part and normalized_part in text:
            score += 2
            matched_reasons.append(f"business_type sub-phrase matched: {part} (+2)")

    keywords = case.get("keywords", [])
    keyword_matched = False
    if isinstance(keywords, list):
        for keyword in keywords:
            normalized_keyword = normalize_text(keyword)
            if normalized_keyword and normalized_keyword in text:
                score += 1
                keyword_matched = True
                matched_reasons.append(f"keyword matched: {keyword} (+1)")

    project_name = normalize_text(case.get("project_name", ""))
    project_name_matches = 0
    for fragment in fragments:
        if len(fragment) < 2:
            continue
        if fragment in project_name:
            project_name_matches += 1
    if project_name_matches > 0:
        bonus = 2 if project_name_matches >= 2 else 1
        score += bonus
        matched_reasons.append(
            f"project_name matched {project_name_matches} fragment(s) (+{bonus})"
        )
    else:
        core_term_matches = 0
        for term in _extract_core_terms(case.get("project_name", "")):
            normalized_term = normalize_text(term)
            if normalized_term and normalized_term in text:
                core_term_matches += 1
        if core_term_matches > 0:
            bonus = 2 if core_term_matches >= 2 else 1
            score += bonus
            matched_reasons.append(
                f"project_name core term matched {core_term_matches} item(s) (+{bonus})"
            )

    if not keyword_matched:
        weak_name_matches = 0
        for term in _extract_core_terms(case.get("project_name", "")):
            normalized_term = normalize_text(term)
            if normalized_term and normalized_term in text:
                weak_name_matches += 1
        if weak_name_matches > 0:
            score += 1
            matched_reasons.append(
                f"keyword fallback to project_name weak match: {weak_name_matches} term(s) (+1)"
            )

    project_amount = _parse_project_amount(case.get("project_amount", 0))
    project_scale = infer_project_scale(project_amount)
    if requested_scale and project_scale == requested_scale:
        score += 1
        matched_reasons.append(f"project_scale matched: {project_scale} (+1)")
    elif requested_scale == "medium" and project_scale == "small":
        score += 1
        matched_reasons.append(
            "project_scale approximately matched: small for medium-like request (+1)"
        )

    return {
        "project_id": case.get("project_id", ""),
        "project_name": case.get("project_name", ""),
        "company_name": case.get("company_name", ""),
        "business_type": case.get("business_type", ""),
        "location_city": case.get("location_city", ""),
        "location_district": case.get("location_district", ""),
        "project_amount": project_amount,
        "score": score,
        "matched_reasons": matched_reasons,
    }



def retrieve_similar_projects(raw_customer_text: str, top_k: int = 3) -> list[dict]:
    """Retrieve top-k similar cases sorted by score then amount."""
    cases = load_project_cases(str(get_data_file()))
    scored_cases = [score_project(case, raw_customer_text) for case in cases]
    ranked_cases = sorted(
        scored_cases,
        key=lambda item: (item["score"], item["project_amount"]),
        reverse=True,
    )
    return ranked_cases[:top_k]



def main() -> None:
    """Run a built-in example and print Top-3 results."""
    raw_customer_text = (
        "\u6df1\u5733\u5b9d\u5b89\u533a\u4e00\u4e2a\u81ea\u52a8\u5316\u8bbe\u5907\u5ba2\u6237\uff0c\u6700\u8fd1\u65b0\u589e\u4ea7\u7ebf\uff0c"
        "\u9700\u8981\u4f4e\u538b\u914d\u7535\u67dc\u914d\u5957\uff0c\u6bd4\u8f83\u62c5\u5fc3\u4ea4\u4ed8\u5468\u671f\uff0c"
        "\u5e0c\u671b\u5148\u770b\u770b\u7c7b\u4f3c\u6848\u4f8b\uff0c\u9879\u76ee\u9884\u7b97\u5927\u6982\u51e0\u5341\u4e07\u3002"
    )
    try:
        results = retrieve_similar_projects(raw_customer_text, top_k=3)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
