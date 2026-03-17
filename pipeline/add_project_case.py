import json
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "project_cases.jsonl"
REQUIRED_FIELDS = [
    "project_id",
    "project_name",
    "industry",
    "business_type",
    "location_city",
    "location_district",
    "project_amount",
    "customer_problem",
    "solution_summary",
    "project_stage",
    "owner_role",
    "duration_estimate",
    "risk_notes",
    "keywords",
    "custom_fields",
]


def _parse_json_objects(text: str, file_path: str, line_number: int) -> list[dict]:
    """Parse one or more JSON objects from a line."""
    decoder = json.JSONDecoder()
    index = 0
    length = len(text)
    items: list[dict] = []

    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
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


def validate_project_case(case: dict) -> None:
    """Validate the required schema for a single project case."""
    if not isinstance(case, dict):
        raise TypeError("Project case must be a dict.")

    missing_fields = [field for field in REQUIRED_FIELDS if field not in case]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    if not isinstance(case["project_amount"], (int, float)):
        raise TypeError("project_amount must be an int or float.")
    if not isinstance(case["risk_notes"], list):
        raise TypeError("risk_notes must be a list.")
    if not isinstance(case["keywords"], list):
        raise TypeError("keywords must be a list.")
    if not isinstance(case["custom_fields"], dict):
        raise TypeError("custom_fields must be a dict.")



def project_id_exists(cases: list[dict], project_id: str) -> bool:
    """Check whether the given project_id already exists."""
    target = str(project_id).strip()
    return any(str(case.get("project_id", "")).strip() == target for case in cases)



def append_project_case(file_path: str, case: dict) -> None:
    """Append one validated project case to the JSONL file."""
    validate_project_case(case)
    path = Path(file_path)
    with path.open("a", encoding="utf-8") as file:
        file.write("\n" + json.dumps(case, ensure_ascii=False))



def main() -> None:
    """Append a built-in sample case and print the updated count."""
    sample_new_case = {
        "project_id": "P022",
        "project_name": "某锂电材料厂动力配电扩容项目",
        "industry": "新能源材料",
        "business_type": "扩产配套 / 动力配电扩容",
        "location_city": "惠州",
        "location_district": "惠阳区",
        "project_amount": 880000,
        "customer_problem": "客户扩产后原有动力配电容量不足，希望尽快补齐配电系统并控制停线影响。",
        "solution_summary": "结合新增负载完成动力配电扩容方案，按窗口期分段实施，兼顾交付进度与现场切换风险。",
        "project_stage": "已交付",
        "owner_role": "销售+方案工程师",
        "duration_estimate": "5周",
        "risk_notes": ["停线窗口有限", "现场切换需与生产计划联动"],
        "keywords": ["扩产", "动力配电", "扩容", "交付周期"],
        "custom_fields": {
            "decision_chain": "设备部与厂务共同确认",
            "delivery_constraints": "需利用夜间窗口分段切换",
            "customer_style": "关注交付稳定性和实施节奏"
        }
    }

    try:
        cases = load_project_cases(str(DATA_FILE))
        validate_project_case(sample_new_case)

        if project_id_exists(cases, sample_new_case["project_id"]):
            raise ValueError(
                f"project_id already exists: {sample_new_case['project_id']}"
            )

        append_project_case(str(DATA_FILE), sample_new_case)
        updated_cases = load_project_cases(str(DATA_FILE))

        print(f"新增项目名称: {sample_new_case['project_name']}")
        print(f"当前项目总数: {len(updated_cases)}")
    except (FileNotFoundError, ValueError, TypeError, OSError) as exc:
        print(f"执行失败: {exc}")


if __name__ == "__main__":
    main()
