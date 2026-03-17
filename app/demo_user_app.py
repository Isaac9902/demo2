import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.init_app_db import DB_FILE, get_connection, init_app_db
from pipeline.manage_opportunity_records import create_followup, delete_opportunity, list_followups, list_opportunities
from pipeline.run_opportunity_flow import run_opportunity_flow, suggest_followup_timing

USER_ID_KEY = "demo_user_app_user_id"
INPUT_KEY = "demo_user_app_input"
RESULT_KEY = "demo_user_app_last_result"


def t(value: str) -> str:
    if "\\u" in value:
        return value.encode("utf-8").decode("unicode_escape")
    return value


def get_demo_samples() -> list[dict]:
    return [
        {
            "title": t("\u81ea\u52a8\u5316\u8bbe\u5907\u5ba2\u6237\u65b0\u589e\u4ea7\u7ebf"),
            "text": t("\u6df1\u5733\u5b9d\u5b89\u4e00\u4e2a\u81ea\u52a8\u5316\u8bbe\u5907\u5ba2\u6237\uff0c\u8054\u7cfb\u4eba\u738b\u5de5\uff0c\u7535\u8bdd13800138000\uff0c\u6700\u8fd1\u65b0\u589e\u4ea7\u7ebf\uff0c\u9700\u8981\u4f4e\u538b\u914d\u7535\u67dc\uff0c\u62c5\u5fc3\u4ea4\u4ed8\u5468\u671f\uff0c\u5e0c\u671b\u5148\u770b\u770b\u7c7b\u4f3c\u6848\u4f8b\u3002"),
        },
        {
            "title": t("\u5de5\u5382\u6269\u5bb9\u4e0e\u8d1f\u8f7d\u9700\u6c42"),
            "text": t("\u67d0\u5de5\u5382\u9884\u8ba1\u603b\u8d1f\u83771.2MW\uff0c\u8003\u8651\u6269\u5bb9\uff0c\u9700\u8981\u8bc4\u4f30\u914d\u7535\u6539\u9020\u65b9\u6848\uff0c\u8054\u7cfb\u4eba\u674e\u5de5\uff0c\u7535\u8bdd13900139000\u3002"),
        },
        {
            "title": t("\u8001\u65e7\u5de5\u4e1a\u56ed\u6539\u9020"),
            "text": t("\u5e7f\u5dde\u67d0\u8001\u65e7\u5de5\u4e1a\u56ed\u914d\u7535\u7cfb\u7edf\u60f3\u6539\u9020\uff0c\u5ba2\u6237\u8fd8\u6ca1\u786e\u5b9a\u5177\u4f53\u5bb9\u91cf\uff0c\u5148\u4e86\u89e3\u7c7b\u4f3c\u9879\u76ee\uff0c\u62c5\u5fc3\u65bd\u5de5\u5f71\u54cd\u751f\u4ea7\u3002"),
        },
    ]


def display_text(value: object, empty_text: str) -> str:
    text = str(value or "").strip()
    return text if text else empty_text


def format_joined_list(values: object, empty_text: str) -> str:
    if not isinstance(values, list):
        return empty_text
    cleaned = [str(item).strip() for item in values if str(item).strip()]
    return t("\u3001").join(cleaned) if cleaned else empty_text


