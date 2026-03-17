import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.project_case_workbench import append_opportunity_correction_log
from pipeline.init_app_db import DB_FILE, get_connection, init_app_db
from pipeline.manage_opportunity_records import create_followup, list_followups, list_opportunities, update_opportunity
from pipeline.parse_opportunity_note import build_review_flags
from pipeline.run_opportunity_flow import run_opportunity_flow, suggest_followup_timing


OPPORTUNITY_RECORD_FILE = ROOT_DIR / "data" / "opportunity_records.jsonl"
DEMO_INPUT_KEY = "visit_assistant_demo_input"
RESULT_KEY = "visit_assistant_last_result"
PENDING_DEMO_INPUT_KEY = "visit_assistant_pending_demo_input"
POST_SAVE_FEEDBACK_KEY = "visit_assistant_post_save_feedback"



def t(value: str) -> str:
    """Decode escaped UI copy only when needed."""
    if "\\u" in value:
        return value.encode("utf-8").decode("unicode_escape")
    return value



def get_demo_samples() -> list[dict]:
    """Return fixed high-quality demo samples."""
    return [
        {
            "title": t("\u81ea\u52a8\u5316\u8bbe\u5907\u5ba2\u6237\u65b0\u589e\u4ea7\u7ebf"),
            "description": t("\u9002\u5408\u770b\u4fe1\u606f\u4e0d\u5b8c\u6574\u65f6\u7cfb\u7edf\u5982\u4f55\u4fdd\u5b88\u8f93\u51fa\u548c\u5efa\u8bae\u540e\u7eed\u8ffd\u95ee\u3002"),
            "input_text": t("\u6df1\u5733\u5b9d\u5b89\u4e00\u4e2a\u81ea\u52a8\u5316\u8bbe\u5907\u5ba2\u6237\uff0c\u8054\u7cfb\u4eba\u738b\u5de5\uff0c\u7535\u8bdd13800138000\uff0c\u6700\u8fd1\u65b0\u589e\u4ea7\u7ebf\uff0c\u9700\u8981\u4f4e\u538b\u914d\u7535\u67dc\uff0c\u62c5\u5fc3\u4ea4\u4ed8\u5468\u671f\uff0c\u5e0c\u671b\u5148\u770b\u770b\u7c7b\u4f3c\u6848\u4f8b\u3002"),
            "guide": t("\u5148\u770b\u7cfb\u7edf\u8bc6\u522b\u51fa\u7684\u9700\u6c42\u6458\u8981\uff0c\u518d\u770b\u63a8\u8350\u8bb2\u70b9\u548c\u8ddf\u8fdb\u5efa\u8bae\uff0c\u6700\u540e\u7528\u76f8\u4f3c\u6848\u4f8b\u652f\u6491\u65b9\u6848\u53ef\u4fe1\u5ea6\u3002"),
        },
        {
            "title": t("\u5de5\u5382\u6269\u5bb9\u4e0e\u8d1f\u8f7d\u9700\u6c42"),
            "description": t("\u9002\u5408\u770b\u8d1f\u8f7d\u5b57\u6bb5\u89e3\u6790\u3001\u6269\u5bb9\u573a\u666f\u6848\u4f8b\u548c\u62dc\u8bbf\u5efa\u8bae\u91cc\u7684\u5bb9\u91cf\u8ffd\u95ee\u3002"),
            "input_text": t("\u67d0\u5de5\u5382\u9884\u8ba1\u603b\u8d1f\u83771.2MW\uff0c\u8003\u8651\u6269\u5bb9\uff0c\u9700\u8981\u8bc4\u4f30\u914d\u7535\u6539\u9020\u65b9\u6848\uff0c\u8054\u7cfb\u4eba\u674e\u5de5\uff0c\u7535\u8bdd13900139000\u3002"),
            "guide": t("\u91cd\u70b9\u770b\u8d1f\u8f7d\u8bc6\u522b\u3001\u62dc\u8bbf\u5efa\u8bae\u91cc\u7684\u8ffd\u95ee\u9879\uff0c\u4ee5\u53ca\u76f8\u4f3c\u6269\u5bb9\u6848\u4f8b\u7684\u5339\u914d\u539f\u56e0\u3002"),
        },
        {
            "title": t("\u8001\u65e7\u7cfb\u7edf\u6539\u9020\u4e14\u4fe1\u606f\u4e0d\u5b8c\u6574"),
            "description": t("\u9002\u5408\u770b\u4fe1\u606f\u4e0d\u5b8c\u6574\u65f6\u7cfb\u7edf\u5982\u4f55\u4fdd\u5b88\u8f93\u51fa\u548c\u5efa\u8bae\u540e\u7eed\u8ffd\u95ee\u3002"),
            "input_text": t("\u5e7f\u5dde\u67d0\u8001\u65e7\u5de5\u4e1a\u56ed\u914d\u7535\u7cfb\u7edf\u60f3\u6539\u9020\uff0c\u5ba2\u6237\u8fd8\u6ca1\u786e\u5b9a\u5177\u4f53\u5bb9\u91cf\uff0c\u5148\u4e86\u89e3\u7c7b\u4f3c\u9879\u76ee\uff0c\u62c5\u5fc3\u65bd\u5de5\u5f71\u54cd\u751f\u4ea7\u3002"),
            "guide": t("\u91cd\u70b9\u770b\u7cfb\u7edf\u5982\u4f55\u63d0\u793a\u4fe1\u606f\u5f85\u8865\u5168\uff0c\u4ee5\u53ca\u5b83\u5efa\u8bae\u4e0b\u4e00\u6b65\u5148\u95ee\u6e05\u4ec0\u4e48\u3002"),
        },
    ]



def load_recent_opportunity_records(limit: int = 5) -> list[dict]:
    """Load recent opportunity records from SQLite, newest first."""
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        records = list_opportunities(conn)
    return records[:limit]



