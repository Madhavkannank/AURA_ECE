import base64
import json
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"


def read_b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")


def main() -> None:
    out: dict = {}

    requests.post(f"{BASE}/auth/bootstrap", timeout=20)
    login = requests.post(
        f"{BASE}/auth/login",
        json={"user_id": "teacher-001", "password": "teacher123"},
        timeout=20,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    out["auth"] = "ok"

    student = requests.post(
        f"{BASE}/students",
        headers=headers,
        json={
            "full_name": "Model Test Student",
            "class_id": "model-test-class",
            "parent_id": "parent-001",
            "parent_name": "Model Parent",
            "parent_language": "en",
        },
        timeout=30,
    )
    student.raise_for_status()
    student_id = student.json()["_id"]
    out["student_id"] = student_id

    ocr_path = "scripts/ocr_probe.png"
    with Path(ocr_path).open("rb") as f:
        files = {"file": (Path(ocr_path).name, f, "image/png")}
        data = {"owner_type": "teacher", "owner_id": "teacher-001", "embed_metadata": "true"}
        ocr = requests.post(f"{BASE}/notes/analyze-upload", headers=headers, files=files, data=data, timeout=60)
    ocr.raise_for_status()
    ocr_json = ocr.json()
    out["ocr_note"] = {
        "status": "ok",
        "file": ocr_path,
        "category": ocr_json.get("category"),
        "keywords": (ocr_json.get("keywords") or [])[:5],
    }

    audio_path = "scripts/tts_probe.wav"
    audio = requests.post(
        f"{BASE}/observations/process",
        headers=headers,
        json={
            "student_id": student_id,
            "audio_base64": read_b64(audio_path),
            "audio_mime_type": "audio/wav",
        },
        timeout=120,
    )
    audio.raise_for_status()
    audio_json = audio.json()
    out["audio_observation"] = {
        "status": "ok",
        "file": audio_path,
        "domain": audio_json.get("domain"),
        "confidence": audio_json.get("confidence"),
    }

    video_path = "scripts/real_probe.mp4"
    video = requests.post(
        f"{BASE}/observations/video-process",
        headers=headers,
        json={
            "student_id": student_id,
            "video_base64": read_b64(video_path),
            "video_mime_type": "video/mp4",
            "teacher_note": "Terminal model test run",
        },
        timeout=180,
    )
    video.raise_for_status()
    video_json = video.json()
    out["video_observation"] = {
        "status": "ok",
        "file": video_path,
        "timeline_count": len(video_json.get("behavior_timeline") or []),
        "insights_count": len(video_json.get("insights") or []),
    }

    meta_path = "scripts/metadata_probe.txt"
    with Path(meta_path).open("rb") as f:
        files = {"file": (Path(meta_path).name, f, "text/plain")}
        data = {"owner_type": "teacher", "owner_id": "teacher-001", "embed_metadata": "true"}
        meta = requests.post(f"{BASE}/notes/analyze-upload", headers=headers, files=files, data=data, timeout=60)
    meta.raise_for_status()
    meta_json = meta.json()
    query = (meta_json.get("keywords") or ["classroom"])[0]
    search = requests.get(
        f"{BASE}/notes/search",
        headers=headers,
        params={"q": query, "owner_type": "teacher", "owner_id": "teacher-001"},
        timeout=30,
    )
    search.raise_for_status()
    search_json = search.json()
    out["metadata_search"] = {
        "status": "ok",
        "file": meta_path,
        "query": query,
        "result_count": len(search_json) if isinstance(search_json, list) else 0,
    }

    report = requests.post(
        f"{BASE}/reports/generate/{student_id}",
        headers=headers,
        json={
            "period": "weekly",
            "include_trends": True,
            "include_activity_suggestions": True,
            "include_parent_translation": True,
        },
        timeout=120,
    )
    report.raise_for_status()
    report_json = report.json()
    out["report_generation"] = {
        "status": "ok",
        "report_id": report_json.get("_id"),
        "period": report_json.get("period"),
        "approved": report_json.get("approved"),
    }

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
