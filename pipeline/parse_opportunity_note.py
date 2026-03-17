import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "data" / "opportunity_records.jsonl"

KNOWN_CITY_TO_PROVINCE = {
    "深圳": "广东",
    "广州": "广东",
    "东莞": "广东",
    "惠州": "广东",
    "佛山": "广东",
    "汕头": "广东",
    "苏州": "江苏",
    "上海": "上海",
    "武汉": "湖北",
    "重庆": "重庆",
    "宁波": "浙江",
    "天津": "天津",
    "成都": "四川",
    "长沙": "湖南",
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
    "浦东新区": "上海",
    "东西湖区": "武汉",
    "渝北区": "重庆",
    "吴中区": "苏州",
    "北仑区": "宁波",
    "滨海新区": "天津",
    "惠阳区": "惠州",
    "长安镇": "东莞",
    "虎门镇": "东莞",
}

BUSINESS_KEYWORDS = [
    ("高低压配电工程", ["高低压", "高低压配电"]),
    ("变配电工程", ["变配电", "配电房", "专变"]),
    ("配电安装工程", ["配电安装", "安装工程", "配电柜"]),
    ("配电改造工程", ["改造", "升级", "扩容", "增容", "整改"]),
    ("供配电建设工程", ["供配电", "建设工程", "新建", "新增产线"]),
]

INDUSTRY_KEYWORDS = [
    ("自动化设备", ["自动化设备", "产线", "机器人"]),
    ("电子制造", ["电子厂", "电子制造", "电子装配"]),
    ("食品制造", ["食品厂", "饮料厂", "灌装线"]),
    ("医药制造", ["医药", "洁净车间"]),
    ("新能源", ["锂电", "新能源"]),
    ("商业楼宇", ["商业综合体", "办公楼", "园区"]),
]

CORE_NEED_PATTERNS = [
    "低压配电柜",
    "配电柜",
    "配电改造",
    "扩容",
    "增容",
    "供配电",
    "变配电",
    "控制柜",
    "新增产线",
    "升级",
]

CONCERN_PATTERNS = [
    "交付周期",
    "工期",
    "停线",
    "预算",
    "价格",
    "稳定性",
    "售后",
    "施工安全",
    "审批",
    "安装配合",
]

ROLE_PATTERNS = ["总经理", "老板", "采购", "设备经理", "厂务经理", "工程经理", "项目经理", "电气工程师", "联系人"]
PROJECT_INTENT_HINTS = CORE_NEED_PATTERNS + [
    "项目",
    "产线",
    "配电",
    "供电",
    "用电",
    "改造",
    "扩容",
    "预算",
    "招标",
]
CONTACT_LABELS = ["\u8054\u7cfb\u4eba", "\u5bf9\u63a5\u4eba", "\u8054\u7cfb\u7a97\u53e3", "\u8d1f\u8d23\u4eba", "\u5bf9\u63a5"]
CONTACT_NAME_BLACKLIST = {
    "\u4f4e\u538b\u914d\u7535",
    "\u9ad8\u4f4e\u538b\u914d\u7535",
    "\u62c5\u5fc3\u65bd\u5de5",
    "\u65bd\u5de5\u5f71\u54cd",
    "\u914d\u7535\u7cfb\u7edf",
    "\u8001\u65e7\u5de5\u4e1a",
    "\u5dde\u67d0\u8001\u65e7",
}


def build_empty_opportunity_record(raw_input: str) -> dict:
    """Build a complete empty opportunity record shell."""
    now = datetime.now(timezone.utc).isoformat()
    entry_timestamp = datetime.now().astimezone().isoformat()
    return {
        "record_id": f"OPP_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
        "raw_input": raw_input.strip(),
        "company_name": "",
        "contact_name": "",
        "contact_phone": "",
        "contact_role": "",
        "industry": "",
        "location_province": "",
        "location_city": "",
        "location_district": "",
        "business_type_guess": "",
        "budget_hint": "",
        "power_load_requirement": "",
        "estimated_load_kw": None,
        "core_needs": [],
        "concerns": [],
        "current_stage": "new",
        "source_type": "manual_input",
        "needs_review": False,
        "review_reasons": [],
        "entry_timestamp": entry_timestamp,
        "created_at": now,
        "updated_at": now,
    }


def _extract_phone(raw_input: str) -> str:
    match = re.search(r"(?<!\d)(1\d{10})(?!\d)", raw_input)
    if match:
        return match.group(1)
    return ""


def _extract_company_name(raw_input: str) -> str:
    company_patterns = [
        r"(某[\u4e00-\u9fa5A-Za-z0-9（）()·\-]{1,30}(?:公司|工厂|集团|厂|研究院|中心))",
        r"(?:客户是|客户为|拜访)([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,40}(?:公司|工厂|集团|厂|研究院|中心))",
        r"([\u4e00-\u9fa5A-Za-z0-9（）()·\-]{2,40}(?:公司|工厂|集团|厂|研究院|中心))",
    ]
    for pattern in company_patterns:
        match = re.search(pattern, raw_input)
        if match:
            return match.group(1).strip("，。；;：: ")
    return ""


