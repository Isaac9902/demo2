import json
from copy import deepcopy

from pipeline.parse_opportunity_note import build_empty_opportunity_record, build_review_flags



def make_record(**overrides: object) -> dict:
    record = build_empty_opportunity_record(str(overrides.get("raw_input", "测试机会记录")))
    record.update(
        {
            "company_name": "某自动化设备公司",
            "contact_name": "张工",
            "contact_phone": "13800138000",
            "contact_role": "设备经理",
            "industry": "自动化设备",
            "location_province": "广东",
            "location_city": "深圳",
            "location_district": "宝安区",
            "business_type_guess": "配电改造工程",
            "budget_hint": "80万",
            "core_needs": ["配电改造"],
            "concerns": ["交付周期"],
            "current_stage": "new",
        }
    )
    record.update(overrides)
    return record



def evaluate_case(case_name: str, record: dict, expected_needs_review: bool, expected_reasons: list[str]) -> bool:
    actual_needs_review, actual_reasons = build_review_flags(record)
    passed = actual_needs_review == expected_needs_review and all(
        reason in actual_reasons for reason in expected_reasons
    )
    print(f"\n{case_name}")
    print("输入关键字段:")
    print(
        json.dumps(
            {
                "current_stage": record.get("current_stage"),
                "company_name": record.get("company_name"),
                "contact_name": record.get("contact_name"),
                "contact_phone": record.get("contact_phone"),
                "business_type_guess": record.get("business_type_guess"),
                "core_needs": record.get("core_needs"),
                "raw_input": record.get("raw_input"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"实际 needs_review: {actual_needs_review}")
    print(f"实际 review_reasons: {actual_reasons}")
    print(f"预期 needs_review: {expected_needs_review}")
    print(f"预期 review_reasons: {expected_reasons}")
    print(f"结果: {'PASS' if passed else 'FAIL'}")
    return passed



def main() -> None:
    cases = [
        (
            "Case A",
            make_record(),
            False,
            [],
        ),
        (
            "Case B",
            make_record(contact_phone=""),
            True,
            ["contact_phone missing"],
        ),
        (
            "Case C",
            make_record(company_name=""),
            True,
            ["company_name missing"],
        ),
        (
            "Case D",
            make_record(current_stage="archived", contact_name="", contact_phone=""),
            False,
            [],
        ),
        (
            "Case E",
            make_record(current_stage="archived", company_name="", contact_name="", contact_phone=""),
            True,
            ["company_name missing"],
        ),
        (
            "Case F",
            make_record(
                raw_input="帮忙看看",
                business_type_guess="",
                core_needs=[],
                concerns=[],
            ),
            True,
            ["project intent weak"],
        ),
    ]

    all_passed = True
    for case_name, record, expected_needs_review, expected_reasons in cases:
        if not evaluate_case(case_name, deepcopy(record), expected_needs_review, expected_reasons):
            all_passed = False

    print("\n测试总结:")
    print("ALL PASS" if all_passed else "HAS FAILURES")


if __name__ == "__main__":
    main()
