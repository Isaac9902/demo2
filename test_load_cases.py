import json

cases = []
with open("data/project_cases.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))

print(f"共加载 {len(cases)} 条项目案例")

first_case = cases[0]
print(first_case["project_name"])
print(first_case["location_city"], first_case["location_district"])
print(first_case["project_amount"])