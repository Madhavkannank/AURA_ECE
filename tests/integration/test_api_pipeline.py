from __future__ import annotations

import os
import time
import uuid

import pytest
import requests

BASE_URL = os.getenv("AURA_API_BASE", "http://localhost:8000")


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _healthcheck() -> bool:
    try:
        response = requests.get(_url("/health"), timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="module")
def teacher_token() -> str:
    if not _healthcheck():
        pytest.skip("Backend is not running. Start API server before running integration tests.")

    try:
        requests.post(_url("/auth/bootstrap"), timeout=15)
        response = requests.post(
            _url("/auth/login"),
            json={"user_id": "teacher-001", "password": "teacher123"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.RequestException as exc:
        pytest.skip(f"Auth bootstrap/login unavailable for integration tests: {exc}")


@pytest.fixture(scope="module")
def parent_token() -> str:
    if not _healthcheck():
        pytest.skip("Backend is not running. Start API server before running integration tests.")

    try:
        requests.post(_url("/auth/bootstrap"), timeout=15)
        response = requests.post(
            _url("/auth/login"),
            json={"user_id": "parent-001", "password": "parent123"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.RequestException as exc:
        pytest.skip(f"Parent auth unavailable for integration tests: {exc}")


def _teacher_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _parent_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_full_teacher_to_parent_pipeline(teacher_token: str, parent_token: str) -> None:
    suffix = uuid.uuid4().hex[:8]

    create_student = requests.post(
        _url("/students"),
        json={
            "full_name": f"Integration Student {suffix}",
            "class_id": "integration-class",
            "parent_id": "parent-001",
            "parent_name": "Integration Parent",
            "parent_language": "en",
        },
        headers=_teacher_headers(teacher_token),
        timeout=20,
    )
    create_student.raise_for_status()
    student = create_student.json()
    student_id = student["_id"]

    obs_response = requests.post(
        _url("/observations/process"),
        json={
            "student_id": student_id,
            "text": "Student solved a counting puzzle, shared toys, and described a short story clearly.",
        },
        headers=_teacher_headers(teacher_token),
        timeout=60,
    )
    obs_response.raise_for_status()
    observation = obs_response.json()
    assert observation["student_id"] == student_id
    assert observation["domain"] in {
        "Cognitive Development",
        "Social-Emotional Development",
        "Physical Development",
        "Language Development",
        "Uncategorized",
    }

    insights_response = requests.get(
        _url(f"/students/{student_id}/insights"),
        headers=_teacher_headers(teacher_token),
        timeout=30,
    )
    insights_response.raise_for_status()
    insights = insights_response.json()
    assert "trends" in insights

    report_response = requests.post(
        _url(f"/reports/generate/{student_id}"),
        json={"period": "weekly"},
        headers=_teacher_headers(teacher_token),
        timeout=90,
    )
    report_response.raise_for_status()
    report = report_response.json()
    report_id = report["_id"]
    assert isinstance(report.get("activity_suggestions", []), list)

    approve_response = requests.post(
        _url(f"/reports/{report_id}/approve"),
        json={"approved": True},
        headers=_teacher_headers(teacher_token),
        timeout=30,
    )
    approve_response.raise_for_status()
    approved = approve_response.json()
    assert approved["approved"] is True

    parent_reports = requests.get(
        _url("/parents/parent-001/reports"),
        headers=_parent_headers(parent_token),
        timeout=30,
    )
    parent_reports.raise_for_status()
    reports = parent_reports.json()
    assert any(r.get("_id") == report_id for r in reports)


def test_report_cycle_and_scheduler_status(teacher_token: str) -> None:
    status_response = requests.get(
        _url("/reports/scheduler-status"),
        headers=_teacher_headers(teacher_token),
        timeout=10,
    )
    status_response.raise_for_status()
    status = status_response.json()
    assert "enabled" in status
    assert "period" in status

    cycle_response = requests.post(
        _url("/reports/run-cycle"),
        json={"period": "weekly"},
        headers=_teacher_headers(teacher_token),
        timeout=120,
    )
    cycle_response.raise_for_status()
    cycle = cycle_response.json()
    assert cycle["status"] == "ok"
    assert "students_processed" in cycle
    assert "reports_created" in cycle
    assert "reports_skipped_recent" in cycle


def test_video_observation_and_class_report_views(teacher_token: str, parent_token: str) -> None:
    suffix = uuid.uuid4().hex[:8]

    create_student = requests.post(
        _url("/students"),
        json={
            "full_name": f"Video Student {suffix}",
            "class_id": "integration-class-video",
            "parent_id": "parent-001",
            "parent_name": "Integration Parent",
            "parent_language": "en",
        },
        headers=_teacher_headers(teacher_token),
        timeout=20,
    )
    create_student.raise_for_status()
    student = create_student.json()
    student_id = student["_id"]

    # Byte payload is intentionally lightweight; service handles unavailable/invalid stream with fallback timeline.
    fake_video_b64 = "bm90LXJlYWwtdmlkZW8="
    video_obs = requests.post(
        _url("/observations/video-process"),
        json={
            "student_id": student_id,
            "video_base64": fake_video_b64,
            "video_mime_type": "video/mp4",
            "teacher_note": "Student worked on puzzle activity and interacted with peers.",
        },
        headers=_teacher_headers(teacher_token),
        timeout=90,
    )
    video_obs.raise_for_status()
    video_data = video_obs.json()
    assert video_data.get("modality") == "video"
    assert isinstance(video_data.get("behavior_timeline", []), list)

    class_report_resp = requests.post(
        _url("/reports/class/generate/integration-class-video"),
        json={"period": "weekly"},
        headers=_teacher_headers(teacher_token),
        timeout=120,
    )
    class_report_resp.raise_for_status()
    class_report = class_report_resp.json()
    assert class_report.get("class_id") == "integration-class-video"
    assert "class_development_summary" in class_report

    teacher_view_resp = requests.post(
        _url("/reports/class/integration-class-video/view"),
        json={"role": "teacher", "period": "weekly"},
        headers=_teacher_headers(teacher_token),
        timeout=30,
    )
    teacher_view_resp.raise_for_status()
    teacher_view = teacher_view_resp.json()
    assert teacher_view.get("role") == "teacher"

    parent_view_resp = requests.post(
        _url("/reports/class/integration-class-video/view"),
        json={"role": "parent", "period": "weekly", "parent_id": "parent-001"},
        headers=_parent_headers(parent_token),
        timeout=30,
    )
    parent_view_resp.raise_for_status()
    parent_view = parent_view_resp.json()
    assert parent_view.get("role") == "parent"
    assert isinstance(parent_view.get("children", []), list)

    student_view_resp = requests.post(
        _url("/reports/class/integration-class-video/view"),
        json={"role": "student", "period": "weekly", "student_id": student_id},
        headers=_teacher_headers(teacher_token),
        timeout=30,
    )
    student_view_resp.raise_for_status()
    student_view = student_view_resp.json()
    assert student_view.get("role") == "student"
    assert "next_goal" in student_view


def test_system_self_test_endpoint_contract() -> None:
    if not _healthcheck():
        pytest.skip("Backend is not running. Start API server before running integration tests.")

    response = requests.get(_url("/system/self-test?run_live_models=false"), timeout=30)
    assert response.status_code in {200, 503}

    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert "checks" in payload
    assert "mongo" in payload["checks"]
    assert "scheduler" in payload["checks"]
