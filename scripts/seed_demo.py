import os
import time
from typing import Any

import requests


API_BASE = os.getenv("AURA_API_BASE", "http://localhost:8000")


def post(path: str, payload: dict[str, Any], token: str | None = None) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.post(f"{API_BASE}{path}", json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    return response.json()


def get(path: str, token: str) -> Any:
    response = requests.get(f"{API_BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=120)
    response.raise_for_status()
    return response.json()


def main() -> None:
    print("Bootstrapping users...")
    post("/auth/bootstrap", {})

    print("Logging in teacher...")
    auth = post("/auth/login", {"user_id": "teacher-001", "password": "teacher123"})
    token = auth["access_token"]

    print("Creating students...")
    students = []
    payloads = [
        {
            "full_name": "Mia Johnson",
            "class_id": "class-a",
            "parent_id": "parent-001",
            "parent_name": "Alex Johnson",
            "parent_language": "es",
        },
        {
            "full_name": "Noah Patel",
            "class_id": "class-a",
            "parent_id": "parent-001",
            "parent_name": "Alex Johnson",
            "parent_language": "fr",
        },
    ]
    for payload in payloads:
        students.append(post("/students", payload, token))

    print("Submitting observations...")
    observations = [
        "Mia focused on sorting shapes by color and completed a new puzzle with minimal help.",
        "Mia shared crayons and calmly waited for her turn during group art activity.",
        "Noah used full sentences to describe his drawing and asked thoughtful questions.",
        "Noah improved balance on the stepping path and showed stronger grip while cutting paper.",
    ]

    for idx, obs in enumerate(observations):
        student = students[0] if idx < 2 else students[1]
        post(
            "/observations/process",
            {
                "student_id": student["_id"],
                "text": obs,
            },
            token,
        )
        time.sleep(0.15)

    print("Generating and approving reports...")
    for student in students:
        report = post(f"/reports/generate/{student['_id']}", {"period": "weekly"}, token)
        post(f"/reports/{report['_id']}/approve", {"approved": True}, token)

    print("Demo seed complete. Login credentials:")
    print("Teacher: teacher-001 / teacher123")
    print("Parent: parent-001 / parent123")
    parent_reports = get("/parents/parent-001/reports", token)
    print(f"Approved reports available: {len(parent_reports)}")


if __name__ == "__main__":
    main()
