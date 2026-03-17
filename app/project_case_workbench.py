import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.init_app_db import DB_FILE, get_connection, init_app_db
from pipeline.manage_opportunity_records import create_followup, delete_opportunity, list_followups, list_opportunities, update_opportunity
from pipeline.retrieve_similar_projects import load_project_cases, retrieve_similar_projects
from pipeline.run_opportunity_flow import run_opportunity_flow


DATA_FILE = ROOT_DIR / "data" / "project_cases_cleaned.jsonl"
CORRECTION_LOG_FILE = ROOT_DIR / 'data' / 'review_corrections.jsonl'
OPPORTUNITY_RECORD_FILE = ROOT_DIR / 'data' / 'opportunity_records.jsonl'
SUSPECT_CITIES = {
    "", "建设地点", "采力光明"
}
EDITABLE_REVIEW_FIELDS = [
    "location_province",
    "location_city",
    "location_district",
    "business_type",
    "keywords",
    "custom_fields.location_scene_label",
]
EDITABLE_OPPORTUNITY_FIELDS = [
    "company_name",
    "contact_name",
    "contact_phone",
    "contact_role",
    "industry",
    "business_type_guess",
    "power_load_requirement",
    "estimated_load_kw",
    "budget_hint",
    "core_needs",
    "concerns",
    "current_stage",
]


@st.cache_data
def load_cases() -> list[dict]:
    """Load project cases for the workbench."""
    return load_project_cases(str(DATA_FILE))



def write_cases(cases: list[dict]) -> None:
    """Persist the edited case list to JSONL."""
    with DATA_FILE.open("w", encoding="utf-8") as file:
        for case in cases:
            file.write(json.dumps(case, ensure_ascii=False) + "\n")
    load_cases.clear()


@st.cache_data
def load_opportunity_records() -> list[dict]:
    """Load opportunity history records from SQLite, newest first."""
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        return list_opportunities(conn)



def get_latest_followup(opportunity_id: int) -> dict:
    """Load the latest follow-up for one opportunity from SQLite."""
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        followups = list_followups(conn, opportunity_id)
    return followups[0] if followups else {}



def append_correction_log(entry: dict) -> None:
    """Append one correction log entry to JSONL."""
    CORRECTION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CORRECTION_LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")



def write_opportunity_records(records: list[dict]) -> None:
    """Legacy placeholder kept for compatibility after SQLite migration."""
    load_opportunity_records.clear()


def get_opportunity_record_key(record: dict, index: int) -> str:
    """Build a stable key for one opportunity history record."""
    opportunity_id = record.get("id")
    if opportunity_id not in (None, ""):
        return f"db:{opportunity_id}"
    record_id = str(record.get("record_id", "")).strip()
    if record_id:
        return record_id
    created_at = str(record.get("created_at", "")).strip()
    company_name = str(record.get("company_name", "")).strip()
    return f"idx:{index}:{created_at}:{company_name}"


def get_opportunity_snapshot(record: dict) -> dict:
    """Extract editable opportunity fields for correction logs and diffs."""
    core_needs = record.get("core_needs", [])
    if not isinstance(core_needs, list):
        core_needs = []

    concerns = record.get("concerns", [])
    if not isinstance(concerns, list):
        concerns = []

    estimated_load_kw = record.get("estimated_load_kw")
    if estimated_load_kw in ("", None):
        normalized_estimated_load_kw = None
    else:
        try:
            numeric_value = float(estimated_load_kw)
        except (TypeError, ValueError):
            normalized_estimated_load_kw = None
        else:
            normalized_estimated_load_kw = int(numeric_value) if numeric_value.is_integer() else numeric_value

    return {
        "company_name": str(record.get("company_name", "")).strip(),
        "contact_name": str(record.get("contact_name", "")).strip(),
        "contact_phone": str(record.get("contact_phone", "")).strip(),
        "contact_role": str(record.get("contact_role", "")).strip(),
        "industry": str(record.get("industry", "")).strip(),
        "business_type_guess": str(record.get("business_type_guess", "")).strip(),
        "power_load_requirement": str(record.get("power_load_requirement", "")).strip(),
        "estimated_load_kw": normalized_estimated_load_kw,
        "budget_hint": str(record.get("budget_hint", "")).strip(),
        "core_needs": [str(item).strip() for item in core_needs if str(item).strip()],
        "concerns": [str(item).strip() for item in concerns if str(item).strip()],
        "current_stage": str(record.get("current_stage", "")).strip(),
    }



def build_opportunity_before_after_diff(before: dict, after: dict | None) -> list[dict]:
    """Build a minimal before/after diff for editable opportunity fields."""
    diff_rows: list[dict] = []
    for field in EDITABLE_OPPORTUNITY_FIELDS:
        before_value = before.get(field)
        after_value = None if after is None else after.get(field)
        if before_value != after_value:
            diff_rows.append(
                {
                    "field": field,
                    "before": _format_diff_value(before_value),
                    "after": _format_diff_value(after_value),
                }
            )
    return diff_rows



def _split_csv_text(value: str) -> list[str]:
    """Split comma-separated text into a cleaned string list."""
    return [item.strip() for item in value.split(",") if item.strip()]



def _parse_estimated_load_kw(value: str) -> float | int | None:
    """Parse the estimated load text input into number or null."""
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        numeric_value = float(cleaned)
    except ValueError:
        return None
    return int(numeric_value) if numeric_value.is_integer() else numeric_value



def build_opportunity_update(record: dict, form_data: dict) -> dict:
    """Apply editable form fields to one opportunity record."""
    updated_record = dict(record)
    updated_record["company_name"] = form_data["company_name"].strip()
    updated_record["contact_name"] = form_data["contact_name"].strip()
    updated_record["contact_phone"] = form_data["contact_phone"].strip()
    updated_record["contact_role"] = form_data["contact_role"].strip()
    updated_record["industry"] = form_data["industry"].strip()
    updated_record["business_type_guess"] = form_data["business_type_guess"].strip()
    if "power_load_requirement" in record or form_data.get("power_load_requirement", "").strip():
        updated_record["power_load_requirement"] = form_data.get("power_load_requirement", "").strip()
    if "estimated_load_kw" in record or form_data.get("estimated_load_kw", "").strip():
        updated_record["estimated_load_kw"] = _parse_estimated_load_kw(form_data.get("estimated_load_kw", ""))
    updated_record["budget_hint"] = form_data["budget_hint"].strip()
    updated_record["core_needs"] = _split_csv_text(form_data["core_needs"])
    updated_record["concerns"] = _split_csv_text(form_data["concerns"])
    updated_record["current_stage"] = form_data["current_stage"].strip()
    updated_record["updated_at"] = datetime.now(timezone.utc).isoformat()
    return updated_record



