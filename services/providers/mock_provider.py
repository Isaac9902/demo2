from services.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """Mock provider for local development."""

    provider_name = "mock"
    model_name = "mock-v1"

    def run_task(self, task_name: str, payload: dict) -> dict:
        if task_name == "normalize_project_case":
            case = dict(payload.get("case", {}))
            normalized_case = dict(case)
            normalized_case["project_name"] = str(case.get("project_name", "")).strip()
            normalized_case["business_type"] = str(
                case.get("business_type", "其他") or "其他"
            ).strip()
            keywords = case.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = []
            normalized_case["keywords"] = [str(item).strip() for item in keywords if str(item).strip()]
            return self.build_response(
                task_name,
                True,
                {
                    "normalized_case": normalized_case,
                    "notes": ["Mock normalized project case."],
                },
            )

        if task_name == "generate_followup_tasks":
            context = payload.get("context", {})
            customer_name = str(context.get("customer_name", "客户")).strip() or "客户"
            return self.build_response(
                task_name,
                True,
                {
                    "tasks": [
                        {
                            "title": f"整理{customer_name}需求摘要",
                            "owner": "销售",
                            "priority": "high",
                        },
                        {
                            "title": "确认项目预算与时间窗口",
                            "owner": "项目经理",
                            "priority": "medium",
                        },
                        {
                            "title": "准备相似案例材料",
                            "owner": "售前",
                            "priority": "medium",
                        },
                    ]
                },
            )

        if task_name == "extract_visit_insights":
            raw_text = str(payload.get("raw_text", "")).strip()
            preview = raw_text[:50]
            return self.build_response(
                task_name,
                True,
                {
                    "summary": "客户关注交付周期、预算和类似案例。",
                    "risks": ["需求仍可能变化", "预算边界尚未完全确认"],
                    "next_actions": ["补充需求清单", "安排方案澄清"],
                    "source_preview": preview,
                },
            )

        if task_name == "generate_visit_recommendation":
            opportunity = payload.get("opportunity", {})
            company_name = str(opportunity.get("company_name", "")).strip() or "客户"
            business_type = str(opportunity.get("business_type_guess", "")).strip() or "配电相关项目"
            return self.build_response(
                task_name,
                True,
                {
                    "questions_to_ask": [
                        f"确认{company_name}本次要推进的是新建、改造还是扩容场景。",
                        "确认预计投运时间和最晚交付节点。",
                    ],
                    "suggested_focus_points": [
                        f"优先讲与{business_type}最接近的实施案例和交付边界。",
                        "重点强调交付周期把控和现场配合经验。",
                    ],
                    "next_actions": [
                        "整理一页案例摘要并标注匹配原因。",
                        "拜访前确认客户现场勘查和技术对接人员。",
                    ],
                    "risk_notes": [
                        "需求边界未锁定时，方案和报价容易反复。",
                        "若交付周期敏感但现场条件不明，后续承诺存在风险。",
                    ],
                },
            )

        return self.build_response(
            task_name,
            False,
            error=f"Unsupported mock task: {task_name}",
        )