def format_time(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return t("\u5f85\u786e\u8ba4")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return dt.strftime("%Y-%m-%d %H:%M")


def derive_current_blocker(opportunity: dict) -> str:
    concerns = opportunity.get("concerns", [])
    if isinstance(concerns, list):
        for item in concerns:
            cleaned = str(item).strip()
            if cleaned:
                return cleaned
    review_reasons = opportunity.get("review_reasons", [])
    if isinstance(review_reasons, list):
        for item in review_reasons:
            cleaned = str(item).strip()
            if cleaned:
                return cleaned
    if bool(opportunity.get("needs_review")):
        return t("\u5173\u952e\u4fe1\u606f\u4ecd\u5f85\u8865\u5145")
    return t("\u6682\u65e0\u660e\u663e\u963b\u585e")


def load_recent_user_opportunities(user_id: str, limit: int = 8) -> list[dict]:
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        return list_opportunities(conn, user_id=user_id)[:limit]


def get_followup_history_map(opportunity_ids: list[int]) -> dict[int, list[dict]]:
    result: dict[int, list[dict]] = {}
    if not opportunity_ids:
        return result
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        for opportunity_id in opportunity_ids:
            result[opportunity_id] = list_followups(conn, opportunity_id)
    return result


def delete_followup_record(followup_id: int) -> None:
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        conn.execute("DELETE FROM opportunity_followups WHERE id = ?", (followup_id,))
        conn.commit()

def delete_opportunity_record(opportunity_id: int) -> None:
    with get_connection(DB_FILE) as conn:
        init_app_db(conn)
        delete_opportunity(conn, opportunity_id)


def render_header() -> None:
    st.title("Demo User App")
    st.caption(t("\u9762\u5411\u552e\u524d/\u9500\u552e\u7684\u9879\u76ee\u673a\u4f1a\u5206\u6790\u4e0e\u8ddf\u8fdb\u6f14\u793a\u5165\u53e3"))
    st.write(t("\u5148\u586b\u5199 user_id\uff0c\u518d\u8f93\u5165\u5ba2\u6237\u9700\u6c42\u63cf\u8ff0\u6216\u52a0\u8f7d\u6837\u4f8b\uff0c\u7cfb\u7edf\u4f1a\u751f\u6210\u673a\u4f1a\u5206\u6790\u7ed3\u679c\uff0c\u5e76\u4fdd\u5b58\u5230\u5f53\u524d user_id \u4e0b\u7684\u6700\u8fd1\u8bb0\u5f55\u4e2d\u3002"))


def render_user_id_section() -> str:
    st.subheader("1. user_id")
    return st.text_input("user_id", key=USER_ID_KEY, placeholder="demo_user_01 / heqi / guest_a")


def render_sample_section() -> None:
    st.subheader(t("2. \u6837\u4f8b\u8f93\u5165"))
    cols = st.columns(len(get_demo_samples()))
    for index, sample in enumerate(get_demo_samples()):
        with cols[index]:
            st.markdown(f"**{sample['title']}**")
            if st.button(t("\u52a0\u8f7d\u8fd9\u6761\u6837\u4f8b"), key=f"demo_user_sample_{index}"):
                st.session_state[INPUT_KEY] = sample["text"]
                st.rerun()


def render_input_section(user_id: str) -> None:
    st.subheader(t("3. \u9700\u6c42\u8f93\u5165\u4e0e\u5206\u6790"))
    st.text_area(
        t("\u5ba2\u6237\u9700\u6c42\u63cf\u8ff0 / \u62dc\u8bbf\u7eaa\u8981"),
        key=INPUT_KEY,
        height=180,
        placeholder=t("\u4f8b\u5982\uff1a\u6df1\u5733\u67d0\u81ea\u52a8\u5316\u8bbe\u5907\u5ba2\u6237\u6700\u8fd1\u65b0\u589e\u4ea7\u7ebf\uff0c\u9700\u8981\u4f4e\u538b\u914d\u7535\u67dc\uff0c\u62c5\u5fc3\u4ea4\u4ed8\u5468\u671f......"),
    )
    if st.button(t("\u8fd0\u884c\u5206\u6790"), type="primary"):
        raw_input = str(st.session_state.get(INPUT_KEY, "")).strip()
        if not str(user_id).strip():
            st.warning(t("\u8bf7\u5148\u586b\u5199 user_id\uff0c\u518d\u8fd0\u884c\u5206\u6790\u3002"))
            return
        if not raw_input:
            st.warning(t("\u8bf7\u8f93\u5165\u5ba2\u6237\u9700\u6c42\u63cf\u8ff0\uff0c\u6216\u5148\u52a0\u8f7d\u4e00\u6761\u6837\u4f8b\u3002"))
            return
        try:
            with st.spinner(t("\u7cfb\u7edf\u5df2\u63a5\u6536\u8bf7\u6c42\uff0c\u6b63\u5728\u5206\u6790\u673a\u4f1a\u3001\u68c0\u7d22\u6848\u4f8b\u5e76\u751f\u6210\u5efa\u8bae\uff0c\u8bf7\u52ff\u91cd\u590d\u70b9\u51fb\u3002")):
                st.session_state[RESULT_KEY] = run_opportunity_flow(raw_input, top_k=3, source_mode="demo_user_app", user_id=user_id)
        except Exception as exc:
            st.error(f"{t('\u8fd0\u884c\u5206\u6790\u5931\u8d25')} : {exc}")


def render_result_section() -> None:
    st.subheader(t("4. \u5206\u6790\u7ed3\u679c"))
    result = st.session_state.get(RESULT_KEY)
    if not isinstance(result, dict):
        st.info(t("\u8fd0\u884c\u5206\u6790\u540e\uff0c\u8fd9\u91cc\u4f1a\u5c55\u793a opportunity \u6458\u8981\u3001\u76f8\u4f3c\u9879\u76ee\u548c\u5efa\u8bae\u5c42\u3002"))
        return

    opportunity = result.get("opportunity", {}) if isinstance(result.get("opportunity", {}), dict) else {}
    st.markdown("#### Opportunity \u6458\u8981")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"\u5ba2\u6237\u540d\u79f0\uff1a{display_text(opportunity.get('company_name', ''), t('\u5ba2\u6237\u540d\u672a\u5f55\u5165'))}")
        st.write(f"\u8054\u7cfb\u4eba\uff1a{display_text(opportunity.get('contact_name', ''), t('\u8054\u7cfb\u4eba\u672a\u8bc6\u522b'))}")
        st.write(f"\u884c\u4e1a\u5224\u65ad\uff1a{display_text(opportunity.get('industry', ''), t('\u5f85\u8fdb\u4e00\u6b65\u5224\u65ad'))}")
        st.write(f"\u4e1a\u52a1\u65b9\u5411\uff1a{display_text(opportunity.get('business_type_guess', ''), t('\u5f85\u8fdb\u4e00\u6b65\u5224\u65ad'))}")
        st.write(f"\u5f53\u524d\u9636\u6bb5\uff1a{display_text(opportunity.get('current_stage', ''), 'new')}")
    with col2:
        st.write(f"\u6838\u5fc3\u9700\u6c42\uff1a{format_joined_list(opportunity.get('core_needs', []), t('\u5f85\u8865\u5145'))}")
        st.write(f"\u5ba2\u6237\u987e\u8651\uff1a{format_joined_list(opportunity.get('concerns', []), t('\u6682\u65e0'))}")
        st.write(f"\u8d1f\u8f7d\u9700\u6c42\uff1a{display_text(opportunity.get('power_load_requirement', ''), t('\u5f85\u8865\u5145'))}")
        estimated_load_kw = opportunity.get('estimated_load_kw')
        st.write(f"\u9884\u8ba1\u8d1f\u8f7d(kW)\uff1a{estimated_load_kw if estimated_load_kw not in (None, '') else '-'}")

    st.markdown("#### Top-K \u76f8\u4f3c\u9879\u76ee")
    cases = result.get("top_k_cases", [])
    if isinstance(cases, list) and cases:
        for index, item in enumerate(cases[:3], start=1):
            title = display_text(item.get('project_name', ''), t('\u672a\u547d\u540d\u9879\u76ee'))
            with st.expander(f"\u6848\u4f8b {index}\uff1a{title}", expanded=False):
                reasons = item.get("matched_reasons", [])
                reason_text = format_joined_list(reasons, t("\u6682\u65e0\u660e\u786e\u5339\u914d\u539f\u56e0"))
                st.write(f"\u5339\u914d\u539f\u56e0\uff1a{reason_text}")
                st.write(f"\u4e1a\u52a1\u7c7b\u578b\uff1a{display_text(item.get('business_type', ''), '-')}")
                st.write(f"\u9879\u76ee\u5730\u533a\uff1a{display_text(item.get('location_city', ''), '-')}")
                st.write(f"\u5efa\u8bbe\u5355\u4f4d\uff1a{display_text(item.get('company_name', ''), '-')}")
    else:
        st.info(t("\u5f53\u524d\u6ca1\u6709\u627e\u5230\u53ef\u76f4\u63a5\u53c2\u8003\u7684\u76f8\u4f3c\u9879\u76ee\u3002"))

    st.markdown("#### \u5efa\u8bae\u5c42")
    recommendation = result.get("visit_recommendation", {}) if isinstance(result.get("visit_recommendation", {}), dict) else {}
    rec_col1, rec_col2 = st.columns(2)
    with rec_col1:
        st.markdown("**\u5efa\u8bae\u8ffd\u95ee**")
        for item in recommendation.get("questions_to_ask", []) or [t("\u5f53\u524d\u65e0\u660e\u786e\u8ffd\u95ee\u9879")]:
            st.write(f"- {item}")
        st.markdown("**\u5efa\u8bae\u805a\u7126\u70b9**")
        for item in recommendation.get("suggested_focus_points", []) or [t("\u5f53\u524d\u65e0\u660e\u786e\u805a\u7126\u70b9")]:
            st.write(f"- {item}")
    with rec_col2:
        st.markdown("**\u5efa\u8bae\u4e0b\u4e00\u6b65**")
        for item in recommendation.get("next_actions", []) or [t("\u5f53\u524d\u65e0\u660e\u786e\u4e0b\u4e00\u6b65")]:
            st.write(f"- {item}")
        st.markdown("**\u98ce\u9669\u63d0\u793a**")
        for item in recommendation.get("risk_notes", []) or [t("\u5f53\u524d\u65e0\u660e\u786e\u98ce\u9669\u63d0\u793a")]:
            st.write(f"- {item}")