def _get_opportunity_id_from_record(record: dict, record_key: str) -> int:
    """Resolve one opportunity primary key from record payload or UI key."""
    opportunity_id = record.get("id")
    if opportunity_id not in (None, ""):
        return int(opportunity_id)
    if record_key.startswith("db:"):
        return int(record_key.split(":", 1)[1])
    raise ValueError("Missing opportunity id for update")


def update_opportunity_record(records: list[dict], record_key: str, updated_record: dict) -> None:
    """Update one opportunity history record in SQLite."""
    opportunity_id = _get_opportunity_id_from_record(updated_record, record_key)
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        update_opportunity(conn, opportunity_id, updated_record)
    load_opportunity_records.clear()


def delete_opportunity_record(records: list[dict], record_key: str) -> None:
    """Delete one opportunity history record from SQLite."""
    matched_record = next(
        (record for index, record in enumerate(records) if get_opportunity_record_key(record, index) == record_key),
        None,
    )
    if matched_record is None:
        raise ValueError("Opportunity record not found")
    opportunity_id = _get_opportunity_id_from_record(matched_record, record_key)
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        delete_opportunity(conn, opportunity_id)
    load_opportunity_records.clear()


def append_opportunity_correction_log(record_id: str, action: str, before: dict, after: dict | None) -> None:
    """Append one opportunity edit/delete correction log entry."""
    append_correction_log(
        {
            "record_type": "opportunity",
            "record_id": record_id,
            "action": action,
            "before": before,
            "after": after,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )



def save_opportunity_record(records: list[dict], before_record: dict, after_record: dict, record_key: str) -> None:
    """Persist one opportunity edit and append a correction log."""
    before_snapshot = get_opportunity_snapshot(before_record)
    after_snapshot = get_opportunity_snapshot(after_record)
    record_id = str(before_record.get("id", "")).strip() or str(before_record.get("record_id", "")).strip() or record_key
    update_opportunity_record(records, record_key, after_record)
    append_opportunity_correction_log(record_id, "manual_edit", before_snapshot, after_snapshot)


def remove_opportunity_record(records: list[dict], record: dict, record_key: str) -> None:
    """Delete one opportunity record and append a correction log."""
    before_snapshot = get_opportunity_snapshot(record)
    record_id = str(record.get("id", "")).strip() or str(record.get("record_id", "")).strip() or record_key
    delete_opportunity_record(records, record_key)
    append_opportunity_correction_log(record_id, "delete", before_snapshot, None)


def format_amount(project_amount: object) -> str:
    """Format project amount as ten-thousand yuan."""
    try:
        amount = float(project_amount)
    except (TypeError, ValueError):
        amount = 0.0
    return f"{amount / 10000:.1f} 万元"



def filter_cases(
    cases: list[dict], keyword: str, city: str, amount_range: str
) -> list[dict]:
    """Filter cases by keyword, city, and amount range."""
    normalized_keyword = keyword.strip().lower()
    filtered: list[dict] = []

    for case in cases:
        haystacks = [
            str(case.get("project_name", "")),
            str(case.get("company_name", "")),
            str(case.get("business_type", "")),
            " ".join(str(item) for item in case.get("keywords", []) if item),
        ]
        search_text = " ".join(haystacks).lower()
        if normalized_keyword and normalized_keyword not in search_text:
            continue

        case_city = str(case.get("location_city", "")).strip()
        if city != "全部" and case_city != city:
            continue

        try:
            amount = float(case.get("project_amount", 0) or 0)
        except (TypeError, ValueError):
            amount = 0.0

        if amount_range == "30万以下" and amount >= 300000:
            continue
        if amount_range == "30万-100万" and not (300000 <= amount <= 1000000):
            continue
        if amount_range == "100万以上" and amount <= 1000000:
            continue

        filtered.append(case)

    return filtered



def render_case_detail(case: dict) -> None:
    """Render one case detail block."""
    st.json(case, expanded=False)



def find_suspect_cities(cases: list[dict]) -> list[str]:
    """Find city values that likely need manual cleanup."""
    suspects = set()
    for case in cases:
        city = str(case.get("location_city", "")).strip()
        if city in SUSPECT_CITIES:
            suspects.add(city or "<空值>")
    return sorted(suspects)



def update_case(cases: list[dict], project_id: str, updated_case: dict) -> None:
    """Update one case by project_id and persist."""
    new_cases = []
    for case in cases:
        if str(case.get("project_id", "")) == project_id:
            new_cases.append(updated_case)
        else:
            new_cases.append(case)
    write_cases(new_cases)



def delete_case(cases: list[dict], project_id: str) -> None:
    """Delete one case by project_id and persist."""
    new_cases = [case for case in cases if str(case.get("project_id", "")) != project_id]
    write_cases(new_cases)



def get_review_cases(cases: list[dict]) -> list[dict]:
    """Return only review queue records."""
    return [case for case in cases if bool(case.get("needs_review"))]



def get_review_summary(cases: list[dict]) -> Counter[str]:
    """Aggregate review reason counts."""
    counter: Counter[str] = Counter()
    for case in cases:
        reasons = case.get("review_reasons", [])
        if isinstance(reasons, list):
            counter.update(str(reason).strip() for reason in reasons if str(reason).strip())
    return counter



def get_case_snapshot(case: dict) -> dict:
    """Extract the minimal governed field snapshot for correction logs and diffs."""
    custom_fields = case.get("custom_fields", {})
    if not isinstance(custom_fields, dict):
        custom_fields = {}

    keywords = case.get("keywords", [])
    if not isinstance(keywords, list):
        keywords = []

    return {
        "location_province": str(case.get("location_province", "")).strip(),
        "location_city": str(case.get("location_city", "")).strip(),
        "location_district": str(case.get("location_district", "")).strip(),
        "business_type": str(case.get("business_type", "")).strip(),
        "keywords": [str(item).strip() for item in keywords if str(item).strip()],
        "custom_fields.location_scene_label": str(
            custom_fields.get("location_scene_label", "")
        ).strip(),
    }



def _format_diff_value(value: object) -> str:
    """Render diff values as plain strings for stable Streamlit table output."""
    if value is None:
        return "null"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)



