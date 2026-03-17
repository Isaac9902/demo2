import json
from collections import Counter
from pathlib import Path

import os
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.ai_capabilities import normalize_project_case


INPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "project_cases.jsonl"
OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "project_cases_cleaned.jsonl"
)

DISTRICT_HINTS = [
    "宝安区",
    "南山区",
    "龙岗区",
    "福田区",
    "罗湖区",
    "盐田区",
    "光明区",
    "坪山区",
    "龙华区",
    "黄埔区",
    "天河区",
    "南海区",
    "三水区",
    "双流区",
    "浦东新区",
    "东西湖区",
    "渝北区",
    "吴中区",
    "北仑区",
    "滨海新区",
    "惠阳区",
    "长安镇",
    "虎门镇",
    "饶平县",
    "饶平",
]

NON_ADMIN_LOCATION_LABELS = {
    "工业园区": "工业园区",
    "产业园区": "产业园区",
    "科技园区": "科技园区",
    "高新区": "高新区",
    "经开区": "经开区",
    "经济开发区": "经济开发区",
    "开发区": "开发区",
    "保税区": "保税区",
    "产业基地": "产业基地",
    "工业基地": "工业基地",
    "物流园区": "物流园区",
    "工业园": "工业园",
    "产业园": "产业园",
    "科技园": "科技园",
    "物流园": "物流园",
}

BUSINESS_RULES = [
    ("高低压配电工程", ["高低压", "高低压配电"]),
    ("变配电工程", ["变配电", "配电房", "专变"]),
    ("配电安装工程", ["配电安装", "安装工程"]),
    ("配电改造工程", ["改造", "升级", "扩容", "增容", "更新"]),
    ("供配电建设工程", ["供配电", "配电建设", "建设工程", "新建"]),
]

KEYWORD_TERMS = [
    "高低压配电",
    "变配电",
    "配电安装",
    "配电改造",
    "供配电",
    "低压配电柜",
    "控制柜",
    "自动化设备",
    "新产线",
    "扩产",
    "增容",
    "电力",
    "工业园",
    "工业园区",
    "产业园",
    "产业园区",
    "科技园",
    "科技园区",
    "高新区",
    "经开区",
    "开发区",
    "保税区",
    "产业基地",
    "物流园",
    "物流园区",
    "厂房",
    "车间",
    "医院",
    "学校",
    "办公楼",
    "数据中心",
]

CITY_NORMALIZATION_MAP = {
    "深圳市": "深圳",
    "广东省深圳市": "深圳",
    "广东深圳": "深圳",
    "广州市": "广州",
    "广东省广州市": "广州",
    "广东广州": "广州",
    "东莞市": "东莞",
    "广东省东莞市": "东莞",
    "广东东莞": "东莞",
    "河南南阳": "南阳",
    "南阳市": "南阳",
    "江西赣州": "赣州",
    "赣州市": "赣州",
    "广西柳州": "柳州",
    "柳州市": "柳州",
    "河南平顶山": "平顶山",
    "平顶山市": "平顶山",
    "江西吉安": "吉安",
    "吉安市": "吉安",
    "潮州饶平": "潮州",
    "潮州市": "潮州",
    "汕头市": "汕头",
    "佛山市": "佛山",
    "苏州市": "苏州",
    "成都市": "成都",
    "长沙市": "长沙",
    "武汉市": "武汉",
    "宁波市": "宁波",
    "天津市": "天津",
    "重庆市": "重庆",
    "上海市": "上海",
    "惠州市": "惠州",
}

KNOWN_CITIES = [
    "深圳", "广州", "东莞", "惠州", "佛山", "汕头", "揭阳", "肇庆", "河源",
    "南阳", "平顶山", "赣州", "吉安", "柳州", "潮州", "苏州", "上海", "武汉",
    "重庆", "宁波", "天津", "成都", "长沙", "南昌", "厦门", "珠海", "佛山"
]

PROVINCE_PREFIXES = [
    "广东省", "河南省", "江西省", "广西壮族自治区", "广西", "湖南省", "湖北省"
]