def render_recent_followups(user_id: str) -> None:
    st.subheader(t("5. 最近机会跟进"))
    st.caption(t("\u5f53\u524d\u7248\u672c\u7684\u8ddf\u8fdb\u8bb0\u5f55\u4ec5\u7528\u4e8e\u6700\u5c0f\u7559\u5b58\u4e0e\u56de\u770b\uff0c\u540e\u7eed\u53ef\u5e76\u5165\u66f4\u5b8c\u6574\u7684\u9879\u76ee\u7ba1\u7406\u4f53\u7cfb\u3002"))
    if not str(user_id).strip():
        st.info(t("请先填写 user_id，再查看当前用户的最近机会记录。"))
        return

    try:
        with get_connection(DB_FILE) as conn:
            init_app_db(conn)
            opportunities = list_opportunities(conn, user_id=user_id)
    except Exception as exc:
        st.error(f"{t('\u6700\u8fd1\u673a\u4f1a\u8bfb\u53d6\u5931\u8d25')} : {exc}")
        return

    if not opportunities:
        st.info(t("当前 user_id 下暂无机会记录。"))
        return

    selected_key = "demo_user_app_selected_opportunity_id"
    valid_ids = [int(item["id"]) for item in opportunities if item.get("id") not in (None, "")]
    selected_opportunity_id = st.session_state.get(selected_key)
    if selected_opportunity_id not in valid_ids:
        selected_opportunity_id = valid_ids[0]
        st.session_state[selected_key] = selected_opportunity_id

    followup_history_map = get_followup_history_map(valid_ids)

    with st.container(border=True):
        st.markdown(t("#### 最近机会列表"))
        st.caption(t("上方为可操作的机会列表，点击“查看”切换下方详情，点击“删除”就地确认。"))

        header_cols = st.columns([1.5, 1.8, 1.2, 2.0, 1.6, 1.8])
        header_cols[0].caption(t("记录时间"))
        header_cols[1].caption(t("客户名称"))
        header_cols[2].caption(t("当前阶段"))
        header_cols[3].caption(t("当前阻塞点"))
        header_cols[4].caption(t("建议下次跟进时间"))
        header_cols[5].caption(t("操作"))

        for index, opportunity in enumerate(opportunities):
            opportunity_id = int(opportunity["id"])
            followup_history = followup_history_map.get(opportunity_id, [])
            latest_followup = followup_history[0] if followup_history else {}
            recommended_follow_up_at = str(latest_followup.get("next_followup_date", "")).strip()
            if not recommended_follow_up_at:
                recommended_follow_up_at, _ = suggest_followup_timing(opportunity)

            row = st.container(border=True)
            with row:
                row_cols = st.columns([1.5, 1.8, 1.2, 2.0, 1.6, 1.8])
                time_text = format_time(opportunity.get("created_at", ""))
                if opportunity_id == selected_opportunity_id:
                    time_text = f"{time_text}  {t('\u5f53\u524d\u67e5\u770b')}"
                row_cols[0].write(time_text)
                row_cols[1].write(display_text(opportunity.get("company_name", ""), t("客户名未录入")))
                row_cols[2].write(display_text(opportunity.get("current_stage", ""), "new"))
                row_cols[3].write(derive_current_blocker(opportunity))
                row_cols[4].write(recommended_follow_up_at or t("待确认"))

                with row_cols[5]:
                    action_cols = st.columns(2)
                    view_label = t("查看中") if opportunity_id == selected_opportunity_id else t("查看")
                    if action_cols[0].button(
                        view_label,
                        key=f"view_opportunity_{opportunity_id}",
                        use_container_width=True,
                        disabled=opportunity_id == selected_opportunity_id,
                    ):
                        st.session_state[selected_key] = opportunity_id
                        st.rerun()
                    if action_cols[1].button(
                        t("删除"),
                        key=f"delete_opportunity_{opportunity_id}",
                        use_container_width=True,
                    ):
                        st.session_state[f"pending_delete_opportunity_{opportunity_id}"] = True
                        st.session_state[selected_key] = opportunity_id
                        st.rerun()

                pending_delete_key = f"pending_delete_opportunity_{opportunity_id}"
                if st.session_state.get(pending_delete_key):
                    st.warning(t("确认删除这条机会记录吗？这会一并移除关联的跟进记录。"))
                    confirm_cols = st.columns(2)
                    if confirm_cols[0].button(
                        t("确认删除"),
                        key=f"confirm_delete_opportunity_{opportunity_id}",
                        use_container_width=True,
                    ):
                        delete_opportunity_record(opportunity_id)
                        st.session_state.pop(pending_delete_key, None)
                        if st.session_state.get(selected_key) == opportunity_id:
                            st.session_state.pop(selected_key, None)
                        st.rerun()
                    if confirm_cols[1].button(
                        t("取消"),
                        key=f"cancel_delete_opportunity_{opportunity_id}",
                        use_container_width=True,
                    ):
                        st.session_state.pop(pending_delete_key, None)
                        st.rerun()

            if index < len(opportunities) - 1:
                st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)

    selected_opportunity = next((item for item in opportunities if int(item["id"]) == selected_opportunity_id), None)
    if not selected_opportunity:
        return

    opportunity_id = int(selected_opportunity["id"])
    followup_history = followup_history_map.get(opportunity_id, [])
    latest_followup = followup_history[0] if followup_history else {}
    recommended_follow_up_at = str(latest_followup.get("next_followup_date", "")).strip()
    if not recommended_follow_up_at:
        recommended_follow_up_at, _ = suggest_followup_timing(selected_opportunity)

    with st.container(border=True):
        title = display_text(selected_opportunity.get("company_name", ""), t("客户名未录入"))
        st.markdown(t("#### 当前选中机会详情"))
        st.caption(f"{t('\u5f53\u524d\u67e5\u770b')} : {title} | ID {opportunity_id}")

        summary1, summary2, summary3 = st.columns(3)
        with summary1:
            st.write(f"{t('\u8bb0\u5f55\u65f6\u95f4')} : {format_time(selected_opportunity.get('created_at', ''))}")
            st.write(f"{t('\u5ba2\u6237\u540d\u79f0')} : {title}")
        with summary2:
            st.write(f"{t('\u5f53\u524d\u9636\u6bb5')} : {display_text(selected_opportunity.get('current_stage', ''), 'new')}")
            st.write(f"{t('\u5f53\u524d\u963b\u585e\u70b9')} : {derive_current_blocker(selected_opportunity)}")
        with summary3:
            st.write(f"{t('\u5efa\u8bae\u4e0b\u6b21\u8ddf\u8fdb\u65f6\u95f4')} : {recommended_follow_up_at or t('\u5f85\u786e\u8ba4')}")
            st.write(f"{t('\u673a\u4f1a\u7f16\u53f7')} : {opportunity_id}")

        st.markdown(t("#### \u6700\u65b0\u8ddf\u8fdb\u8bb0\u5f55"))
        if latest_followup:
            with st.container(border=True):
                st.caption(t("\u6700\u65b0\u4e00\u6761\u8ddf\u8fdb"))
                st.write(f"{t('\u8ddf\u8fdb\u72b6\u6001')} : {display_text(latest_followup.get('followup_status', ''), t('\u5f85\u8ddf\u8fdb'))}")
                st.write(f"{t('\u6700\u8fd1\u8ddf\u8fdb\u5907\u6ce8')} : {display_text(latest_followup.get('followup_note', ''), t('\u6682\u65e0'))}")
                st.write(f"{t('\u4e0b\u4e00\u6b65\u8ddf\u8fdb\u52a8\u4f5c')} : {display_text(latest_followup.get('next_action', ''), t('\u6682\u65e0'))}")
                st.write(f"{t('\u5efa\u8bae\u4e0b\u6b21\u8ddf\u8fdb\u65f6\u95f4')} : {display_text(latest_followup.get('next_followup_date', ''), t('\u5f85\u786e\u8ba4'))}")
                latest_followup_id = int(latest_followup["id"])
                latest_delete_state_key = f"pending_delete_latest_followup_{latest_followup_id}"
                if st.button(t("\u5220\u9664\u8fd9\u6761\u6700\u65b0\u8ddf\u8fdb\u8bb0\u5f55"), key=f"trigger_delete_latest_followup_{latest_followup_id}"):
                    st.session_state[latest_delete_state_key] = True
                    st.rerun()
                if st.session_state.get(latest_delete_state_key):
                    st.warning(t("\u786e\u8ba4\u5220\u9664\u8fd9\u6761\u6700\u65b0\u8ddf\u8fdb\u8bb0\u5f55\u5417\uff1f"))
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button(t("\u786e\u8ba4\u5220\u9664"), key=f"confirm_delete_latest_followup_{latest_followup_id}"):
                            delete_followup_record(latest_followup_id)
                            st.session_state.pop(latest_delete_state_key, None)
                            st.rerun()
                    with confirm_col2:
                        if st.button(t("\u53d6\u6d88"), key=f"cancel_delete_latest_followup_{latest_followup_id}"):
                            st.session_state.pop(latest_delete_state_key, None)
                            st.rerun()

        else:
            st.info(t("\u8fd9\u6761\u673a\u4f1a\u5f53\u524d\u8fd8\u6ca1\u6709\u8ddf\u8fdb\u8bb0\u5f55\u3002"))

        st.markdown(t("#### \u540e\u7eed\u8ddf\u8fdb\u8bb0\u5f55"))
        if len(followup_history) > 1:
            for display_index, history_item in enumerate(followup_history[1:], start=1):
                history_followup_id = int(history_item["id"])
                with st.container(border=True):
                    st.caption(f"{t('\u540e\u7eed\u8ddf\u8fdb')} #{display_index}")
                    st.write(f"{t('\u8bb0\u5f55\u65f6\u95f4')} : {format_time(history_item.get('created_at', ''))}")
                    st.write(f"{t('\u8ddf\u8fdb\u72b6\u6001')} : {display_text(history_item.get('followup_status', ''), t('\u5f85\u8ddf\u8fdb'))}")
                    st.write(f"{t('\u8ddf\u8fdb\u5907\u6ce8')} : {display_text(history_item.get('followup_note', ''), t('\u6682\u65e0'))}")
                    st.write(f"{t('\u4e0b\u4e00\u6b65\u52a8\u4f5c')} : {display_text(history_item.get('next_action', ''), t('\u6682\u65e0'))}")
                    if st.button(t("\u5220\u9664\u8fd9\u6761\u8ddf\u8fdb\u8bb0\u5f55") + f" #{display_index}", key=f"trigger_delete_history_followup_{history_followup_id}"):
                        st.session_state[f"pending_delete_history_followup_{history_followup_id}"] = True
                        st.rerun()
                    if st.session_state.get(f"pending_delete_history_followup_{history_followup_id}"):
                        st.warning(t("\u786e\u8ba4\u5220\u9664\u8fd9\u6761\u8ddf\u8fdb\u8bb0\u5f55\u5417\uff1f"))
                        confirm_col1, confirm_col2 = st.columns(2)
                        with confirm_col1:
                            if st.button(t("\u786e\u8ba4\u5220\u9664"), key=f"confirm_delete_history_followup_{history_followup_id}"):
                                delete_followup_record(history_followup_id)
                                st.session_state.pop(f"pending_delete_history_followup_{history_followup_id}", None)
                                st.rerun()
                        with confirm_col2:
                            if st.button(t("\u53d6\u6d88"), key=f"cancel_delete_history_followup_{history_followup_id}"):
                                st.session_state.pop(f"pending_delete_history_followup_{history_followup_id}", None)
                                st.rerun()
        else:
            st.caption(t("\u6682\u65e0\u66f4\u65e9\u7684\u540e\u7eed\u8ddf\u8fdb\u8bb0\u5f55\u3002"))



        st.markdown(t("#### 跟进更新"))
        with st.form(f"demo_user_followup_{opportunity_id}"):
            left, right = st.columns(2)
            with left:
                follow_up_status = st.text_input(t("跟进状态"), value=str(latest_followup.get('followup_status', '')).strip())
                last_follow_up_note = st.text_area(t("最近跟进备注"), value=str(latest_followup.get('followup_note', '')).strip(), height=90)
            with right:
                next_follow_up_action = st.text_area(t("下一步跟进动作"), value=str(latest_followup.get('next_action', '')).strip(), height=90)
                edited_followup_at = st.text_input(t("建议下次跟进时间"), value=str(latest_followup.get('next_followup_date', '')).strip() or recommended_follow_up_at)

            info1, info2, info3 = st.columns(3)
            with info1:
                st.write(f"{t('\u6838\u5fc3\u9700\u6c42')} : {format_joined_list(selected_opportunity.get('core_needs', []), '-')}")
            with info2:
                st.write(f"{t('\u5ba2\u6237\u987e\u8651')} : {format_joined_list(selected_opportunity.get('concerns', []), '-')}")
            with info3:
                st.write(f"{t('\u4e1a\u52a1\u65b9\u5411')} : {display_text(selected_opportunity.get('business_type_guess', ''), '-')}")

            submitted = st.form_submit_button(t("保存跟进更新"), type="primary")

        if submitted:
            try:
                with get_connection(DB_FILE) as conn:
                    init_app_db(conn)
                    create_followup(
                        conn,
                        {
                            "opportunity_id": opportunity_id,
                            "user_id": user_id,
                            "followup_status": str(follow_up_status).strip(),
                            "followup_note": str(last_follow_up_note).strip(),
                            "next_action": str(next_follow_up_action).strip(),
                            "next_followup_date": str(edited_followup_at).strip(),
                        },
                    )
                st.success(t("跟进更新已保存。"))
                st.rerun()
            except Exception as exc:
                st.error(f"{t('\u4fdd\u5b58\u8ddf\u8fdb\u66f4\u65b0\u5931\u8d25')} : {exc}")


def render_demo_notice() -> None:
    st.caption(t("\u5f53\u524d\u4e3a Demo \u4f53\u9a8c\u5165\u53e3\uff0cuser_id \u7531\u624b\u52a8\u586b\u5199\uff0c\u64cd\u4f5c\u4e0d\u505a\u4e25\u683c\u5ba1\u8ba1\u4e0e\u8ffd\u6eaf\uff0c\u4e0d\u7b49\u540c\u4e8e\u6b63\u5f0f\u751f\u4ea7\u7cfb\u7edf\u3002"))


def main() -> None:
    st.set_page_config(page_title="Demo User App", layout="wide")
    st.session_state.setdefault(USER_ID_KEY, "")
    st.session_state.setdefault(INPUT_KEY, "")
    render_header()
    user_id = render_user_id_section()
    render_sample_section()
    render_input_section(user_id)
    render_result_section()
    render_recent_followups(user_id)
    render_demo_notice()


if __name__ == "__main__":
    main()