def build_before_after_diff(before: dict, after: dict | None) -> list[dict]:
    """Build a minimal before/after diff for governed fields."""
    diff_rows: list[dict] = []
    for field in EDITABLE_REVIEW_FIELDS:
        before_value = before.get(field)
        after_value = None if after is None else after.get(field)
        if before_value != after_value:
            diff_rows.append(
                {
                    "field": field,
                    "before": _format_diff_value(before_value),
                    "after": _format_diff_value(after_value),
                }
            )
    return diff_rows



def build_review_update(case: dict, form_data: dict) -> dict:
    """Apply governed field edits to one review record."""
    updated_case = dict(case)
    updated_case["location_province"] = form_data["location_province"].strip()
    updated_case["location_city"] = form_data["location_city"].strip()
    updated_case["location_district"] = form_data["location_district"].strip()
    updated_case["business_type"] = form_data["business_type"].strip()
    updated_case["keywords"] = [
        item.strip() for item in form_data["keywords"].split(",") if item.strip()
    ]

    custom_fields = updated_case.get("custom_fields", {})
    if not isinstance(custom_fields, dict):
        custom_fields = {}
    scene_label = form_data["location_scene_label"].strip()
    if scene_label:
        custom_fields["location_scene_label"] = scene_label
    else:
        custom_fields.pop("location_scene_label", None)
    updated_case["custom_fields"] = custom_fields
    return updated_case