CITY_TO_PROVINCE = {
    "深圳": "广东",
    "广州": "广东",
    "东莞": "广东",
    "惠州": "广东",
    "佛山": "广东",
    "汕头": "广东",
    "揭阳": "广东",
    "肇庆": "广东",
    "河源": "广东",
    "珠海": "广东",
    "潮州": "广东",
    "南阳": "河南",
    "平顶山": "河南",
    "赣州": "江西",
    "吉安": "江西",
    "南昌": "江西",
    "柳州": "广西",
    "苏州": "江苏",
    "上海": "上海",
    "武汉": "湖北",
    "重庆": "重庆",
    "宁波": "浙江",
    "天津": "天津",
    "成都": "四川",
    "长沙": "湖南",
    "厦门": "福建",
}

DISTRICT_TO_CITY = {
    "宝安区": "深圳",
    "南山区": "深圳",
    "龙岗区": "深圳",
    "福田区": "深圳",
    "罗湖区": "深圳",
    "盐田区": "深圳",
    "光明区": "深圳",
    "坪山区": "深圳",
    "龙华区": "深圳",
    "黄埔区": "广州",
    "天河区": "广州",
    "南海区": "佛山",
    "三水区": "佛山",
    "双流区": "成都",
    "浦东新区": "上海",
    "东西湖区": "武汉",
    "渝北区": "重庆",
    "吴中区": "苏州",
    "北仑区": "宁波",
    "滨海新区": "天津",
    "惠阳区": "惠州",
    "长安镇": "东莞",
    "虎门镇": "东莞",
    "饶平县": "潮州",
    "饶平": "潮州",
}

PROVINCE_NORMALIZATION_MAP = {
    "广东省": "广东",
    "河南省": "河南",
    "江西省": "江西",
    "湖北省": "湖北",
    "湖南省": "湖南",
    "江苏省": "江苏",
    "浙江省": "浙江",
    "福建省": "福建",
    "四川省": "四川",
    "广西壮族自治区": "广西",
    "广西自治区": "广西",
    "上海市": "上海",
    "天津市": "天津",
    "重庆市": "重庆",
}

KNOWN_PROVINCES = set(PROVINCE_NORMALIZATION_MAP.values()) | {
    "广东", "河南", "江西", "湖北", "湖南", "江苏", "浙江", "福建", "四川", "广西",
    "上海", "天津", "重庆",
}


def _parse_json_objects(text: str, file_path: str, line_number: int) -> list[dict]:
    """Parse one or more JSON objects from a line."""
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



def load_cases(file_path: str) -> list[dict]:
    """Load project cases from a JSONL file."""
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



def _extract_source_location(case: dict) -> str:
    custom_fields = case.get("custom_fields", {})
    if isinstance(custom_fields, dict):
        return str(custom_fields.get("source_construction_location", "")).strip()
    return ""