def _format_followup_datetime(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return t("\u5f85\u786e\u8ba4")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return dt.strftime("%Y-%m-%d %H:%M")



def _derive_current_blocker(opportunity: dict) -> str:
    concerns = opportunity.get("concerns", [])
    if isinstance(concerns, list):
        for item in concerns:
            cleaned = str(item).strip()
            if cleaned:
                return cleaned
    review_reasons = opportunity.get("review_reasons", [])
    if isinstance(review_reasons, list):
        for item in review_reasons:
            cleaned = humanize_review_reason(str(item))
            if cleaned:
                return cleaned
    if bool(opportunity.get("needs_review")):
        return t("\u5173\u952e\u4fe1\u606f\u4ecd\u5f85\u8865\u5145")
    return t("\u6682\u65e0\u660e\u663e\u963b\u585e")



def _get_latest_followup_map(opportunity_ids: list[int]) -> dict[int, dict]:
    followup_map: dict[int, dict] = {}
    if not opportunity_ids:
        return followup_map
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        for opportunity_id in opportunity_ids:
            followups = list_followups(conn, opportunity_id)
            if followups:
                followup_map[opportunity_id] = followups[0]
    return followup_map



def _build_recent_followup_items(limit: int = 8) -> list[dict]:
    opportunities = load_recent_opportunity_records(limit=limit)
    opportunity_ids = [int(item.get("id")) for item in opportunities if item.get("id") not in (None, "")]
    followup_map = _get_latest_followup_map(opportunity_ids)
    items: list[dict] = []
    for opportunity in opportunities:
        opportunity_id = opportunity.get("id")
        followup = followup_map.get(int(opportunity_id), {}) if opportunity_id not in (None, "") else {}
        suggested_time = str(followup.get("next_followup_date", "")).strip()
        if not suggested_time:
            suggestion, _ = suggest_followup_timing(opportunity)
            suggested_time = suggestion
        items.append(
            {
                "opportunity": opportunity,
                "followup": followup,
                "created_at": str(opportunity.get("created_at", "")).strip(),
                "company_name": str(opportunity.get("company_name", "")).strip() or t("\u5ba2\u6237\u540d\u672a\u5f55\u5165"),
                "current_stage": str(opportunity.get("current_stage", "")).strip() or "new",
                "current_blocker": _derive_current_blocker(opportunity),
                "recommended_follow_up_at": suggested_time,
            }
        )
    return items



def clear_demo_records() -> int:
    """Remove only demo-mode records from opportunity history."""
    if not OPPORTUNITY_RECORD_FILE.exists():
        return 0

    kept_records: list[dict] = []
    removed_count = 0
    with OPPORTUNITY_RECORD_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            content = line.strip()
            if not content:
                continue
            record = json.loads(content)
            if not isinstance(record, dict):
                continue
            if str(record.get("source_mode", "")).strip() == "demo":
                removed_count += 1
                continue
            kept_records.append(record)

    with OPPORTUNITY_RECORD_FILE.open("w", encoding="utf-8") as file:
        for record in kept_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return removed_count



def render_header() -> None:
    st.title(t("\u5ba2\u6237\u62dc\u8bbf\u52a9\u624b Demo"))
    st.caption(t("\u628a\u4e00\u6bb5\u5ba2\u6237\u6216\u9879\u76ee\u63cf\u8ff0\u5feb\u901f\u8f6c\u6210\u7ed3\u6784\u5316\u673a\u4f1a\u3001\u76f8\u4f3c\u6848\u4f8b\u548c\u62dc\u8bbf\u5efa\u8bae\uff0c\u4f5c\u4e3a\u524d\u53f0\u8bd5\u7528\u5165\u53e3\u3002"))
    st.write(t("\u8fd9\u4e2a demo \u9762\u5411\u9500\u552e\u6216\u552e\u524d\u7684\u9996\u8f6e\u6c9f\u901a\u573a\u666f\uff0c\u5e2e\u52a9\u7528\u6237\u5feb\u901f\u770b\u6e05\u5ba2\u6237\u9700\u6c42\u3001\u53c2\u8003\u7c7b\u4f3c\u9879\u76ee\uff0c\u5e76\u5f62\u6210\u4e0b\u4e00\u6b65\u62dc\u8bbf\u91cd\u70b9\u3002"))



def render_demo_guide() -> None:
    st.subheader(t("A. Demo Guide / \u6f14\u793a\u5bfc\u89c8"))
    st.write(t("\u63a8\u8350\u6f14\u793a\u8def\u5f84\uff1a1\uff09\u5148\u52a0\u8f7d\u4e00\u4e2a\u6837\u4f8b\uff1b2\uff09\u8fd0\u884c\u4e3b\u94fe\uff1b3\uff09\u5148\u770b\u7cfb\u7edf\u7ed3\u8bba\u4e0e\u63a8\u8350\u52a8\u4f5c\uff1b4\uff09\u518d\u5c55\u5f00\u76f8\u4f3c\u6848\u4f8b\u548c\u7ed3\u6784\u5316\u8be6\u60c5\u3002"))

    for index, sample in enumerate(get_demo_samples()):
        with st.container(border=True):
            st.markdown(f"**{t('\\u6837\\u4f8b')} {index + 1}\uff1a{sample['title']}**")
            st.write(sample["description"])
            st.caption(sample["guide"])
            st.code(sample["input_text"], language="text")
            if st.button(t("\u52a0\u8f7d\u6837\u4f8b"), key=f"load_demo_sample_{index}"):
                st.session_state[DEMO_INPUT_KEY] = sample["input_text"]
                st.rerun()



def render_input_section() -> None:
    st.subheader(t("B. Opportunity Input / \u8f93\u5165\u533a"))
    st.text_area(
        t("\u5ba2\u6237 / \u9879\u76ee\u81ea\u7136\u8bed\u8a00\u63cf\u8ff0"),
        key=DEMO_INPUT_KEY,
        height=160,
        placeholder=t("\u4f8b\u5982\uff1a\u6df1\u5733\u67d0\u81ea\u52a8\u5316\u8bbe\u5907\u5ba2\u6237\u6700\u8fd1\u65b0\u589e\u4ea7\u7ebf\uff0c\u9700\u8981\u4f4e\u538b\u914d\u7535\u67dc\uff0c\u62c5\u5fc3\u4ea4\u4ed8\u5468\u671f\u2026\u2026"),
    )

    if st.button(t("\u8fd0\u884c\u4e3b\u94fe"), type="primary", key="visit_assistant_run_flow"):
        raw_input = str(st.session_state.get(DEMO_INPUT_KEY, "")).strip()
        if not raw_input:
            st.warning(t("\u8bf7\u8f93\u5165\u5ba2\u6237\u6216\u9879\u76ee\u63cf\u8ff0\uff0c\u6216\u5148\u52a0\u8f7d\u4e00\u4e2a\u6f14\u793a\u6837\u4f8b\u3002"))
            return

        try:
            with st.spinner(t("\u7cfb\u7edf\u5df2\u63a5\u6536\u8bf7\u6c42\uff0c\u6b63\u5728\u89e3\u6790\u673a\u4f1a\u3001\u68c0\u7d22\u76f8\u4f3c\u9879\u76ee\u5e76\u751f\u6210\u62dc\u8bbf\u5efa\u8bae\uff0c\u8bf7\u52ff\u91cd\u590d\u70b9\u51fb\u3002")):
                st.session_state[RESULT_KEY] = run_opportunity_flow(raw_input, top_k=3, source_mode="demo")
        except (FileNotFoundError, ValueError, OSError) as exc:
            st.error(f"{t('\\u4e3b\\u94fe\\u8fd0\\u884c\\u5931\\u8d25')} : {exc}")
        except Exception as exc:
            st.error(f"{t('\\u4e3b\\u94fe\\u8fd0\\u884c\\u5f02\\u5e38')} : {exc}")



def humanize_review_reason(reason: str) -> str:
    mapping = {
        "company_name missing": t("\u5ba2\u6237\u540d\u79f0\u5f85\u8865\u5145"),
        "contact_phone missing": t("\u8054\u7cfb\u7535\u8bdd\u5f85\u8865\u5145"),
        "project intent weak": t("\u9879\u76ee\u76ee\u6807\u4ecd\u4e0d\u591f\u6e05\u6670"),
    }
    return mapping.get(str(reason).strip(), str(reason).strip())



def humanize_match_reason(reason: str) -> str:
    text = str(reason).strip()
    if not text:
        return ""
    if "location_city matched in request text" in text:
        city = text.split(":")[-1].split("(")[0].strip()
        return t("\u5730\u533a\u573a\u666f\u8f83\u63a5\u8fd1\uff1a") + city
    if "keyword matched:" in text:
        keyword = text.split(":", 1)[-1].split("(")[0].strip()
        return t("\u8bc6\u522b\u5230\u7684\u53ef\u80fd\u4e1a\u52a1\u7c7b\u578b\u6216\u9700\u6c42\u65b9\u5411\uff1a") + keyword
    if "project_name core term matched" in text:
        return t("\u9879\u76ee\u540d\u79f0\u548c\u5f53\u524d\u7ebf\u7d22\u7684\u4e3b\u9898\u8f83\u63a5\u8fd1")
    return text



def humanize_talking_point(point: str) -> str:
    text = str(point).strip()
    if not text:
        return ""
    if text.startswith(t("\u5efa\u8bae\u5f3a\u8c03\u5339\u914d\u70b9\uff1a")):
        raw_reasons = text.split(t("\u5efa\u8bae\u5f3a\u8c03\u5339\u914d\u70b9\uff1a"), 1)[-1]
        parts = [humanize_match_reason(item) for item in raw_reasons.split(t("\uff1b")) if str(item).strip()]
        parts = [item for item in parts if item]
        if parts:
            return t("\u53ef\u4ee5\u91cd\u70b9\u5411\u5ba2\u6237\u8bf4\u660e\uff1a") + t("\uff1b").join(parts)
    return text


def _format_joined_list(values: object, empty_text: str | None = None) -> str:
    if empty_text is None:
        empty_text = t("\u5f85\u8865\u5145")
    if not isinstance(values, list):
        return empty_text
    cleaned = [str(item).strip() for item in values if str(item).strip()]
    return t("\u3001").join(cleaned) if cleaned else empty_text





def _display_field(value: object, missing_text: str) -> str:
    text = str(value or "").strip()
    return text if text else missing_text


def build_post_save_feedback(record: dict, saved_to_file: bool, correction_logged: bool) -> dict:
    save_status_lines = [t("\u5f53\u524d\u8bb0\u5f55\u5df2\u66f4\u65b0")]
    save_status_lines.append(
        t("\u5f53\u524d\u4fee\u6539\u5df2\u4fdd\u5b58\u5230\u6570\u636e\u6587\u4ef6") if saved_to_file else t("\u5f53\u524d\u4fee\u6539\u5c1a\u672a\u5199\u5165\u6570\u636e\u6587\u4ef6")
    )
    save_status_lines.append(
        t("correction log \u5df2\u8bb0\u5f55") if correction_logged else t("correction log \u5c1a\u672a\u8bb0\u5f55")
    )

    next_actions: list[str] = []
    if bool(record.get("needs_review")):
        next_actions.append(t("\u4f18\u5148\u7ee7\u7eed\u8865\u5168\u5173\u952e\u5b57\u6bb5\uff0c\u518d\u63a8\u8fdb\u540e\u7eed\u6c9f\u901a\u3002"))
        next_actions.append(t("\u5982\u679c\u4ecd\u7f3a\u5c11\u516c\u53f8\u540d\u79f0\u6216\u8054\u7cfb\u7535\u8bdd\uff0c\u5efa\u8bae\u5148\u786e\u8ba4\u518d\u8ddf\u8fdb\u3002"))
    else:
        next_actions.append(t("\u53ef\u4ee5\u91cd\u65b0\u8fd0\u884c\u4e3b\u94fe\uff0c\u67e5\u770b\u66f4\u65b0\u540e\u7684\u62dc\u8bbf\u5efa\u8bae\u548c\u53c2\u8003\u6848\u4f8b\u3002"))
        next_actions.append(t("\u53ef\u4ee5\u5bf9\u7167 Opportunity History \u6216\u5f53\u524d\u8bb0\u5f55 JSON\uff0c\u786e\u8ba4\u5b57\u6bb5\u5df2\u6309\u9884\u671f\u66f4\u65b0\u3002"))

    if str(record.get("current_stage", "")).strip() in {"new", "quoted", "proposal"}:
        next_actions.append(t("\u6839\u636e\u5f53\u524d\u9636\u6bb5\uff0c\u51c6\u5907\u4e0b\u4e00\u8f6e\u6c9f\u901a\u8981\u70b9\u6216\u62dc\u8bbf\u6750\u6599\u3002"))
    else:
        next_actions.append(t("\u5982\u8bb0\u5f55\u5df2\u76f8\u5bf9\u5b8c\u6574\uff0c\u53ef\u6309\u5efa\u8bae\u65f6\u95f4\u7ee7\u7eed\u63a8\u8fdb\u3002"))

    if not str(record.get("contact_phone", "")).strip() and t("\u4f18\u5148\u7ee7\u7eed\u8865\u5168\u5173\u952e\u5b57\u6bb5\uff0c\u518d\u63a8\u8fdb\u540e\u7eed\u6c9f\u901a\u3002") not in next_actions:
        next_actions.append(t("\u4f18\u5148\u8865\u5145\u8054\u7cfb\u7535\u8bdd\uff0c\u4ee5\u4fbf\u540e\u7eed\u8ddf\u8fdb\u548c\u56de\u8bbf\u3002"))

    deduped_actions: list[str] = []
    for action in next_actions:
        cleaned = str(action).strip()
        if cleaned and cleaned not in deduped_actions:
            deduped_actions.append(cleaned)

    followup_time_suggestion = t("\u8865\u5168\u4fe1\u606f\u540e\u518d\u8ddf\u8fdb")
    followup_time_reason = t("\u5f53\u524d\u8bb0\u5f55\u4ecd\u6709\u5173\u952e\u5b57\u6bb5\u9700\u8981\u8865\u5145\uff0c\u5efa\u8bae\u5148\u5b8c\u6210\u6821\u51c6\u518d\u63a8\u8fdb\u3002")
    if not bool(record.get("needs_review")):
        concerns = record.get("concerns", [])
        if not isinstance(concerns, list):
            concerns = []
        if any(item in concerns for item in [t("\u4ea4\u4ed8\u5468\u671f"), t("\u5de5\u671f"), t("\u5b89\u88c5\u914d\u5408")]):
            followup_time_suggestion = t("3 \u5929\u5185")
            followup_time_reason = t("\u5ba2\u6237\u5bf9\u4ea4\u4ed8\u8282\u594f\u6216\u73b0\u573a\u914d\u5408\u8f83\u654f\u611f\uff0c\u4fdd\u5b58\u540e\u9002\u5408\u5c3d\u5feb\u8fdb\u4e00\u6b65\u8ddf\u8fdb\u3002")
        elif str(record.get("company_name", "")).strip() and str(record.get("contact_phone", "")).strip() and record.get("core_needs", []):
            followup_time_suggestion = t("1 \u5468\u5185")
            followup_time_reason = t("\u5173\u952e\u5b57\u6bb5\u5df2\u76f8\u5bf9\u5b8c\u6574\uff0c\u5efa\u8bae\u5728\u4e00\u5468\u5185\u91cd\u65b0\u67e5\u770b\u5efa\u8bae\u5e76\u63a8\u8fdb\u540e\u7eed\u6c9f\u901a\u3002")

    return {
        "save_status_lines": save_status_lines,
        "next_actions": deduped_actions[:4],
        "followup_time_suggestion": followup_time_suggestion,
        "followup_time_reason": followup_time_reason,
    }


def render_post_save_feedback(feedback: dict) -> None:
    if not isinstance(feedback, dict):
        return

    st.markdown(f"#### {t('\u4fdd\u5b58\u540e\u53cd\u9988\u533a')}")
    status_col, action_col, time_col = st.columns(3)

    with status_col:
        st.markdown(f"**{t('\u4fdd\u5b58\u7ed3\u679c\u53cd\u9988')}**")
        for line in feedback.get("save_status_lines", []):
            st.write(f"- {line}")

    with action_col:
        st.markdown(f"**{t('\u4e0b\u4e00\u6b65\u5efa\u8bae\u52a8\u4f5c')}**")
        for action in feedback.get("next_actions", []):
            st.write(f"- {action}")

    with time_col:
        st.markdown(f"**{t('\u5efa\u8bae\u8ddf\u8fdb\u65f6\u95f4')}**")
        st.write(str(feedback.get("followup_time_suggestion", "")).strip() or t("\u5f85\u5224\u65ad"))
        st.caption(str(feedback.get("followup_time_reason", "")).strip() or t("\u6682\u65e0"))
def render_result_summary(opportunity: dict, result: dict) -> None:
    load_text = str(opportunity.get("power_load_requirement", "")).strip()
    if not load_text:
        estimated_load_kw = opportunity.get("estimated_load_kw")
        if estimated_load_kw not in (None, ""):
            load_text = f"{t('\\u7ea6')} {estimated_load_kw} kW"
    if not load_text:
        load_text = str(opportunity.get("budget_hint", "")).strip() or t("\u5f85\u8865\u5145")

    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    with summary_col1:
        st.metric(t("\u5ba2\u6237\u540d\u79f0"), str(opportunity.get("company_name", "")).strip() or t("\u5f85\u8865\u5145"))
    with summary_col2:
        st.metric(t("\u5f53\u524d\u9636\u6bb5"), str(opportunity.get("current_stage", "")).strip() or "new")
    with summary_col3:
        st.metric(t("\u89c4\u6a21\u7ebf\u7d22"), load_text)
    with summary_col4:
        st.metric(t("\u5efa\u8bae\u8ddf\u8fdb\u65f6\u95f4"), str(result.get("followup_time_suggestion", "")).strip() or t("\u5f85\u5224\u65ad"))



def render_opportunity_brief(opportunity: dict, result: dict) -> None:
    st.markdown(f"#### {t('\u7cfb\u7edf\u8bc6\u522b\u7ed3\u8bba')}")
    left_col, right_col = st.columns(2)
    contact_name = _display_field(opportunity.get("contact_name", ""), t("\u672a\u8bc6\u522b\u5230\u8054\u7cfb\u4eba"))
    contact_phone = _display_field(opportunity.get("contact_phone", ""), t("\u672a\u63d0\u4f9b\u8054\u7cfb\u7535\u8bdd"))
    rule_industry = str(opportunity.get("industry", "")).strip()
    rule_business_type = str(opportunity.get("business_type_guess", "")).strip()
    rule_load_requirement = str(opportunity.get("power_load_requirement", "")).strip()
    load_requirement = _display_field(rule_load_requirement, t("\u5c1a\u672a\u63d0\u4f9b\u660e\u786e\u8d1f\u8f7d\u4fe1\u606f"))
    llm_insights = result.get("llm_assisted_insights", {})
    if not isinstance(llm_insights, dict):
        llm_insights = {}
    llm_success = bool(llm_insights.get("success"))
    llm_business_type = str(llm_insights.get("business_type", "")).strip() if llm_success else ""
    llm_keywords = llm_insights.get("keywords", []) if llm_success else []
    if not isinstance(llm_keywords, list):
        llm_keywords = []
    llm_keywords = [str(item).strip() for item in llm_keywords if str(item).strip()]
    llm_location_parts = [
        str(llm_insights.get("location_city", "")).strip() if llm_success else "",
        str(llm_insights.get("location_district", "")).strip() if llm_success else "",
    ]
    llm_location = " ".join(part for part in llm_location_parts if part).strip()
    business_type_display = llm_business_type or _display_field(rule_business_type, t("\u5f85\u7cfb\u7edf\u8fdb\u4e00\u6b65\u5224\u65ad"))
    keyword_display = t("\u3001").join(llm_keywords) if llm_keywords else _format_joined_list(opportunity.get("core_needs", []), t("\u5f85\u8865\u5145"))
    scenario_display = llm_location or _display_field(opportunity.get("location_city", ""), t("\u5f85\u7cfb\u7edf\u8fdb\u4e00\u6b65\u5224\u65ad"))
    with left_col:
        st.write(f"{t('\u5ba2\u6237\u8054\u7cfb\u4eba')}\uff1a{contact_name}")
        st.write(f"{t('\u8054\u7cfb\u7535\u8bdd')}\uff1a{contact_phone}")
        st.write(f"{t('\u884c\u4e1a\u5224\u65ad')}\uff1a{_display_field(rule_industry, t('\u5f85\u7cfb\u7edf\u8fdb\u4e00\u6b65\u5224\u65ad'))}")
        st.write(f"{t('\u4e1a\u52a1\u65b9\u5411')}\uff1a{business_type_display}")
        if llm_success and rule_business_type and rule_business_type != llm_business_type:
            st.caption(f"{t('\u89c4\u5219\u8bc6\u522b')}\uff1a{rule_business_type}")
    with right_col:
        st.write(f"{t('\u6838\u5fc3\u9700\u6c42 / \u9700\u6c42\u65b9\u5411')}\uff1a{keyword_display}")
        st.write(f"{t('\u53ef\u80fd\u573a\u666f\u533a\u57df')}\uff1a{scenario_display}")
        st.write(f"{t('\u8d1f\u8f7d\u9700\u6c42')}\uff1a{load_requirement}")
        decision = t("\u4fe1\u606f\u4ecd\u9700\u8865\u5145") if bool(opportunity.get("needs_review")) else t("\u4fe1\u606f\u8f83\u5b8c\u6574\uff0c\u53ef\u7ee7\u7eed\u63a8\u8fdb")
        st.write(f"{t('\u7cfb\u7edf\u5224\u65ad')}\uff1a{decision}")
        if llm_success and opportunity.get("core_needs", []):
            st.caption(f"{t('\u89c4\u5219\u63d0\u53d6')}\uff1a{_format_joined_list(opportunity.get('core_needs', []))}")

    review_reasons = opportunity.get("review_reasons", [])
    if isinstance(review_reasons, list) and review_reasons:
        st.caption(t("\u5f85\u8865\u5145\u4fe1\u606f\uff1a") + t("\uff1b").join(humanize_review_reason(str(item)) for item in review_reasons if str(item).strip()))
        if not str(opportunity.get("contact_name", "")).strip():
            st.warning(t("\u672c\u6b21\u63cf\u8ff0\u4e2d\u6ca1\u6709\u53ef\u9760\u7684\u8054\u7cfb\u4eba\u4fe1\u606f\uff0c\u9875\u9762\u5df2\u6309\u201c\u672a\u8bc6\u522b\u5230\u8054\u7cfb\u4eba\u201d\u5c55\u793a\uff0c\u907f\u514d\u8bef\u5bfc\u3002"))

    if llm_success:
        st.caption(t("\u5f53\u524d\u4ee5\u672c\u5730 LLM \u8bc6\u522b\u7ed3\u679c\u4f5c\u4e3a\u4e3b\u5c55\u793a\uff0c\u89c4\u5219\u7ed3\u679c\u4ee5\u5c0f\u5b57\u4f5c\u4e3a\u65c1\u6ce8\u8865\u5145\u3002"))

    st.info(f"{t('\u5efa\u8bae\u8ddf\u8fdb\u539f\u56e0')}\uff1a{str(result.get('followup_time_reason', '')).strip() or t('\u6682\u65e0')}")


def render_visit_recommendation(recommendation: dict, talking_points: list[str]) -> None:
    st.markdown(f"#### {t('\\u63a8\\u8350\\u52a8\\u4f5c')}")
    if not isinstance(recommendation, dict):
        recommendation = {}

    if recommendation.get("error"):
        st.warning(str(recommendation.get("error")))

    ask_col, focus_col = st.columns(2)
    with ask_col:
        st.markdown(f"**{t('\\u5efa\\u8bae\\u8ffd\\u95ee')}**")
        questions = recommendation.get("questions_to_ask", [])
        if isinstance(questions, list) and questions:
            for item in questions:
                st.write(f"- {item}")
        else:
            st.write(f"- {t('\\u5148\\u786e\\u8ba4\\u9879\\u76ee\\u8303\\u56f4\\u3001\\u65f6\\u95f4\\u8981\\u6c42\\u548c\\u5173\\u952e\\u51b3\\u7b56\\u4eba\\u3002')}")

        st.markdown(f"**{t('\\u63a8\\u8350\\u8bb2\\u70b9')}**")
        if isinstance(talking_points, list) and talking_points:
            for item in talking_points:
                st.write(f"- {humanize_talking_point(item)}")
        else:
            st.write(f"- {t('\\u5f53\\u524d\\u6ca1\\u6709\\u751f\\u6210\\u660e\\u786e\\u8bb2\\u70b9\\uff0c\\u5efa\\u8bae\\u56f4\\u7ed5\\u9700\\u6c42\\u6f84\\u6e05\\u5c55\\u5f00\\u3002')}")

    with focus_col:
        st.markdown(f"**{t('\\u5efa\\u8bae\\u805a\\u7126\\u70b9')}**")
        focus_points = recommendation.get("suggested_focus_points", [])
        if isinstance(focus_points, list) and focus_points:
            for item in focus_points:
                st.write(f"- {item}")
        else:
            st.write(f"- {t('\\u4f18\\u5148\\u8bb2\\u6e05\\u65b9\\u6848\\u8fb9\\u754c\\u3001\\u4ea4\\u4ed8\\u8282\\u594f\\u548c\\u76f8\\u4f3c\\u9879\\u76ee\\u7ecf\\u9a8c\\u3002')}")

        st.markdown(f"**{t('\\u98ce\\u9669\\u63d0\\u793a')}**")
        risk_notes = recommendation.get("risk_notes", [])
        if isinstance(risk_notes, list) and risk_notes:
            for item in risk_notes:
                st.write(f"- {item}")
        else:
            st.write(f"- {t('\\u5f53\\u524d\\u6ca1\\u6709\\u8bc6\\u522b\\u5230\\u7a81\\u51fa\\u7684\\u98ce\\u9669\\u63d0\\u793a\\u3002')}")

    next_actions = recommendation.get("next_actions", [])
    if isinstance(next_actions, list) and next_actions:
        st.markdown(f"**{t('\\u5efa\\u8bae\\u4e0b\\u4e00\\u6b65')}**")
        for item in next_actions:
            st.write(f"- {item}")



def render_top_k_cases(cases: list[dict]) -> None:
    st.markdown(f"#### {t('\u7cfb\u7edf\u5efa\u8bae\u53c2\u8003\u7684\u6848\u4f8b')}")
    if not cases:
        st.info(t("\u5f53\u524d\u6ca1\u6709\u627e\u5230\u53ef\u76f4\u63a5\u53c2\u8003\u7684\u7c7b\u4f3c\u9879\u76ee\u3002"))
        return

    st.write(t("\u4ee5\u4e0b\u6848\u4f8b\u53ef\u4ee5\u4f5c\u4e3a\u672c\u6b21\u6c9f\u901a\u7684\u53c2\u8003\u7d20\u6750\uff0c\u53ef\u4ee5\u5148\u5207\u6362\u6848\u4f8b\u5361\u7247\uff0c\u518d\u67e5\u770b\u5f53\u524d\u8fd9\u4e00\u6761\u7684\u5339\u914d\u7406\u7531\u548c\u8be6\u60c5\u3002"))

    top_cases = cases[:3]
    labels: list[str] = []
    label_to_case: dict[str, dict] = {}
    for index, item in enumerate(top_cases, start=1):
        project_name = str(item.get("project_name", "")).strip() or t("\u672a\u547d\u540d\u6848\u4f8b")
        label = f"{t('\u6848\u4f8b')} {index}"
        labels.append(label)
        label_to_case[label] = item

    selected_label = st.radio(
        t("\u5207\u6362\u53c2\u8003\u6848\u4f8b"),
        options=labels,
        horizontal=True,
        label_visibility="collapsed",
        key="visit_assistant_case_switch",
    )
    selected_case = label_to_case[selected_label]

    project_name = str(selected_case.get("project_name", "")).strip() or t("\u672a\u547d\u540d\u6848\u4f8b")
    business_type = str(selected_case.get("business_type", "")).strip() or "-"
    location_text = f"{selected_case.get('location_city', '') or '-'} {selected_case.get('location_district', '') or ''}".strip()
    reasons = selected_case.get("matched_reasons", [])
    summary = t("\u8fd9\u4e2a\u6848\u4f8b\u53ef\u4ee5\u5e2e\u4f60\u8865\u5145\u4ea4\u4ed8\u7ecf\u9a8c\u548c\u65b9\u6848\u6c9f\u901a\u601d\u8def\u3002")
    if isinstance(reasons, list) and reasons:
        summary = t("\u53c2\u8003\u7406\u7531\uff1a") + t("\uff1b").join(humanize_match_reason(str(reason)) for reason in reasons[:2])

    with st.container(border=True):
        st.markdown(f"**{selected_label}\uff1a{project_name}**")
        st.write(summary)
        meta_col1, meta_col2 = st.columns(2)
        with meta_col1:
            st.write(f"{t('\u4e1a\u52a1\u7c7b\u578b')}\uff1a{business_type}")
        with meta_col2:
            st.write(f"{t('\u9879\u76ee\u5730\u533a')}\uff1a{location_text or '-'}")
        with st.expander(t("\u5c55\u5f00\u67e5\u770b\u8fd9\u4e2a\u6848\u4f8b\u7684\u5b8c\u6574\u4fe1\u606f"), expanded=False):
            st.json(selected_case, expanded=False)


def render_natural_advice(opportunity: dict, result: dict) -> None:
    """Render a user-facing natural language summary."""
    company_name = str(opportunity.get("company_name", "")).strip() or t("这个客户")
    business_type = str(opportunity.get("business_type_guess", "")).strip() or t("配电相关机会")
    core_needs = _format_joined_list(opportunity.get("core_needs", []), t("需求待进一步确认"))
    concerns = _format_joined_list(opportunity.get("concerns", []), t("当前顾虑待进一步确认"))
    load_text = str(opportunity.get("power_load_requirement", "")).strip()
    if not load_text:
        estimated_load_kw = opportunity.get("estimated_load_kw")
        if estimated_load_kw not in (None, ""):
            load_text = f"{t('\u7ea6')} {estimated_load_kw} kW"
    if not load_text:
        load_text = t("负载规模待确认")

    suggestion_text = str(result.get("followup_time_suggestion", "")).strip() or t("建议尽快跟进")
    reason_text = str(result.get("followup_time_reason", "")).strip() or t("当前需要进一步确认项目边界")

    summary = (
        f"{t('\u4ece\u5f53\u524d\u63cf\u8ff0\u770b\uff0c')}{company_name}{t('\u66f4\u50cf\u662f\u4e00\u4e2a')}{business_type}{t('\u7ebf\u7d22\u3002')}"
        f"{t('\u73b0\u9636\u6bb5\u7cfb\u7edf\u8bc6\u522b\u5230\u7684\u6838\u5fc3\u9700\u6c42\u662f')}{core_needs}{t('\uff0c\u5ba2\u6237\u6700\u5728\u610f\u7684\u662f')}{concerns}{t('\uff0c')}"
        f"{t('\u5f53\u524d\u89c4\u6a21\u7ebf\u7d22\u4e3a')}{load_text}{t('\u3002\u5efa\u8bae\u6309\u201c')}{suggestion_text}{t('\u201d\u7684\u8282\u594f\u63a8\u8fdb\uff0c\u539f\u56e0\u662f\uff1a')}{reason_text}"
    )
    st.markdown(t("#### 系统建议摘要"))
    st.write(summary)



def render_result_section() -> None:
    st.subheader(t("C. Result / \u7ed3\u679c\u533a"))
    result = st.session_state.get(RESULT_KEY)
    if not isinstance(result, dict):
        st.info(t("\u8fd0\u884c\u4e3b\u94fe\u540e\uff0c\u8fd9\u91cc\u4f1a\u5148\u5c55\u793a\u7cfb\u7edf\u7ed3\u8bba\u4e0e\u5efa\u8bae\u52a8\u4f5c\uff0c\u518d\u5c55\u793a\u76f8\u4f3c\u6848\u4f8b\u548c\u7ed3\u6784\u5316\u8be6\u60c5\u3002"))
        return

    opportunity = result.get("opportunity", {})
    if not isinstance(opportunity, dict):
        opportunity = {}

    render_result_summary(opportunity, result)
    render_natural_advice(opportunity, result)
    render_opportunity_brief(opportunity, result)
    render_visit_recommendation(result.get("visit_recommendation", {}), result.get("recommended_talking_points", []))
    render_top_k_cases(result.get("top_k_cases", []))

    with st.expander(t("\u5c55\u5f00\u67e5\u770b\u7ed3\u6784\u5316\u8be6\u60c5"), expanded=False):
        st.markdown(f"**{t('\\u7ed3\\u6784\\u5316\\u673a\\u4f1a\\u5bf9\\u8c61')}**")
        st.json(opportunity, expanded=True)
        st.markdown(f"**{t('\\u5b8c\\u6574\\u4e3b\\u94fe\\u8fd4\\u56de\\u7ed3\\u679c')}**")
        st.json(result, expanded=False)



def render_recent_opportunity_followups() -> None:
    st.subheader(t("E. Recent Opportunity Follow-up / \u6700\u8fd1\u673a\u4f1a\u8ddf\u8fdb"))
    st.caption(t("\u5f53\u524d\u7248\u672c\u7684\u8ddf\u8fdb\u8bb0\u5f55\u4ec5\u7528\u4e8e\u6700\u5c0f\u7559\u5b58\u4e0e\u56de\u770b\uff0c\u540e\u7eed\u53ef\u5e76\u5165\u66f4\u5b8c\u6574\u7684\u9879\u76ee\u7ba1\u7406\u4f53\u7cfb\u3002"))
    st.caption(t("\u7528\u4e8e\u56de\u770b\u591a\u4e2a\u6700\u8fd1\u673a\u4f1a\uff0c\u5e76\u5bf9\u5355\u6761\u673a\u4f1a\u8865\u5145\u6700\u5c0f\u8ddf\u8fdb\u72b6\u6001\u3001\u8ddf\u8fdb\u5907\u6ce8\u548c\u4e0b\u4e00\u6b65\u52a8\u4f5c\u3002"))

    try:
        items = _build_recent_followup_items(limit=8)
    except Exception as exc:
        st.error(f"{t('\u6700\u8fd1\u673a\u4f1a\u8bfb\u53d6\u5931\u8d25')} : {exc}")
        return

    if not items:
        st.info(t("\u5f53\u524d\u8fd8\u6ca1\u6709\u53ef\u56de\u770b\u7684\u6700\u8fd1\u673a\u4f1a\u8bb0\u5f55\u3002"))
        return

    for index, item in enumerate(items, start=1):
        opportunity = item["opportunity"]
        followup = item.get("followup", {}) if isinstance(item.get("followup"), dict) else {}
        opportunity_id = int(opportunity.get("id"))
        company_name = item["company_name"]
        created_at = _format_followup_datetime(item.get("created_at", ""))
        current_stage = item["current_stage"]
        current_blocker = item["current_blocker"]
        recommended_follow_up_at = str(item.get("recommended_follow_up_at", "")).strip() or t("\u5f85\u786e\u8ba4")
        expander_label = f"{index}. {company_name} | {created_at} | {current_stage}"

        with st.expander(expander_label, expanded=False):
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            with summary_col1:
                st.write(f"{t('\u8bb0\u5f55\u65f6\u95f4')}\uff1a{created_at}")
                st.write(f"{t('\u5ba2\u6237\u540d\u79f0')}\uff1a{company_name}")
            with summary_col2:
                st.write(f"{t('\u5f53\u524d\u9636\u6bb5')}\uff1a{current_stage}")
                st.write(f"{t('\u5f53\u524d\u963b\u585e\u70b9')}\uff1a{current_blocker}")
            with summary_col3:
                st.write(f"{t('\u5efa\u8bae\u4e0b\u6b21\u8ddf\u8fdb\u65f6\u95f4')}\uff1a{recommended_follow_up_at}")
                st.write(f"{t('\u673a\u4f1a\u7f16\u53f7')}\uff1a{opportunity_id}")

            st.caption(t("\u5c55\u5f00\u540e\u53ef\u505a\u5355\u6761\u673a\u4f1a\u7684\u6700\u5c0f\u8ddf\u8fdb\u66f4\u65b0\uff0c\u4e0d\u505a\u6279\u91cf\u64cd\u4f5c\u3002"))

            form_key = f"recent_followup_form_{opportunity_id}"
            default_status = str(followup.get("followup_status", "")).strip() or t("\u5f85\u8ddf\u8fdb")
            default_note = str(followup.get("followup_note", "")).strip()
            default_action = str(followup.get("next_action", "")).strip()
            default_followup_at = str(followup.get("next_followup_date", "")).strip() or recommended_follow_up_at

            with st.form(form_key):
                follow_col1, follow_col2 = st.columns(2)
                with follow_col1:
                    follow_up_status = st.text_input(t("\u8ddf\u8fdb\u72b6\u6001"), value=default_status)
                    last_follow_up_note = st.text_area(t("\u6700\u8fd1\u8ddf\u8fdb\u5907\u6ce8"), value=default_note, height=90)
                with follow_col2:
                    next_follow_up_action = st.text_area(t("\u4e0b\u4e00\u6b65\u8ddf\u8fdb\u52a8\u4f5c"), value=default_action, height=90)
                    edited_followup_at = st.text_input(t("\u5efa\u8bae\u4e0b\u6b21\u8ddf\u8fdb\u65f6\u95f4"), value=default_followup_at)

                readonly_col1, readonly_col2, readonly_col3 = st.columns(3)
                with readonly_col1:
                    st.write(f"{t('\u6838\u5fc3\u9700\u6c42')}\uff1a{_format_joined_list(opportunity.get('core_needs', []), '-')}")
                with readonly_col2:
                    st.write(f"{t('\u5ba2\u6237\u987e\u8651')}\uff1a{_format_joined_list(opportunity.get('concerns', []), '-')}")
                with readonly_col3:
                    st.write(f"{t('\u4e1a\u52a1\u65b9\u5411')}\uff1a{str(opportunity.get('business_type_guess', '')).strip() or '-'}")

                submitted = st.form_submit_button(t("\u4fdd\u5b58\u8ddf\u8fdb\u66f4\u65b0"), type="primary")

            if submitted:
                try:
                    with get_connection(DB_FILE) as conn:
                        init_app_db(conn)
                        create_followup(
                            conn,
                            {
                                "opportunity_id": opportunity_id,
                                "user_id": str(opportunity.get("user_id", "")).strip(),
                                "followup_status": str(follow_up_status).strip(),
                                "followup_note": str(last_follow_up_note).strip(),
                                "next_action": str(next_follow_up_action).strip(),
                                "next_followup_date": str(edited_followup_at).strip(),
                            },
                        )
                    st.success(t("\u8ddf\u8fdb\u66f4\u65b0\u5df2\u4fdd\u5b58\u3002"))
                    st.rerun()
                except Exception as exc:
                    st.error(f"{t('\u4fdd\u5b58\u8ddf\u8fdb\u66f4\u65b0\u5931\u8d25')} : {exc}")


def render_record_mode() -> None:
    st.subheader(t("D. Record Mode / \u8bb0\u5f55\u6a21\u5f0f"))
    result = st.session_state.get(RESULT_KEY)
    if not isinstance(result, dict):
        st.info(t("\u8bf7\u5148\u8fd0\u884c\u4e3b\u94fe\uff0c\u7136\u540e\u5728\u8fd9\u91cc review \u548c\u7f16\u8f91\u672c\u6b21\u8f93\u5165\u5bf9\u5e94\u7684\u8bb0\u5f55\u3002"))
        return

    opportunity = result.get("opportunity", {})
    if not isinstance(opportunity, dict):
        opportunity = {}

    st.caption(t("\u8fd9\u4e2a\u533a\u57df\u53ea\u9762\u5411\u672c\u6b21\u8f93\u5165\u7684\u8bb0\u5f55\uff1a\u53ef\u4ee5\u5bf9\u7ed3\u6784\u5316\u5b57\u6bb5\u8fdb\u884c review\u3001\u624b\u52a8\u4fee\u6b63\uff0c\u4f46\u4e0d\u4f1a\u5c55\u5f00\u5386\u53f2\u8bb0\u5f55\u7ba1\u7406\u3002"))

    with st.form("visit_assistant_record_mode_form"):
        st.markdown(f"**{t('\\u672c\\u6b21\\u8f93\\u5165\\u539f\\u6587')}**")
        raw_input = st.text_area(
            t("\u672c\u6b21\u8f93\u5165\u5185\u5bb9"),
            value=str(opportunity.get("raw_input", "")).strip() or str(st.session_state.get(DEMO_INPUT_KEY, "")).strip(),
            height=120,
        )

        col1, col2 = st.columns(2)
        with col1:
            company_name = st.text_input(t("\u5ba2\u6237\u540d\u79f0"), value=str(opportunity.get("company_name", "")).strip())
            contact_name = st.text_input(t("\u8054\u7cfb\u4eba"), value=str(opportunity.get("contact_name", "")).strip())
            contact_phone = st.text_input(t("\u8054\u7cfb\u7535\u8bdd"), value=str(opportunity.get("contact_phone", "")).strip())
            industry = st.text_input(t("\u884c\u4e1a\u5224\u65ad"), value=str(opportunity.get("industry", "")).strip())
            current_stage = st.text_input(t("\u5f53\u524d\u9636\u6bb5"), value=str(opportunity.get("current_stage", "new")).strip() or "new")
        with col2:
            business_type = st.text_input(t("\u4e1a\u52a1\u65b9\u5411"), value=str(opportunity.get("business_type_guess", "")).strip())
            power_load_requirement = st.text_input(t("\u8d1f\u8f7d\u9700\u6c42"), value=str(opportunity.get("power_load_requirement", "")).strip())
            budget_hint = st.text_input(t("\u9884\u7b97\u7ebf\u7d22"), value=str(opportunity.get("budget_hint", "")).strip())
            core_needs = st.text_area(t("\u6838\u5fc3\u9700\u6c42\uff08\u7528\u9017\u53f7\u6216\u987f\u53f7\u5206\u9694\uff09"), value="\u3001".join(opportunity.get("core_needs", [])), height=90)
            concerns = st.text_area(t("\u5ba2\u6237\u987e\u8651\uff08\u7528\u9017\u53f7\u6216\u987f\u53f7\u5206\u9694\uff09"), value="\u3001".join(opportunity.get("concerns", [])), height=90)

        submitted = st.form_submit_button(t("\u4fdd\u5b58\u672c\u6b21 review \u4fee\u6539"), type="primary")

    if submitted:
        def split_items(value: str) -> list[str]:
            normalized = str(value).replace("\uFF0C", ",").replace("\u3001", ",").replace("\n", ",")
            return [item.strip() for item in normalized.split(",") if item.strip()]

        updated_opportunity = dict(opportunity)
        updated_opportunity["raw_input"] = str(raw_input).strip()
        updated_opportunity["company_name"] = str(company_name).strip()
        updated_opportunity["contact_name"] = str(contact_name).strip()
        updated_opportunity["contact_phone"] = str(contact_phone).strip()
        updated_opportunity["industry"] = str(industry).strip()
        updated_opportunity["current_stage"] = str(current_stage).strip() or "new"
        updated_opportunity["business_type_guess"] = str(business_type).strip()
        updated_opportunity["power_load_requirement"] = str(power_load_requirement).strip()
        updated_opportunity["budget_hint"] = str(budget_hint).strip()
        updated_opportunity["core_needs"] = split_items(core_needs)
        updated_opportunity["concerns"] = split_items(concerns)

        needs_review, review_reasons = build_review_flags(updated_opportunity)
        updated_opportunity["needs_review"] = needs_review
        updated_opportunity["review_reasons"] = review_reasons

        updated_result = dict(result)
        updated_result["opportunity"] = updated_opportunity
        suggestion, reason = suggest_followup_timing(updated_opportunity)
        updated_result["followup_time_suggestion"] = suggestion
        updated_result["followup_time_reason"] = reason

        try:
            opportunity_id = int(updated_opportunity.get("id"))
            with get_connection(DB_FILE) as conn:
                init_app_db(conn)
                before_record = next(
                    (record for record in list_opportunities(conn) if int(record.get("id", 0)) == opportunity_id),
                    None,
                )
                if before_record is None:
                    raise ValueError(t("未找到本次记录对应的数据库条目"))

                persisted_record = dict(before_record)
                persisted_record.update(updated_opportunity)
                persisted_record["updated_at"] = datetime.now(timezone.utc).isoformat()
                update_opportunity(conn, opportunity_id, persisted_record)

            append_opportunity_correction_log(
                str(opportunity_id),
                "manual_edit",
                dict(before_record),
                dict(persisted_record),
            )

            updated_result["opportunity"] = persisted_record
            st.session_state[PENDING_DEMO_INPUT_KEY] = persisted_record["raw_input"]
            st.session_state[RESULT_KEY] = updated_result
            st.session_state[POST_SAVE_FEEDBACK_KEY] = build_post_save_feedback(
                persisted_record,
                saved_to_file=True,
                correction_logged=True,
            )
            st.rerun()
        except Exception as exc:
            st.error(f"{t('\u4fdd\u5b58\u5931\u8d25')} : {exc}")

    review_reasons = opportunity.get("review_reasons", [])
    if isinstance(review_reasons, list) and review_reasons:
        st.caption(t("\u5f53\u524d review \u63d0\u9192\uff1a") + t("\uff1b").join(humanize_review_reason(str(item)) for item in review_reasons if str(item).strip()))

    feedback = st.session_state.get(POST_SAVE_FEEDBACK_KEY)
    if isinstance(feedback, dict):
        render_post_save_feedback(feedback)

    with st.expander(t("\u5c55\u5f00\u67e5\u770b\u672c\u6b21\u8bb0\u5f55 JSON"), expanded=False):
        st.json(opportunity, expanded=False)




def main() -> None:
    st.set_page_config(page_title=t("\u5ba2\u6237\u62dc\u8bbf\u52a9\u624b Demo"), layout="wide")
    st.session_state.setdefault(DEMO_INPUT_KEY, "")
    pending_demo_input = st.session_state.pop(PENDING_DEMO_INPUT_KEY, None)
    if pending_demo_input is not None:
        st.session_state[DEMO_INPUT_KEY] = str(pending_demo_input)

    render_header()
    render_demo_guide()
    render_input_section()
    render_result_section()
    render_record_mode()
    render_recent_opportunity_followups()


if __name__ == "__main__":
    main()