def save_review_case(cases: list[dict], before_case: dict, after_case: dict) -> None:
    """Persist one review edit and append a correction log."""
    project_id = str(before_case.get("project_id", ""))
    before_snapshot = get_case_snapshot(before_case)
    after_snapshot = get_case_snapshot(after_case)
    update_case(cases, project_id, after_case)
    append_correction_log(
        {
            "project_id": project_id,
            "action": "manual_edit",
            "before": before_snapshot,
            "after": after_snapshot,
            "review_reasons": list(before_case.get("review_reasons", []) or []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )



def remove_review_case(cases: list[dict], case: dict) -> None:
    """Delete one review record and append a correction log."""
    project_id = str(case.get("project_id", ""))
    before_snapshot = get_case_snapshot(case)
    delete_case(cases, project_id)
    append_correction_log(
        {
            "project_id": project_id,
            "action": "delete",
            "before": before_snapshot,
            "after": None,
            "review_reasons": list(case.get("review_reasons", []) or []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )



def render_review_summary(review_cases: list[dict]) -> None:
    """Render Review Queue summary cards and top reasons."""
    st.markdown("#### Review Queue Summary")
    reason_counter = get_review_summary(review_cases)
    summary_col1, summary_col2 = st.columns([1, 2])
    with summary_col1:
        st.metric("待治理记录数", len(review_cases))
    with summary_col2:
        if reason_counter:
            st.write("Review reasons Top 5")
            for reason, count in reason_counter.most_common(5):
                st.write(f"- {reason}: {count}")
        else:
            st.write("当前没有 review reasons。")



def render_review_list(review_cases: list[dict]) -> str | None:
    """Render the review record selector and return selected project_id."""
    st.markdown("#### Review Record List")
    if not review_cases:
        st.info("当前没有 needs_review=true 的记录。")
        return None

    labels = [
        f"{case.get('project_id', '')} | {case.get('project_name', '')} | {', '.join(case.get('review_reasons', []) or [])}"
        for case in review_cases
    ]
    selected_label = st.radio(
        "选择一条待治理记录",
        options=labels,
        key="review_queue_selected_label",
    )
    selected_index = labels.index(selected_label)

    with st.expander("展开查看全部待 review 记录", expanded=False):
        for case in review_cases:
            st.write(
                f"- {case.get('project_id', '')} | {case.get('project_name', '')} | {', '.join(case.get('review_reasons', []) or [])}"
            )

    return str(review_cases[selected_index].get("project_id", ""))



def render_record_editor(cases: list[dict], case: dict) -> None:
    """Render the inspector, editable form, diff view, and save/delete actions."""
    project_id = str(case.get("project_id", ""))
    custom_fields = case.get("custom_fields", {})
    if not isinstance(custom_fields, dict):
        custom_fields = {}

    before_snapshot = get_case_snapshot(case)
    form_prefix = f"review_form_{project_id}"

    st.markdown("#### Record Inspector / Editor")
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.write(f"project_id: {project_id}")
        st.write(f"project_name: {case.get('project_name', '') or '-'}")
        st.write(f"review_reasons: {', '.join(case.get('review_reasons', []) or []) or '-'}")
    with top_col2:
        st.write(f"LLM attempted: {bool(case.get('llm_enrichment_attempted'))}")
        st.write(f"LLM succeeded: {bool(case.get('llm_enrichment_succeeded'))}")

    source_col1, source_col2 = st.columns(2)
    with source_col1:
        st.markdown("**当前标准化字段**")
        st.json(before_snapshot, expanded=True)
    with source_col2:
        st.markdown("**原始相关字段 / custom_fields**")
        source_payload = {
            "company_name": case.get("company_name", ""),
            "industry": case.get("industry", ""),
            "customer_problem": case.get("customer_problem", ""),
            "solution_summary": case.get("solution_summary", ""),
            "project_stage": case.get("project_stage", ""),
            "owner_role": case.get("owner_role", ""),
            "duration_estimate": case.get("duration_estimate", ""),
            "custom_fields": custom_fields,
        }
        st.json(source_payload, expanded=False)

    default_keywords = ", ".join(before_snapshot["keywords"])
    draft_form_data = {
        "location_province": st.session_state.get(f"{form_prefix}_location_province", before_snapshot["location_province"]),
        "location_city": st.session_state.get(f"{form_prefix}_location_city", before_snapshot["location_city"]),
        "location_district": st.session_state.get(f"{form_prefix}_location_district", before_snapshot["location_district"]),
        "business_type": st.session_state.get(f"{form_prefix}_business_type", before_snapshot["business_type"]),
        "keywords": st.session_state.get(f"{form_prefix}_keywords", default_keywords),
        "location_scene_label": st.session_state.get(
            f"{form_prefix}_location_scene_label",
            before_snapshot["custom_fields.location_scene_label"],
        ),
    }
    draft_case = build_review_update(case, draft_form_data)
    diff_rows = build_before_after_diff(before_snapshot, get_case_snapshot(draft_case))

    st.markdown("#### Minimal Diff View")
    if diff_rows:
        st.table(diff_rows)
    else:
        st.write("当前无差异。")

    with st.form(f"review_editor_{project_id}"):
        st.markdown("**可编辑字段**")
        edit_col1, edit_col2 = st.columns(2)
        with edit_col1:
            edited_province = st.text_input(
                "location_province",
                value=draft_form_data["location_province"],
                key=f"{form_prefix}_location_province",
            )
            edited_city = st.text_input(
                "location_city",
                value=draft_form_data["location_city"],
                key=f"{form_prefix}_location_city",
            )
            edited_district = st.text_input(
                "location_district",
                value=draft_form_data["location_district"],
                key=f"{form_prefix}_location_district",
            )
        with edit_col2:
            edited_business_type = st.text_input(
                "business_type",
                value=draft_form_data["business_type"],
                key=f"{form_prefix}_business_type",
            )
            edited_keywords = st.text_input(
                "keywords（逗号分隔）",
                value=draft_form_data["keywords"],
                key=f"{form_prefix}_keywords",
            )
            edited_scene_label = st.text_input(
                "custom_fields.location_scene_label",
                value=draft_form_data["location_scene_label"],
                key=f"{form_prefix}_location_scene_label",
            )
        submitted = st.form_submit_button("保存修改", type="primary")

    if submitted:
        updated_case = build_review_update(
            case,
            {
                "location_province": edited_province,
                "location_city": edited_city,
                "location_district": edited_district,
                "business_type": edited_business_type,
                "keywords": edited_keywords,
                "location_scene_label": edited_scene_label,
            },
        )
        save_review_case(cases, case, updated_case)
        st.success(f"已保存 review 修改: {project_id}")
        st.rerun()

    delete_key = f"confirm_delete_{project_id}"
    action_col1, action_col2 = st.columns([1, 2])
    with action_col1:
        if st.button("删除该条记录", key=f"delete_trigger_{project_id}"):
            st.session_state[delete_key] = True
    with action_col2:
        st.caption("删除会写回 cleaned 文件并追加 correction log。")

    if st.session_state.get(delete_key):
        st.warning(f"确认删除 {project_id} 吗？此操作不可恢复。")
        confirm_col1, confirm_col2 = st.columns(2)
        with confirm_col1:
            if st.button("确认删除", key=f"delete_confirm_{project_id}"):
                remove_review_case(cases, case)
                st.session_state.pop(delete_key, None)
                st.success(f"已删除: {project_id}")
                st.rerun()
        with confirm_col2:
            if st.button("取消", key=f"delete_cancel_{project_id}"):
                st.session_state.pop(delete_key, None)
                st.rerun()



def render_review_workbench(cases: list[dict]) -> None:
    """Render the calibration / review queue workspace."""
    st.subheader("数据校准 / Review Queue")
    st.caption("只面向 needs_review=true 的记录，支持逐条查看、人工修订、删除和 correction log 留痕。")

    review_cases = get_review_cases(cases)
    render_review_summary(review_cases)
    selected_project_id = render_review_list(review_cases)
    if not selected_project_id:
        return

    selected_case = next(
        (case for case in review_cases if str(case.get("project_id", "")) == selected_project_id),
        None,
    )
    if selected_case is None:
        st.info("未找到选中的 review 记录。")
        return

    render_record_editor(cases, selected_case)



def render_library_browser(cases: list[dict]) -> None:
    """Render the original project library browser."""
    suspect_cities = find_suspect_cities(cases)
    if suspect_cities:
        st.warning("疑似异常城市值: " + "、".join(suspect_cities))

    st.subheader("区块 A：项目库浏览器")
    st.write(f"当前案例总数: {len(cases)}")

    all_cities = sorted(
        {str(case.get('location_city', '')).strip() for case in cases if case.get('location_city')}
    )
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        keyword = st.text_input("关键词搜索", placeholder="搜索项目名称 / 建设单位 / 业务类型 / 关键词")
    with col2:
        city = st.selectbox("城市筛选", ["全部", *all_cities])
    with col3:
        amount_range = st.selectbox(
            "金额区间",
            ["全部", "30万以下", "30万-100万", "100万以上"],
        )

    filtered_cases = filter_cases(cases, keyword, city, amount_range)
    st.write(f"筛选后项目数: {len(filtered_cases)}")

    for case in filtered_cases:
        project_id = str(case.get("project_id", ""))
        title = f"{project_id} | {case.get('project_name', '')}"
        with st.expander(title):
            st.write(f"建设单位: {case.get('company_name', '') or '-'}")
            st.write(f"业务类型: {case.get('business_type', '') or '-'}")
            st.write(
                f"地区: {case.get('location_city', '') or '-'} {case.get('location_district', '') or ''}"
            )
            st.write(f"项目金额: {format_amount(case.get('project_amount', 0))}")

            with st.form(f"edit_{project_id}"):
                edited_project_name = st.text_input("项目名称", value=str(case.get("project_name", "")))
                edited_company_name = st.text_input("建设单位", value=str(case.get("company_name", "")))
                edited_business_type = st.text_input("业务类型", value=str(case.get("business_type", "")))
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    edited_city = st.text_input("城市", value=str(case.get("location_city", "")))
                with edit_col2:
                    edited_district = st.text_input("区县", value=str(case.get("location_district", "")))
                edited_amount = st.number_input(
                    "项目金额（元）",
                    min_value=0.0,
                    value=float(case.get("project_amount", 0) or 0),
                    step=10000.0,
                )
                edited_keywords = st.text_input(
                    "关键词（逗号分隔）",
                    value=", ".join(str(item) for item in case.get("keywords", []) if item),
                )
                submitted = st.form_submit_button("保存修改")

            action_col1, action_col2 = st.columns([1, 3])
            with action_col1:
                deleted = st.button("删除该条", key=f"delete_{project_id}")
            with action_col2:
                st.caption("删除会直接写回 cleaned 文件，请谨慎操作。")

            if submitted:
                updated_case = dict(case)
                updated_case["project_name"] = edited_project_name.strip()
                updated_case["company_name"] = edited_company_name.strip()
                updated_case["business_type"] = edited_business_type.strip()
                updated_case["location_city"] = edited_city.strip()
                updated_case["location_district"] = edited_district.strip()
                updated_case["project_amount"] = int(edited_amount)
                updated_case["keywords"] = [
                    item.strip() for item in edited_keywords.split(",") if item.strip()
                ]
                update_case(cases, project_id, updated_case)
                st.success(f"已保存: {project_id}")
                st.rerun()

            if deleted:
                delete_case(cases, project_id)
                st.success(f"已删除: {project_id}")
                st.rerun()

            render_case_detail(case)



def render_top_k_cases(cases: list[dict]) -> None:
    """Render retrieved top-k project cases for the opportunity flow."""
    st.markdown("#### Top-K 相似项目")
    if not cases:
        st.info("当前未检索到相似项目。")
        return

    for item in cases:
        title = f"{item.get('project_id', '')} | {item.get('project_name', '')} | score={item.get('score', 0)}"
        with st.expander(title, expanded=False):
            st.write(f"project_id: {item.get('project_id', '')}")
            st.write(f"project_name: {item.get('project_name', '')}")
            st.write(f"score: {item.get('score', 0)}")
            st.write("matched_reasons:")
            reasons = item.get("matched_reasons", []) or ["无明确命中原因"]
            for reason in reasons:
                st.write(f"- {reason}")



def render_talking_points(points: list[str]) -> None:
    """Render minimal talking points for the opportunity flow."""
    st.markdown("#### 推荐讲点")
    if not points:
        st.info("当前没有可展示的 talking points。")
        return
    for point in points:
        st.write(f"- {point}")



def render_followup_suggestion(result: dict) -> None:
    """Render follow-up suggestion from the opportunity flow result."""
    st.markdown("#### 跟进建议")
    st.write(f"建议时间: {result.get('followup_time_suggestion', '') or '-'}")
    st.write(f"原因: {result.get('followup_time_reason', '') or '-'}")



def render_opportunity_flow_section() -> None:
    """Render the end-to-end opportunity flow demo section."""
    st.subheader("机会输入 / Opportunity Flow")
    st.caption("输入一段客户或项目描述，运行主链并查看结构化机会、相似案例、推荐讲点和跟进建议。")

    default_input = (
        "深圳宝安一个自动化设备客户，联系人王工，电话13800138000，最近新增产线，"
        "需要低压配电柜，担心交付周期，预算几十万。"
    )
    raw_input = st.text_area(
        "客户/项目自然语言描述",
        value=default_input,
        height=140,
        key="opportunity_flow_input",
    )

    if st.button("运行主链", type="primary", key="run_opportunity_flow_button"):
        if not raw_input.strip():
            st.warning("请输入客户或项目描述。")
            return

        try:
            result = run_opportunity_flow(raw_input.strip())
        except (FileNotFoundError, ValueError, OSError) as exc:
            st.error(f"主链运行失败: {exc}")
            return
        except Exception as exc:
            st.error(f"主链运行异常: {exc}")
            return

        st.markdown("#### 结构化机会对象")
        st.json(result.get("opportunity", {}), expanded=True)
        render_top_k_cases(result.get("top_k_cases", []))
        render_talking_points(result.get("recommended_talking_points", []))
        render_followup_suggestion(result)



def render_opportunity_record_detail(record: dict) -> None:
    """Render one opportunity record detail block."""
    st.markdown("#### 机会记录详情")
    summary_col1, summary_col2 = st.columns(2)
    with summary_col1:
        st.write(f"record_id: {record.get('record_id', '') or '-'}")
        st.write(f"当前 stage: {record.get('current_stage', '') or '-'}")
        st.write(f"company_name: {record.get('company_name', '') or '未识别'}")
        st.write(f"contact_name: {record.get('contact_name', '') or '未识别'}")
        st.write(f"contact_phone: {record.get('contact_phone', '') or '未识别'}")
    with summary_col2:
        core_needs = record.get('core_needs', [])
        concerns = record.get('concerns', [])
        st.write(f"core_needs: {', '.join(core_needs) if isinstance(core_needs, list) and core_needs else '-'}")
        st.write(f"concerns: {', '.join(concerns) if isinstance(concerns, list) and concerns else '-'}")
        st.write(f"entry_timestamp: {record.get('entry_timestamp', '') or record.get('created_at', '') or '-'}")
        st.write(f"created_at: {record.get('created_at', '') or '-'}")
        st.write(f"updated_at: {record.get('updated_at', '') or '-'}")

    talking_points = record.get('recommended_talking_points', [])
    if isinstance(talking_points, list) and talking_points:
        st.markdown("#### 历史讲点")
        for point in talking_points:
            st.write(f"- {point}")

    followup_time_suggestion = record.get('followup_time_suggestion', '')
    followup_time_reason = record.get('followup_time_reason', '')
    if followup_time_suggestion or followup_time_reason:
        st.markdown("#### 历史跟进建议")
        st.write(f"建议时间: {followup_time_suggestion or '-'}")
        st.write(f"原因: {followup_time_reason or '-'}")

    st.markdown("#### 完整结构化机会对象")
    st.json(record, expanded=True)



def render_opportunity_record_editor(records: list[dict], record: dict, record_key: str) -> None:
    """Render the editable opportunity history form and save/delete actions."""
    before_snapshot = get_opportunity_snapshot(record)
    has_load_fields = "power_load_requirement" in record or "estimated_load_kw" in record
    safe_key = ''.join(char if char.isalnum() else '_' for char in record_key)
    form_prefix = f"opportunity_form_{safe_key}"

    draft_form_data = {
        "company_name": st.session_state.get(f"{form_prefix}_company_name", before_snapshot["company_name"]),
        "contact_name": st.session_state.get(f"{form_prefix}_contact_name", before_snapshot["contact_name"]),
        "contact_phone": st.session_state.get(f"{form_prefix}_contact_phone", before_snapshot["contact_phone"]),
        "contact_role": st.session_state.get(f"{form_prefix}_contact_role", before_snapshot["contact_role"]),
        "industry": st.session_state.get(f"{form_prefix}_industry", before_snapshot["industry"]),
        "business_type_guess": st.session_state.get(f"{form_prefix}_business_type_guess", before_snapshot["business_type_guess"]),
        "power_load_requirement": st.session_state.get(f"{form_prefix}_power_load_requirement", before_snapshot["power_load_requirement"]),
        "estimated_load_kw": st.session_state.get(
            f"{form_prefix}_estimated_load_kw",
            "" if before_snapshot["estimated_load_kw"] is None else str(before_snapshot["estimated_load_kw"]),
        ),
        "budget_hint": st.session_state.get(f"{form_prefix}_budget_hint", before_snapshot["budget_hint"]),
        "core_needs": st.session_state.get(f"{form_prefix}_core_needs", ", ".join(before_snapshot["core_needs"])),
        "concerns": st.session_state.get(f"{form_prefix}_concerns", ", ".join(before_snapshot["concerns"])),
        "current_stage": st.session_state.get(f"{form_prefix}_current_stage", before_snapshot["current_stage"]),
    }
    draft_record = build_opportunity_update(record, draft_form_data)
    diff_rows = build_opportunity_before_after_diff(before_snapshot, get_opportunity_snapshot(draft_record))

    st.markdown("#### 编辑机会记录")
    if diff_rows:
        st.table(diff_rows)
    else:
        st.write("当前无差异。")

    with st.form(f"opportunity_editor_{safe_key}"):
        edit_col1, edit_col2 = st.columns(2)
        with edit_col1:
            edited_company_name = st.text_input(
                "company_name",
                value=draft_form_data["company_name"],
                key=f"{form_prefix}_company_name",
            )
            edited_contact_name = st.text_input(
                "contact_name",
                value=draft_form_data["contact_name"],
                key=f"{form_prefix}_contact_name",
            )
            edited_contact_phone = st.text_input(
                "contact_phone",
                value=draft_form_data["contact_phone"],
                key=f"{form_prefix}_contact_phone",
            )
            edited_contact_role = st.text_input(
                "contact_role",
                value=draft_form_data["contact_role"],
                key=f"{form_prefix}_contact_role",
            )
            edited_industry = st.text_input(
                "industry",
                value=draft_form_data["industry"],
                key=f"{form_prefix}_industry",
            )
            edited_business_type_guess = st.text_input(
                "business_type_guess",
                value=draft_form_data["business_type_guess"],
                key=f"{form_prefix}_business_type_guess",
            )
        with edit_col2:
            edited_budget_hint = st.text_input(
                "budget_hint",
                value=draft_form_data["budget_hint"],
                key=f"{form_prefix}_budget_hint",
            )
            edited_core_needs = st.text_input(
                "core_needs（逗号分隔）",
                value=draft_form_data["core_needs"],
                key=f"{form_prefix}_core_needs",
            )
            edited_concerns = st.text_input(
                "concerns（逗号分隔）",
                value=draft_form_data["concerns"],
                key=f"{form_prefix}_concerns",
            )
            edited_current_stage = st.text_input(
                "current_stage",
                value=draft_form_data["current_stage"],
                key=f"{form_prefix}_current_stage",
            )
            if has_load_fields:
                edited_power_load_requirement = st.text_input(
                    "power_load_requirement",
                    value=draft_form_data["power_load_requirement"],
                    key=f"{form_prefix}_power_load_requirement",
                )
                edited_estimated_load_kw = st.text_input(
                    "estimated_load_kw",
                    value=draft_form_data["estimated_load_kw"],
                    key=f"{form_prefix}_estimated_load_kw",
                )
            else:
                edited_power_load_requirement = draft_form_data["power_load_requirement"]
                edited_estimated_load_kw = draft_form_data["estimated_load_kw"]
        submitted = st.form_submit_button("保存修改", type="primary")

    if submitted:
        updated_record = build_opportunity_update(
            record,
            {
                "company_name": edited_company_name,
                "contact_name": edited_contact_name,
                "contact_phone": edited_contact_phone,
                "contact_role": edited_contact_role,
                "industry": edited_industry,
                "business_type_guess": edited_business_type_guess,
                "power_load_requirement": edited_power_load_requirement,
                "estimated_load_kw": edited_estimated_load_kw,
                "budget_hint": edited_budget_hint,
                "core_needs": edited_core_needs,
                "concerns": edited_concerns,
                "current_stage": edited_current_stage,
            },
        )
        save_opportunity_record(records, record, updated_record, record_key)
        st.success("机会记录已保存，并追加 correction log。")
        st.rerun()

    delete_key = f"confirm_delete_opportunity_{safe_key}"
    action_col1, action_col2 = st.columns([1, 2])
    with action_col1:
        if st.button("删除该条记录", key=f"delete_opportunity_trigger_{safe_key}"):
            st.session_state[delete_key] = True
    with action_col2:
        st.caption("Delete persists to SQLite and appends an opportunity correction log.")

    if st.session_state.get(delete_key):
        st.warning("确认删除这条机会记录吗？此操作不可恢复。")
        confirm_col1, confirm_col2 = st.columns(2)
        with confirm_col1:
            if st.button("确认删除", key=f"delete_opportunity_confirm_{safe_key}"):
                remove_opportunity_record(records, record, record_key)
                st.session_state.pop(delete_key, None)
                st.success("机会记录已删除，并追加 correction log。")
                st.rerun()
        with confirm_col2:
            if st.button("取消", key=f"delete_opportunity_cancel_{safe_key}"):
                st.session_state.pop(delete_key, None)
                st.rerun()



def render_opportunity_history_section() -> None:
    """Render opportunity history list and detail/editor view."""
    st.subheader("机会记录历史 / Opportunity History")
    st.caption("查看已写入缓冲层的机会记录历史，支持单条编辑、保存、删除和 correction log 留痕。")

    try:
        records = load_opportunity_records()
    except (FileNotFoundError, ValueError, OSError) as exc:
        st.error(f"机会记录读取失败: {exc}")
        return

    if not records:
        st.info("SQLite opportunity store is empty.")
        return

    recent_records = records[:10]
    list_col, detail_col = st.columns([1, 2])
    with list_col:
        st.markdown("#### 最近机会记录")
        label_to_key: dict[str, str] = {}
        labels: list[str] = []
        for index, record in enumerate(recent_records):
            record_key = get_opportunity_record_key(record, index)
            company_name = str(record.get('company_name', '')).strip() or '未识别公司'
            contact_name = str(record.get('contact_name', '')).strip() or '未识别联系人'
            current_stage = str(record.get('current_stage', '')).strip() or '未识别阶段'
            created_at = str(record.get('created_at', '')).strip() or '无时间'
            display_id = str(record.get('id', '')).strip() or str(record.get('record_id', '')).strip() or f"idx-{index}"
            label = f"{display_id} | {company_name} | {contact_name} | {current_stage} | {created_at}"
            labels.append(label)
            label_to_key[label] = record_key

        selected_label = st.selectbox(
            "选择一条历史机会记录",
            options=labels,
            key='opportunity_history_selected_label',
        )
        with st.expander("展开查看最近记录列表", expanded=False):
            for label in labels:
                st.write(f"- {label}")

    selected_key = label_to_key[selected_label]
    selected_record = next(
        (
            record for index, record in enumerate(recent_records)
            if get_opportunity_record_key(record, index) == selected_key
        ),
        None,
    )
    if selected_record is None:
        st.info("未找到选中的机会记录。")
        return

    with detail_col:
        render_opportunity_record_detail(selected_record)
        render_opportunity_record_editor(records, selected_record, selected_key)



def render_opportunity_data_governance_section() -> None:
    """Render a minimal data governance entry for opportunity records."""
    st.subheader("Opportunity Data Governance / 机会数据治理")
    st.caption("Browse recent opportunity records, inspect review flags, and make small record corrections or deletions. / 用于查看最近机会记录、review 状态，并对单条记录做小范围修正、跟进补录或删除。")

    try:
        records = load_opportunity_records()
    except (FileNotFoundError, ValueError, OSError) as exc:
        st.error(f"Failed to load opportunity records: {exc}")
        return

    if not records:
        st.info("SQLite opportunity store is empty.")
        return

    recent_records = records[:12]
    summary_rows: list[dict] = []
    label_to_key: dict[str, str] = {}
    labels: list[str] = []
    latest_followups: dict[int, dict] = {}
    for index, record in enumerate(recent_records):
        record_key = get_opportunity_record_key(record, index)
        review_reasons = record.get("review_reasons", [])
        if not isinstance(review_reasons, list):
            review_reasons = []
        opportunity_id = int(record.get("id", 0))
        latest_followup = get_latest_followup(opportunity_id) if opportunity_id else {}
        latest_followups[opportunity_id] = latest_followup
        summary_rows.append(
            {
                "id": record.get("id", ""),
                "company_name": str(record.get("company_name", "")).strip() or "Unknown company",
                "business_type_guess": str(record.get("business_type_guess", "")).strip() or "-",
                "current_stage": str(record.get("current_stage", "")).strip() or "-",
                "needs_review": "yes" if bool(record.get("needs_review")) else "no",
                "review_reasons": ", ".join(str(item).strip() for item in review_reasons if str(item).strip()) or "-",
                "follow_up_status": str(latest_followup.get("followup_status", "")).strip() or "-",
                "next_followup_date": str(latest_followup.get("next_followup_date", "")).strip() or "-",
                "updated_at": str(record.get("updated_at", "")).strip() or "-",
            }
        )
        label = (
            f"{record.get('id', '-')} | "
            f"{str(record.get('company_name', '')).strip() or 'Unknown company'} | "
            f"{str(record.get('business_type_guess', '')).strip() or '-'} | "
            f"review={'Y' if bool(record.get('needs_review')) else 'N'}"
        )
        labels.append(label)
        label_to_key[label] = record_key

    st.markdown("#### Recent Opportunity Summary / 最近机会摘要")
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    selected_label = st.selectbox(
        "Select a record to govern / 选择一条记录进入治理",
        options=labels,
        key="opportunity_governance_selected_label",
    )
    selected_key = label_to_key[selected_label]
    selected_record = next(
        (
            record for index, record in enumerate(recent_records)
            if get_opportunity_record_key(record, index) == selected_key
        ),
        None,
    )
    if selected_record is None:
        st.info("Selected governance record was not found.")
        return

    selected_opportunity_id = int(selected_record.get("id", 0))
    latest_followup = latest_followups.get(selected_opportunity_id) or {}

    st.markdown("#### Selected Record / 当前治理对象")
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.write(f"id: {selected_record.get('id', '-')}")
        st.write(f"company_name: {selected_record.get('company_name', '') or 'Unknown'}")
        st.write(f"business_type_guess: {selected_record.get('business_type_guess', '') or '-'}")
        st.write(f"current_stage: {selected_record.get('current_stage', '') or '-'}")
    with info_col2:
        review_reasons = selected_record.get("review_reasons", [])
        if not isinstance(review_reasons, list):
            review_reasons = []
        st.write(f"needs_review: {'yes' if bool(selected_record.get('needs_review')) else 'no'}")
        st.write(f"review_reasons: {', '.join(review_reasons) if review_reasons else '-'}")
        st.write(f"updated_at: {selected_record.get('updated_at', '') or '-'}")

    governance_key = ''.join(char if char.isalnum() else '_' for char in selected_key)
    form_prefix = f"governance_form_{governance_key}"
    core_needs = selected_record.get("core_needs", [])
    if not isinstance(core_needs, list):
        core_needs = []
    estimated_load_kw = selected_record.get("estimated_load_kw")

    with st.form(f"opportunity_governance_form_{governance_key}"):
        st.markdown("#### Lightweight Corrections / 轻量字段修正")
        edit_col1, edit_col2 = st.columns(2)
        with edit_col1:
            edited_company_name = st.text_input(
                "company_name",
                value=str(selected_record.get("company_name", "")),
                key=f"{form_prefix}_company_name",
            )
            edited_business_type_guess = st.text_input(
                "business_type_guess",
                value=str(selected_record.get("business_type_guess", "")),
                key=f"{form_prefix}_business_type_guess",
            )
            edited_core_needs = st.text_input(
                "core_needs (comma separated)",
                value=", ".join(str(item).strip() for item in core_needs if str(item).strip()),
                key=f"{form_prefix}_core_needs",
            )
            edited_current_stage = st.text_input(
                "current_stage",
                value=str(selected_record.get("current_stage", "")),
                key=f"{form_prefix}_current_stage",
            )
        with edit_col2:
            edited_power_load_requirement = st.text_input(
                "power_load_requirement",
                value=str(selected_record.get("power_load_requirement", "")),
                key=f"{form_prefix}_power_load_requirement",
            )
            edited_estimated_load_kw = st.text_input(
                "estimated_load_kw",
                value="" if estimated_load_kw in (None, "") else str(estimated_load_kw),
                key=f"{form_prefix}_estimated_load_kw",
            )
            edited_needs_review = st.checkbox(
                "needs_review",
                value=bool(selected_record.get("needs_review")),
                key=f"{form_prefix}_needs_review",
            )
        submitted = st.form_submit_button("Save Governance Changes / 保存治理修改", type="primary")

    if submitted:
        updated_record = dict(selected_record)
        updated_record["company_name"] = edited_company_name.strip()
        updated_record["business_type_guess"] = edited_business_type_guess.strip()
        updated_record["core_needs"] = _split_csv_text(edited_core_needs)
        updated_record["current_stage"] = edited_current_stage.strip()
        updated_record["power_load_requirement"] = edited_power_load_requirement.strip()
        updated_record["estimated_load_kw"] = _parse_estimated_load_kw(edited_estimated_load_kw)
        updated_record["needs_review"] = bool(edited_needs_review)
        updated_record["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_opportunity_record(records, selected_record, updated_record, selected_key)
        st.success("Governance changes saved to SQLite and appended to the correction log.")
        st.rerun()

    st.markdown("#### Latest Follow-up / 最新跟进")
    followup_info_col1, followup_info_col2 = st.columns(2)
    with followup_info_col1:
        st.write(f"follow_up_status: {str(latest_followup.get('followup_status', '')).strip() or '-'}")
        st.write(f"next_followup_date: {str(latest_followup.get('next_followup_date', '')).strip() or '-'}")
    with followup_info_col2:
        st.write(f"followup_note: {str(latest_followup.get('followup_note', '')).strip() or '-'}")
        st.write(f"next_action: {str(latest_followup.get('next_action', '')).strip() or '-'}")

    with st.form(f"opportunity_followup_form_{governance_key}"):
        st.markdown("#### Update Follow-up / 跟进补录")
        follow_col1, follow_col2 = st.columns(2)
        with follow_col1:
            follow_up_status = st.text_input(
                "follow_up_status",
                value=str(latest_followup.get("followup_status", "")).strip(),
                key=f"{form_prefix}_follow_up_status",
            )
            last_follow_up_note = st.text_area(
                "last_follow_up_note",
                value=str(latest_followup.get("followup_note", "")).strip(),
                height=90,
                key=f"{form_prefix}_last_follow_up_note",
            )
        with follow_col2:
            next_follow_up_action = st.text_area(
                "next_follow_up_action",
                value=str(latest_followup.get("next_action", "")).strip(),
                height=90,
                key=f"{form_prefix}_next_follow_up_action",
            )
            next_follow_up_date = st.text_input(
                "next_follow_up_date",
                value=str(latest_followup.get("next_followup_date", "")).strip(),
                key=f"{form_prefix}_next_follow_up_date",
            )
        followup_submitted = st.form_submit_button("Save Follow-up Update / 保存跟进更新", type="primary")

    if followup_submitted:
        try:
            with get_connection(DB_FILE) as conn:
                init_app_db(conn)
                create_followup(
                    conn,
                    {
                        "opportunity_id": selected_opportunity_id,
                        "user_id": str(selected_record.get("user_id", "")).strip(),
                        "followup_status": str(follow_up_status).strip(),
                        "followup_note": str(last_follow_up_note).strip(),
                        "next_action": str(next_follow_up_action).strip(),
                        "next_followup_date": str(next_follow_up_date).strip(),
                    },
                )
            st.success("Follow-up update saved to SQLite.")
            st.rerun()
        except Exception as exc:
            st.error(f"Failed to save follow-up update: {exc}")

    delete_state_key = f"governance_confirm_delete_{governance_key}"
    st.markdown("#### Cleanup / 清理入口")
    st.caption("Use this only for obvious dirty data or demo records. Deletion cannot be undone. / 仅用于删除明显脏数据或 demo 数据，删除不可恢复。")
    trigger_col, helper_col = st.columns([1, 2])
    with trigger_col:
        if st.button("Delete This Record / 删除这条记录", key=f"governance_delete_trigger_{governance_key}"):
            st.session_state[delete_state_key] = True
    with helper_col:
        st.write("Recommended only for test data, duplicate dirty records, or invalid demo samples.")

    if st.session_state.get(delete_state_key):
        st.warning("Confirm deletion. This removes the SQLite opportunity record and keeps the correction log.")
        confirm_col1, confirm_col2 = st.columns(2)
        with confirm_col1:
            if st.button("Confirm Delete / 确认删除", key=f"governance_delete_confirm_{governance_key}"):
                remove_opportunity_record(records, selected_record, selected_key)
                st.session_state.pop(delete_state_key, None)
                st.success("Governance delete completed and appended to the correction log.")
                st.rerun()
        with confirm_col2:
            if st.button("Cancel / 取消", key=f"governance_delete_cancel_{governance_key}"):
                st.session_state.pop(delete_state_key, None)
                st.rerun()


def render_retrieval_debugger() -> None:
    """Render the original retrieval debugging block."""
    st.subheader("区块 B：检索调试器")
    default_query = (
        "深圳宝安区一个自动化设备客户，最近新增产线，需要低压配电柜配套，"
        "比较担心交付周期，希望先看看类似案例，项目预算大概几十万。"
    )
    query = st.text_area("客户需求描述", value=default_query, height=120)
    top_k = st.radio("Top K", options=[3, 5], horizontal=True)

    if st.button("执行检索", type="primary"):
        if not query.strip():
            st.warning("请输入客户需求描述。")
        else:
            try:
                results = retrieve_similar_projects(query, top_k=top_k)
            except (FileNotFoundError, ValueError, OSError) as exc:
                st.error(f"检索失败: {exc}")
                return

            st.write(f"检索结果数: {len(results)}")
            for item in results:
                with st.expander(
                    f"{item.get('project_id', '')} | {item.get('project_name', '')} | score={item.get('score', 0)}",
                    expanded=True,
                ):
                    st.write(f"建设单位: {item.get('company_name', '') or '-'}")
                    st.write(f"业务类型: {item.get('business_type', '') or '-'}")
                    st.write(
                        f"地区: {item.get('location_city', '') or '-'} {item.get('location_district', '') or ''}"
                    )
                    st.write(f"项目金额: {format_amount(item.get('project_amount', 0))}")
                    st.write(f"得分: {item.get('score', 0)}")
                    st.write("命中原因:")
                    reasons = item.get("matched_reasons", []) or ["无明确命中原因"]
                    for reason in reasons:
                        st.write(f"- {reason}")
                    st.json(item, expanded=False)



def main() -> None:
    """Render the local project case workbench."""
    st.set_page_config(page_title="项目库工作台", layout="wide")
    st.title("项目库浏览 + 检索调试")
    st.caption("本地调试工作台，用于浏览案例库、提示异常值并手工修订。")

    if not DATA_FILE.exists():
        st.warning("未找到 data/project_cases_cleaned.jsonl，请先运行清洗脚本。")
        return

    try:
        cases = load_cases()
    except (FileNotFoundError, ValueError, OSError) as exc:
        st.error(f"案例库读取失败: {exc}")
        return

    if not cases:
        st.info("项目案例库为空，暂无可展示数据。")
        return

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["\u9879\u76ee\u5e93\u6d4f\u89c8", "\u6570\u636e\u6821\u51c6 / Review Queue", "\u673a\u4f1a\u8f93\u5165 / Opportunity Flow", "\u673a\u4f1a\u8bb0\u5f55\u5386\u53f2 / Opportunity History", "Data Governance / \u673a\u4f1a\u6570\u636e\u6cbb\u7406", "\u68c0\u7d22\u8c03\u8bd5"])
    with tab1:
        render_library_browser(cases)
    with tab2:
        render_review_workbench(cases)
    with tab3:
        render_opportunity_flow_section()
    with tab4:
        render_opportunity_history_section()
    with tab5:
        render_opportunity_data_governance_section()
    with tab6:
        render_retrieval_debugger()


if __name__ == "__main__":
    main()





