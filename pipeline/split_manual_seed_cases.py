import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT_DIR / "data" / "project_cases_cleaned.jsonl"
SEED_OUTPUT_FILE = ROOT_DIR / "data" / "project_cases_manual_seed.jsonl"

MANUAL_SEED_IDS = {f"P{i:03d}" for i in range(1, 21)}


def load_cases(file_path: Path) -> list[dict]:
    """Load JSONL cases from disk."""
    if not file_path.exists():
        raise FileNotFoundError(f"Case file not found: {file_path}")

    cases: list[dict] = []
    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            content = line.strip()
            if not content:
                continue
            try:
                case = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} in {file_path}: {exc}"
                ) from exc
            if not isinstance(case, dict):
                raise ValueError(
                    f"Invalid record on line {line_number} in {file_path}: expected object"
                )
            cases.append(case)
    return cases


def is_manual_seed_case(case: dict) -> bool:
    """Identify the earliest hand-written seed cases by explicit project_id rule."""
    project_id = str(case.get("project_id", "")).strip()
    return project_id in MANUAL_SEED_IDS


def write_cases(file_path: Path, cases: list[dict]) -> None:
    """Write JSONL cases to disk."""
    with file_path.open("w", encoding="utf-8") as file:
        for case in cases:
            file.write(json.dumps(case, ensure_ascii=False) + "\n")


def _preview_cases(cases: list[dict], limit: int = 3) -> list[dict]:
    preview: list[dict] = []
    for case in cases[:limit]:
        preview.append(
            {
                "project_id": case.get("project_id", ""),
                "project_name": case.get("project_name", ""),
            }
        )
    return preview


def main() -> None:
    """Split explicit manual seed cases from the main cleaned case library."""
    try:
        all_cases = load_cases(INPUT_FILE)
        manual_seed_cases = [case for case in all_cases if is_manual_seed_case(case)]
        remaining_cases = [case for case in all_cases if not is_manual_seed_case(case)]

        seed_file_preexisted = SEED_OUTPUT_FILE.exists()

        write_cases(SEED_OUTPUT_FILE, manual_seed_cases)
        write_cases(INPUT_FILE, remaining_cases)

        print(f"总记录数: {len(all_cases)}")
        print("手工测试样本识别规则: project_id 精确命中 P001-P020")
        print(f"识别出的手工样本数: {len(manual_seed_cases)}")
        print(f"保留在主库中的记录数: {len(remaining_cases)}")
        print(
            "seed 文件状态: "
            + ("已覆盖已有文件" if seed_file_preexisted else "新建文件")
        )
        print(f"手工样本文件路径: {SEED_OUTPUT_FILE}")
        print(f"主库文件路径: {INPUT_FILE}")
        print(
            "seed 样本预览: "
            + json.dumps(_preview_cases(manual_seed_cases), ensure_ascii=False)
        )
        print(
            "主库保留样本预览: "
            + json.dumps(_preview_cases(remaining_cases), ensure_ascii=False)
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"执行失败: {exc}")


if __name__ == "__main__":
    main()