def _normalize_contact_candidate(candidate: str) -> str:
    text = str(candidate).strip()
    if not text:
        return ""
    if text.startswith("姓") and len(text) >= 2:
        text = text[1:].strip()
    if text in {"先生", "女士", "老板", "经理", "总"}:
        return ""
    return text


def _extract_contact_name(raw_input: str) -> str:
    explicit_patterns = [
        r"(?:\u8054\u7cfb\u4eba|\u5bf9\u63a5\u4eba|\u8054\u7cfb\u7a97\u53e3|\u8d1f\u8d23\u4eba|\u5bf9\u63a5)[\u662f\u4e3a:? ]*([\u4e00-\u9fa5]{1,4}(?:\u603b|\u7ecf\u7406|\u8001\u677f|\u5de5)?)",
        r"(?:\u8054\u7cfb\u4eba|\u5bf9\u63a5\u4eba|\u8054\u7cfb\u7a97\u53e3|\u8d1f\u8d23\u4eba|\u5bf9\u63a5)[^\uFF0C\u3002\uFF1B;:\n]{0,8}([\u4e00-\u9fa5]{1,4}(?:\u603b|\u7ecf\u7406|\u8001\u677f|\u5de5))",
    ]
    for pattern in explicit_patterns:
        if "\\u" in pattern:
            pattern = pattern.encode("ascii").decode("unicode_escape")
        match = re.search(pattern, raw_input)
        if match:
            candidate = _normalize_contact_candidate(match.group(1))
            if candidate and candidate not in CONTACT_NAME_BLACKLIST:
                return candidate

    title_patterns = [
        (r"([\u4e00-\u9fa5]{2,3})(?:\u603b\u7ecf\u7406|\u7ecf\u7406|\u8001\u677f)", ""),
        (r"([\u4e00-\u9fa5]{1,3})\u5de5(?!\u4e1a|\u5382|\u7a0b|\u5730|\u4f5c|\u5177|\u671f|\u827a|\u5546|\u5e8f|\u51b5|\u6cd5|\u4f4d)", "\u5de5"),
    ]
    has_contact_label = any(label in raw_input for label in CONTACT_LABELS)
    if has_contact_label:
        for pattern, suffix in title_patterns:
            if "\\u" in pattern:
                pattern = pattern.encode("ascii").decode("unicode_escape")
            suffix_text = suffix.encode("ascii").decode("unicode_escape") if "\\u" in suffix else suffix
            match = re.search(pattern, raw_input)
            if match:
                candidate = _normalize_contact_candidate(match.group(1).strip() + suffix_text)
                if candidate and candidate not in CONTACT_NAME_BLACKLIST:
                    return candidate
    return ""

def _extract_contact_role(raw_input: str) -> str:
    for role in ROLE_PATTERNS:
        if role in raw_input:
            return role
    return ""


