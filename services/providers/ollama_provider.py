import json
import os
import urllib.error
import urllib.request

from services.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    """Minimal Ollama provider for local LLM access."""

    provider_name = "ollama"
    VALID_PROVINCES = {
        "北京",
        "天津",
        "上海",
        "重庆",
        "河北",
        "山西",
        "辽宁",
        "吉林",
        "黑龙江",
        "江苏",
        "浙江",
        "安徽",
        "福建",
        "江西",
        "山东",
        "河南",
        "湖北",
        "湖南",
        "广东",
        "海南",
        "四川",
        "贵州",
        "云南",
        "陕西",
        "甘肃",
        "青海",
        "台湾",
        "内蒙古",
        "广西",
        "西藏",
        "宁夏",
        "新疆",
        "香港",
        "澳门",
    }
    NORMALIZE_PROJECT_CASE_SCHEMA = {
        "type": "object",
        "properties": {
            "location_province": {"type": "string"},
            "location_city": {"type": "string"},
            "location_district": {"type": "string"},
            "business_type": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "location_province",
            "location_city",
            "location_district",
            "business_type",
            "keywords",
        ],
    }
    VISIT_RECOMMENDATION_SCHEMA = {
        "type": "object",
        "properties": {
            "questions_to_ask": {"type": "array", "items": {"type": "string"}},
            "suggested_focus_points": {"type": "array", "items": {"type": "string"}},
            "next_actions": {"type": "array", "items": {"type": "string"}},
            "risk_notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "questions_to_ask",
            "suggested_focus_points",
            "next_actions",
            "risk_notes",
        ],
    }

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
        self.model_name = model or os.getenv("OLLAMA_MODEL") or "qwen3:8b"

    def run_task(self, task_name: str, payload: dict) -> dict:
        if task_name == "normalize_project_case":
            case = payload.get("case", {})
            if not isinstance(case, dict):
                return self.build_response(
                    task_name,
                    False,
                    error="Payload must include a dict field: case",
                )

            prompt = self._build_normalize_prompt(case)
            try:
                normalized_case = self._call_json_task(
                    prompt,
                    self.NORMALIZE_PROJECT_CASE_SCHEMA,
                    self._validate_normalized_case,
                )
            except RuntimeError as exc:
                return self.build_response(task_name, False, error=str(exc))

            return self.build_response(task_name, True, normalized_case)

        if task_name == "generate_visit_recommendation":
            opportunity = payload.get("opportunity", {})
            top_k_cases = payload.get("top_k_cases", [])
            if not isinstance(opportunity, dict):
                return self.build_response(
                    task_name,
                    False,
                    error="Payload must include a dict field: opportunity",
                )
            if not isinstance(top_k_cases, list):
                return self.build_response(
                    task_name,
                    False,
                    error="Payload must include a list field: top_k_cases",
                )

            prompt = self._build_visit_recommendation_prompt(opportunity, top_k_cases)
            try:
                recommendation = self._call_json_task(
                    prompt,
                    self.VISIT_RECOMMENDATION_SCHEMA,
                    self._validate_visit_recommendation,
                )
            except RuntimeError as exc:
                return self.build_response(task_name, False, error=str(exc))

            return self.build_response(task_name, True, recommendation)

        return self.build_response(
            task_name,
            False,
            error=f"Unsupported Ollama task: {task_name}",
        )

    def _build_normalize_prompt(self, case: dict) -> str:
        """Build a constrained normalization prompt."""
        source_text = self._extract_source_text(case)
        return (
            "你是项目案例字段标准化助手。\n"
            "你的任务是从输入内容中提取并标准化字段。\n"
            "只允许输出 JSON。\n"
            "不要解释。\n"
            "不确定就留空，但如果项目名称已经出现明显工程词，请优先推断 business_type 和 keywords。\n"
            "location_district 只能填写真实行政区、县、镇、新区；像工业园区、产业园区、科技园区、开发区、高新区、经开区、保税区、产业基地、物流园区都不要填入 location_district。\n"
            "business_type 只能从以下枚举中选择其一，否则留空：高低压配电工程、变配电工程、配电安装工程、配电改造工程、供配电建设工程。\n"
            "keywords 请尽量提取 2-4 个高信息量短语，优先从项目名称和业务类型中提取；不要只返回泛词。\n"
            "输出字段固定为：\n"
            "{\n"
            '  "location_province": "",\n'
            '  "location_city": "",\n'
            '  "location_district": "",\n'
            '  "business_type": "",\n'
            '  "keywords": []\n'
            "}\n\n"
            f"输入文本：{source_text}\n"
            f"输入案例：{json.dumps(case, ensure_ascii=False)}"
        )

    def _build_visit_recommendation_prompt(self, opportunity: dict, top_k_cases: list[dict]) -> str:
        """Build a constrained prompt for visit recommendation generation."""
        condensed_cases = [self._condense_case(case) for case in top_k_cases[:3]]
        return (
            "你是售前拜访辅助系统，负责基于当前机会和相似案例生成可执行的拜访建议。\n"
            "只输出 JSON，不要解释，不要输出 markdown，不要输出 schema 外字段。\n"
            "如果信息不足，少说，不要乱猜。\n"
            "所有字段都必须是字符串数组，每个数组给出 2 到 4 条。\n"
            "建议必须贴合输入，避免空泛表达，例如不要写‘加强沟通’‘深入了解客户需求’‘持续跟进’。\n"
            "questions_to_ask: 只写拜访时要追问的关键信息，聚焦缺失信息、推进条件、决策约束。\n"
            "suggested_focus_points: 只写该重点讲什么案例、什么能力、什么经验，必须结合 opportunity 和 top_k_cases。\n"
            "next_actions: 只写拜访后的具体动作或拜访前必须准备的具体动作。\n"
            "risk_notes: 只写当前最可能影响推进或导致判断失真的风险点。\n"
            "输出 JSON schema：\n"
            "{\n"
            '  "questions_to_ask": [],\n'
            '  "suggested_focus_points": [],\n'
            '  "next_actions": [],\n'
            '  "risk_notes": []\n'
            "}\n\n"
            f"opportunity = {json.dumps(opportunity, ensure_ascii=False)}\n"
            f"top_k_cases = {json.dumps(condensed_cases, ensure_ascii=False)}"
        )

    def _extract_source_text(self, case: dict) -> str:
        custom_fields = case.get("custom_fields", {})
        if isinstance(custom_fields, dict):
            location_text = str(custom_fields.get("source_construction_location", "")).strip()
            if location_text:
                return location_text

        for key in ("location_city", "location_district", "project_name", "company_name"):
            value = str(case.get(key, "")).strip()
            if value:
                return value

        return json.dumps(case, ensure_ascii=False)

    def _condense_case(self, case: dict) -> dict:
        project_scale = case.get("project_scale")
        if not isinstance(project_scale, str):
            project_scale = self._infer_project_scale(case.get("project_amount", 0))

        keywords = case.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []

        matched_reasons = case.get("matched_reasons", [])
        if not isinstance(matched_reasons, list):
            matched_reasons = []

        risk_notes = case.get("risk_notes", [])
        if not isinstance(risk_notes, list):
            risk_notes = []

        return {
            "project_name": str(case.get("project_name", "")).strip(),
            "business_type": str(case.get("business_type", "")).strip(),
            "matched_reasons": [str(item).strip() for item in matched_reasons if str(item).strip()],
            "keywords": [str(item).strip() for item in keywords if str(item).strip()],
            "project_scale": project_scale,
            "risk_notes": [str(item).strip() for item in risk_notes if str(item).strip()],
        }

    def _infer_project_scale(self, project_amount: object) -> str:
        try:
            amount = int(float(str(project_amount).strip()))
        except (TypeError, ValueError):
            amount = 0

        if amount <= 300000:
            return "small"
        if amount <= 1000000:
            return "medium"
        return "large"

    def _call_json_task(self, prompt: str, schema: dict, validator) -> dict:
        response_data = self._generate_json_response(prompt, schema)
        return validator(response_data)

    def _generate_json_response(self, prompt: str, schema: dict) -> dict:
        """Call the local Ollama generate endpoint and parse JSON output."""
        url = f"{self.base_url}/api/generate"
        request_body = json.dumps(
            {
                "model": self.model_name,
                "prompt": prompt,
                "format": schema,
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ollama HTTP error: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Failed to reach Ollama at {self.base_url}: {exc.reason}"
            ) from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Invalid response from Ollama provider") from exc

        response_text = str(parsed.get("response", "")).strip()
        if not response_text:
            raise RuntimeError("Ollama returned an empty response")

        try:
            response_data = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned invalid JSON: {response_text}") from exc

        if not isinstance(response_data, dict):
            raise RuntimeError("Ollama returned non-object JSON")
        return response_data

    def _validate_normalized_case(self, response_data: object) -> dict:
        if not isinstance(response_data, dict):
            raise RuntimeError("Ollama returned non-object JSON")

        normalized_case = {
            "location_province": "",
            "location_city": "",
            "location_district": "",
            "business_type": "",
            "keywords": [],
        }

        for key in ("location_province", "location_city", "location_district", "business_type"):
            value = response_data.get(key, "")
            if value is None:
                value = ""
            if not isinstance(value, str):
                raise RuntimeError(f"Ollama returned invalid field type for {key}")
            normalized_case[key] = self._normalize_text_value(key, value)

        keywords = response_data.get("keywords", [])
        if keywords is None:
            keywords = []
        if not isinstance(keywords, list):
            raise RuntimeError("Ollama returned invalid field type for keywords")

        normalized_keywords: list[str] = []
        for item in keywords:
            if not isinstance(item, str):
                raise RuntimeError("Ollama returned a non-string keyword")
            cleaned = item.strip()
            if cleaned:
                normalized_keywords.append(cleaned)

        normalized_case["keywords"] = normalized_keywords
        return normalized_case

    def _validate_visit_recommendation(self, response_data: object) -> dict:
        if not isinstance(response_data, dict):
            raise RuntimeError("Ollama returned non-object JSON")

        normalized = {
            "questions_to_ask": [],
            "suggested_focus_points": [],
            "next_actions": [],
            "risk_notes": [],
        }
        for key in normalized:
            values = response_data.get(key, [])
            if not isinstance(values, list):
                normalized[key] = []
                continue

            cleaned_values: list[str] = []
            for item in values:
                if not isinstance(item, str):
                    continue
                cleaned = item.strip()
                if cleaned:
                    cleaned_values.append(cleaned)
            normalized[key] = cleaned_values[:4]

        return normalized

    def _normalize_text_value(self, key: str, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""

        if key == "location_province":
            cleaned = self._normalize_province(cleaned)
        elif key == "location_city":
            cleaned = self._normalize_city(cleaned)

        return cleaned

    def _normalize_province(self, value: str) -> str:
        cleaned = value.strip()
        replacements = {
            "省": "",
            "市": "",
            "壮族自治区": "",
            "回族自治区": "",
            "维吾尔自治区": "",
            "自治区": "",
            "特别行政区": "",
        }
        for suffix, replacement in replacements.items():
            if cleaned.endswith(suffix):
                cleaned = f"{cleaned[:-len(suffix)]}{replacement}".strip()
                break

        if cleaned not in self.VALID_PROVINCES:
            return ""
        return cleaned

    def _normalize_city(self, value: str) -> str:
        cleaned = value.strip()
        for suffix in ("市", "地区", "自治州", "盟"):
            if cleaned.endswith(suffix):
                return cleaned[:-len(suffix)].strip()
        return cleaned