def _extract_location_scene_label(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""

    for label in NON_ADMIN_LOCATION_LABELS:
        if label in value:
            return NON_ADMIN_LOCATION_LABELS[label]
    return ""



def _normalize_city_text(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""

    if value in CITY_NORMALIZATION_MAP:
        return CITY_NORMALIZATION_MAP[value]

    for city in KNOWN_CITIES:
        if city in value:
            return city

    city_marker = "市"
    province_marker = "省"

    if city_marker in value:
        city_text = value.split(city_marker, 1)[0]
        for prefix in PROVINCE_PREFIXES:
            if city_text.startswith(prefix):
                city_text = city_text[len(prefix):]
                break
        if city_text:
            return city_text

    if province_marker in value:
        after_province = value.split(province_marker, 1)[1]
        if city_marker in after_province:
            return after_province.split(city_marker, 1)[0]
        for city in KNOWN_CITIES:
            if city in after_province:
                return city
        if len(after_province) >= 2:
            return after_province[:3].rstrip("区县镇")

    for prefix in PROVINCE_PREFIXES:
        if value.startswith(prefix):
            tail = value[len(prefix):]
            for city in KNOWN_CITIES:
                if city in tail:
                    return city
            if len(tail) >= 2:
                return tail[:3].rstrip("区县镇")

    if len(value) >= 4 and value[:2] in ["河南", "江西", "广西", "广东"]:
        tail = value[2:]
        for city in KNOWN_CITIES:
            if city in tail:
                return city
        if len(tail) >= 2:
            return tail[:3].rstrip("区县镇")

    for suffix in [city_marker, "区", "县", "镇"]:
        if suffix in value:
            return value.split(suffix, 1)[0]
    return value



def _normalize_province_text(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""

    if value in PROVINCE_NORMALIZATION_MAP:
        return PROVINCE_NORMALIZATION_MAP[value]

    for raw_prefix, normalized in PROVINCE_NORMALIZATION_MAP.items():
        if value.startswith(raw_prefix):
            return normalized

    for province in KNOWN_PROVINCES:
        if province and province in value:
            return province

    return ""



def normalize_city_and_district(case: dict) -> dict:
    """Normalize location_province, location_city and location_district."""
    new_case = dict(case)
    raw_province = str(case.get("location_province", "")).strip()
    raw_city = str(case.get("location_city", "")).strip()
    raw_district = str(case.get("location_district", "")).strip()
    source_location = _extract_source_location(case)
    combined_text = " ".join(
        part for part in [raw_province, raw_city, raw_district, source_location] if part
    )

    normalized_city = _normalize_city_text(raw_city or source_location)
    normalized_district = raw_district
    location_scene_label = ""
    if not normalized_district:
        for district in DISTRICT_HINTS:
            if district in combined_text:
                normalized_district = district
                break

    if normalized_district == "饶平":
        normalized_district = "饶平县"

    if normalized_district:
        location_scene_label = _extract_location_scene_label(normalized_district)
        if location_scene_label:
            normalized_district = ""

    if not normalized_city and normalized_district:
        normalized_city = DISTRICT_TO_CITY.get(normalized_district, "")

    normalized_province = _normalize_province_text(raw_province or source_location)
    if not normalized_province and normalized_city:
        normalized_province = CITY_TO_PROVINCE.get(normalized_city, "")

    new_case["location_province"] = normalized_province
    new_case["location_city"] = normalized_city
    new_case["location_district"] = normalized_district
    custom_fields = new_case.get("custom_fields", {})
    if not isinstance(custom_fields, dict):
        custom_fields = {}
    if location_scene_label:
        custom_fields["location_scene_label"] = location_scene_label
    elif "location_scene_label" in custom_fields:
        custom_fields.pop("location_scene_label", None)
    new_case["custom_fields"] = custom_fields
    return new_case



def normalize_business_type(case: dict) -> str:
    """Normalize business type to a small set of standard labels."""
    text = " ".join(
        [
            str(case.get("business_type", "")).strip(),
            str(case.get("project_name", "")).strip(),
        ]
    )
    for target, keywords in BUSINESS_RULES:
        if any(keyword in text for keyword in keywords):
            return target
    return "其他"



def rebuild_keywords(case: dict) -> list[str]:
    """Rebuild keyword list from project name, normalized business type and scene labels."""
    custom_fields = case.get("custom_fields", {})
    scene_label = ""
    if isinstance(custom_fields, dict):
        scene_label = str(custom_fields.get("location_scene_label", "")).strip()

    text = " ".join(
        [
            str(case.get("project_name", "")).strip(),
            str(case.get("business_type", "")).strip(),
            scene_label,
        ]
    )
    keywords: list[str] = []
    for term in KEYWORD_TERMS:
        if term in text and term not in keywords:
            keywords.append(term)
    business_type = str(case.get("business_type", "")).strip()
    if business_type and business_type != "其他" and business_type not in keywords:
        keywords.append(business_type)
    return keywords



def infer_project_scale(case: dict) -> str:
    """Infer project scale from project amount."""
    amount = case.get("project_amount", 0)
    try:
        numeric_amount = float(amount)
    except (TypeError, ValueError):
        numeric_amount = 0.0

    if numeric_amount <= 300000:
        return "small"
    if numeric_amount <= 1000000:
        return "medium"
    return "large"



def _keywords_too_weak(keywords: list[str], business_type: str) -> bool:
    if not keywords:
        return True
    if len(keywords) == 1:
        only_keyword = keywords[0]
        if only_keyword == business_type or len(only_keyword) <= 2:
            return True
    meaningful_keywords = [keyword for keyword in keywords if len(keyword.strip()) >= 3]
    return not meaningful_keywords



def build_review_flags(case: dict) -> tuple[bool, list[str]]:
    """Build review flags for records that still look weak or ambiguous."""
    review_reasons: list[str] = []

    province = str(case.get("location_province", "")).strip()
    city = str(case.get("location_city", "")).strip()
    district = str(case.get("location_district", "")).strip()
    business_type = str(case.get("business_type", "")).strip()
    keywords = case.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []

    source_location = _extract_source_location(case)

    location_ambiguous = False
    if not city:
        location_ambiguous = True
    elif city not in KNOWN_CITIES:
        location_ambiguous = True
    elif not province:
        location_ambiguous = True
    elif district and district not in DISTRICT_TO_CITY:
        location_ambiguous = True
    elif source_location and city not in source_location and district and district not in source_location:
        location_ambiguous = True

    if location_ambiguous:
        review_reasons.append("location ambiguous")

    if business_type == "其他":
        review_reasons.append("business_type weak")

    if _keywords_too_weak(keywords, business_type):
        if keywords:
            review_reasons.append("keywords weak")
        else:
            review_reasons.append("keywords empty")

    return bool(review_reasons), review_reasons



def should_use_llm_enrichment(case: dict) -> bool:
    """Placeholder for future LLM enrichment routing."""
    needs_review, reasons = build_review_flags(case)
    return needs_review and any(
        reason in {"location ambiguous", "business_type weak", "keywords weak", "keywords empty"}
        for reason in reasons
    )



def _env_flag(name: str, default: bool = False) -> bool:
    value = str(os.getenv(name, "")).strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}



def _extract_enrichment_payload(result: dict) -> tuple[dict, list[str]]:
    data = result.get("data", {})
    if not isinstance(data, dict):
        return {}, []

    notes = data.get("notes", [])
    if not isinstance(notes, list):
        notes = []
    normalized_notes = [str(note).strip() for note in notes if str(note).strip()]

    normalized_case = data.get("normalized_case")
    if isinstance(normalized_case, dict):
        return normalized_case, normalized_notes

    return data, normalized_notes



def _dedupe_keywords(keywords: list[str]) -> list[str]:
    deduped: list[str] = []
    for keyword in keywords:
        cleaned = str(keyword).strip()
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
    return deduped



def apply_llm_enrichment(case: dict, review_reasons: list[str], provider: str) -> tuple[dict, bool, bool]:
    """Optionally fill weak fields via the existing AI normalization capability."""
    if not should_use_llm_enrichment(case):
        return dict(case), False, False

    result = normalize_project_case(case, provider=provider)
    success = bool(result.get("success"))
    if not success:
        return dict(case), True, False

    suggestion, notes = _extract_enrichment_payload(result)
    if not suggestion:
        return dict(case), True, False

    new_case = dict(case)
    location_is_weak = "location ambiguous" in review_reasons
    business_is_weak = "business_type weak" in review_reasons
    keywords_are_weak = (
        "keywords weak" in review_reasons or "keywords empty" in review_reasons
    )

    if location_is_weak:
        for field in ("location_province", "location_city", "location_district"):
            candidate = str(suggestion.get(field, "")).strip()
            if candidate:
                new_case[field] = candidate
        new_case = normalize_city_and_district(new_case)

    if business_is_weak:
        candidate_business = str(suggestion.get("business_type", "")).strip()
        if candidate_business and candidate_business != "其他":
            new_case["business_type"] = candidate_business

    if keywords_are_weak:
        candidate_keywords = suggestion.get("keywords", [])
        if isinstance(candidate_keywords, list):
            merged_keywords = _dedupe_keywords(
                list(new_case.get("keywords", [])) + candidate_keywords
            )
            if merged_keywords:
                new_case["keywords"] = merged_keywords

    if notes:
        custom_fields = new_case.get("custom_fields", {})
        if not isinstance(custom_fields, dict):
            custom_fields = {}
        custom_fields["llm_enrichment_notes"] = notes
        new_case["custom_fields"] = custom_fields

    return new_case, True, True



def write_cases(file_path: str, cases: list[dict]) -> None:
    """Write normalized cases to a JSONL file."""
    path = Path(file_path)
    with path.open("w", encoding="utf-8") as file:
        for case in cases:
            file.write(json.dumps(case, ensure_ascii=False) + "\n")



def main() -> None:
    """Run one pass of case normalization and review flagging."""
    try:
        llm_enrichment_enabled = _env_flag("NORMALIZE_ENABLE_LLM_ENRICHMENT")
        llm_provider = str(os.getenv("NORMALIZE_LLM_PROVIDER", "mock")).strip() or "mock"
        cases = load_cases(str(INPUT_FILE))
        cleaned_cases: list[dict] = []
        city_changed = 0
        district_filled = 0
        business_changed = 0
        keywords_changed = 0
        needs_review_count = 0
        llm_attempted_count = 0
        llm_success_count = 0
        review_reason_counter: Counter[str] = Counter()

        for case in cases:
            original_city = str(case.get("location_city", "")).strip()
            original_district = str(case.get("location_district", "")).strip()
            original_business = str(case.get("business_type", "")).strip()
            original_keywords = case.get("keywords", [])
            if not isinstance(original_keywords, list):
                original_keywords = []

            new_case = normalize_city_and_district(case)
            if str(new_case.get("location_city", "")).strip() != original_city:
                city_changed += 1
            if not original_district and str(new_case.get("location_district", "")).strip():
                district_filled += 1

            new_business_type = normalize_business_type(new_case)
            if new_business_type != original_business:
                business_changed += 1
            new_case["business_type"] = new_business_type

            new_keywords = rebuild_keywords(new_case)
            if new_keywords != original_keywords:
                keywords_changed += 1
            new_case["keywords"] = new_keywords

            new_case["project_scale"] = infer_project_scale(new_case)
            needs_review, review_reasons = build_review_flags(new_case)

            llm_attempted = False
            llm_success = False
            if llm_enrichment_enabled and should_use_llm_enrichment(new_case):
                new_case, llm_attempted, llm_success = apply_llm_enrichment(
                    new_case,
                    review_reasons,
                    provider=llm_provider,
                )
                if llm_attempted:
                    llm_attempted_count += 1
                if llm_success:
                    llm_success_count += 1
                needs_review, review_reasons = build_review_flags(new_case)

            new_case["needs_review"] = needs_review
            new_case["review_reasons"] = review_reasons
            new_case["should_use_llm_enrichment"] = should_use_llm_enrichment(new_case)
            new_case["llm_enrichment_attempted"] = llm_attempted
            new_case["llm_enrichment_succeeded"] = llm_success

            if needs_review:
                needs_review_count += 1
                review_reason_counter.update(review_reasons)

            cleaned_cases.append(new_case)

        write_cases(str(OUTPUT_FILE), cleaned_cases)

        print(f"总记录数: {len(cleaned_cases)}")
        print(f"城市被规范化条数: {city_changed}")
        print(f"区县成功拆出条数: {district_filled}")
        print(f"业务类型被归一化条数: {business_changed}")
        print(f"关键词更新条数: {keywords_changed}")
        print(f"needs_review=true 的记录数: {needs_review_count}")
        print(f"LLM 补全尝试条数: {llm_attempted_count}")
        print(f"LLM 补全成功条数: {llm_success_count}")
        print(
            "前 10 条 review reason 统计: "
            + json.dumps(review_reason_counter.most_common(10), ensure_ascii=False)
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"执行失败: {exc}")


if __name__ == "__main__":
    main()