def _extract_budget_hint(raw_input: str) -> str:
    patterns = [
        r"预算[大概约为在]*([0-9一二三四五六七八九十百千万亿]+[万亿]?)",
        r"([0-9]+\s*万左右)",
        r"([0-9]+\s*万)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_input)
        if match:
            return re.sub(r"\s+", "", match.group(1))
    return ""


def _normalize_load_value_kw(raw_value: str, unit: str) -> float | int | None:
    try:
        numeric_value = float(raw_value)
    except (TypeError, ValueError):
        return None

    normalized_unit = unit.strip().lower()
    if normalized_unit in {"kw", "千瓦"}:
        load_kw = numeric_value
    elif normalized_unit == "mw":
        load_kw = numeric_value * 1000
    else:
        return None

    if load_kw.is_integer():
        return int(load_kw)
    return round(load_kw, 3)


def _extract_power_load_requirement(raw_input: str) -> tuple[str, float | int | None]:
    patterns = [
        re.compile(
            r"((?:(?:预计|预估)?(?:新增)?(?:用电负载|负载需求|负载|总负荷|负荷|容量需求|容量)|"
            r"(?:预计|预估)?(?:总负荷|负荷|容量)|(?:新增负载|新增容量))"
            r"(?:约|约为|大约)?\s*(\d+(?:\.\d+)?)\s*(kW|KW|kw|千瓦|MW|mw))"
        ),
        re.compile(r"((\d+(?:\.\d+)?)\s*(kW|KW|kw|千瓦|MW|mw))"),
    ]

    for pattern in patterns:
        match = pattern.search(raw_input)
        if not match:
            continue
        original_expression = re.sub(r"\s+", "", match.group(1))
        estimated_load_kw = _normalize_load_value_kw(match.group(2), match.group(3))
        return original_expression, estimated_load_kw

    return "", None


def _extract_location(raw_input: str) -> tuple[str, str, str]:
    province = ""
    city = ""
    district = ""

    for candidate_city, candidate_province in KNOWN_CITY_TO_PROVINCE.items():
        if candidate_city in raw_input:
            city = candidate_city
            province = candidate_province
            break

    for candidate_district, mapped_city in DISTRICT_TO_CITY.items():
        if candidate_district in raw_input:
            district = candidate_district
            if not city:
                city = mapped_city
                province = KNOWN_CITY_TO_PROVINCE.get(city, "")
            break

    if not province:
        province_match = re.search(r"([\u4e00-\u9fa5]{2,6})(?:省|市)", raw_input)
        if province_match:
            candidate = province_match.group(1)
            if candidate in set(KNOWN_CITY_TO_PROVINCE.values()):
                province = candidate

    return province, city, district


def _guess_business_type(raw_input: str) -> str:
    for business_type, keywords in BUSINESS_KEYWORDS:
        if any(keyword in raw_input for keyword in keywords):
            return business_type
    return ""


def _guess_industry(raw_input: str) -> str:
    for industry, keywords in INDUSTRY_KEYWORDS:
        if any(keyword in raw_input for keyword in keywords):
            return industry
    return ""


def _extract_list_by_keywords(raw_input: str, keywords: list[str]) -> list[str]:
    values: list[str] = []
    for keyword in keywords:
        if keyword in raw_input and keyword not in values:
            values.append(keyword)
    return values


def _has_project_intent(record: dict) -> bool:
    raw_input = str(record.get("raw_input", "")).strip()
    core_needs = record.get("core_needs", [])
    if not isinstance(core_needs, list):
        core_needs = []
    business_type_guess = str(record.get("business_type_guess", "")).strip()
    power_load_requirement = str(record.get("power_load_requirement", "")).strip()
    estimated_load_kw = record.get("estimated_load_kw")

    if core_needs:
        return True
    if business_type_guess:
        return True
    if power_load_requirement or estimated_load_kw is not None:
        return True
    return any(hint in raw_input for hint in PROJECT_INTENT_HINTS)


def build_review_flags(record: dict) -> tuple[bool, list[str]]:
    """Build review flags with project opportunity fields prioritized over contact fields."""
    review_reasons: list[str] = []
    company_name = str(record.get("company_name", "")).strip()
    contact_phone = str(record.get("contact_phone", "")).strip()
    current_stage = str(record.get("current_stage", "new")).strip() or "new"

    if not company_name:
        review_reasons.append("company_name missing")
    if not _has_project_intent(record):
        review_reasons.append("project intent weak")
    if current_stage == "new" and not contact_phone:
        review_reasons.append("contact_phone missing")

    return bool(review_reasons), review_reasons


def _maybe_llm_parse_placeholder(raw_input: str) -> dict:
    """Placeholder for future LLM enrichment; intentionally unused in v1."""
    return {}


def parse_opportunity_note(raw_input: str) -> dict:
    """Parse one natural-language opportunity note into a structured record."""
    record = build_empty_opportunity_record(raw_input)
    text = raw_input.strip()

    record["company_name"] = _extract_company_name(text)
    record["contact_name"] = _extract_contact_name(text)
    record["contact_phone"] = _extract_phone(text)
    record["contact_role"] = _extract_contact_role(text)
    record["industry"] = _guess_industry(text)
    province, city, district = _extract_location(text)
    record["location_province"] = province
    record["location_city"] = city
    record["location_district"] = district
    record["business_type_guess"] = _guess_business_type(text)
    record["budget_hint"] = _extract_budget_hint(text)
    (
        record["power_load_requirement"],
        record["estimated_load_kw"],
    ) = _extract_power_load_requirement(text)
    record["core_needs"] = _extract_list_by_keywords(text, CORE_NEED_PATTERNS)
    record["concerns"] = _extract_list_by_keywords(text, CONCERN_PATTERNS)

    needs_review, review_reasons = build_review_flags(record)
    record["needs_review"] = needs_review
    record["review_reasons"] = review_reasons
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    return record


def append_opportunity_record(file_path: str, record: dict) -> None:
    """Append one structured opportunity record to a JSONL buffer file."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    """Run a minimal parsing demo and persist parsed opportunity records."""
    sample_inputs = [
        "深圳某自动化客户，预计新增负载约800kW，需要低压配电柜。",
        "某工厂预计总负荷1.2MW，考虑扩容。",
        "某客户有项目，后续再确认容量。",
    ]

    for sample_input in sample_inputs:
        record = parse_opportunity_note(sample_input)
        append_opportunity_record(str(OUTPUT_FILE), record)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        print("-" * 40)

    print(f"已追加写入: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
