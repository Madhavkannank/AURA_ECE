import base64
import json
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
AUDIO_PATH = Path("sample_audio.wav")
OCR_IMAGE_PATH = Path("scripts/ocr_probe.png")


def print_result(name: str, ok: bool, details: dict):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")
    print(json.dumps(details, indent=2, ensure_ascii=True))


def main() -> int:
    # Health
    h = requests.get(f"{BASE}/health", timeout=10)
    if h.status_code != 200:
        print_result("Backend health", False, {"status_code": h.status_code, "body": h.text})
        return 1

    # Auth bootstrap + teacher login
    requests.post(f"{BASE}/auth/bootstrap", timeout=15)
    login = requests.post(
        f"{BASE}/auth/login",
        json={"user_id": "teacher-001", "password": "teacher123"},
        timeout=15,
    )
    if login.status_code != 200:
        print_result("Teacher login", False, {"status_code": login.status_code, "body": login.text})
        return 1

    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Create student for audio/video observations
    student = requests.post(
        f"{BASE}/students",
        headers=headers,
        json={
            "full_name": "Runtime Multimodal Student",
            "class_id": "runtime-multimodal",
            "parent_id": "parent-001",
            "parent_name": "Runtime Parent",
            "parent_language": "en",
        },
        timeout=20,
    )
    if student.status_code != 200:
        print_result("Create student", False, {"status_code": student.status_code, "body": student.text})
        return 1
    student_id = student.json().get("_id")

    # OCR test via notes upload (image)
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (900, 220), color="white")
        d = ImageDraw.Draw(img)
        d.text((20, 60), "Arjun shared blocks and counted to ten", fill="black")
        OCR_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        img.save(OCR_IMAGE_PATH, format="PNG")

        with OCR_IMAGE_PATH.open("rb") as f:
            ocr_resp = requests.post(
                f"{BASE}/notes/analyze-upload",
                headers=headers,
                data={
                    "owner_type": "teacher",
                    "owner_id": "teacher-001",
                    "embed_metadata": "false",
                },
                files={"file": (OCR_IMAGE_PATH.name, f, "image/png")},
                timeout=120,
            )

        ocr_ok = ocr_resp.status_code == 200
        ocr_json = ocr_resp.json() if ocr_ok else {"error": ocr_resp.text}
        print_result(
            "OCR image upload + extraction",
            ocr_ok,
            {
                "status_code": ocr_resp.status_code,
                "category": ocr_json.get("category") if ocr_ok else None,
                "summary": ocr_json.get("summary") if ocr_ok else None,
                "keywords": ocr_json.get("keywords") if ocr_ok else None,
                "text_preview_len": len(ocr_json.get("text_preview", "")) if ocr_ok else 0,
                "file_kind": ocr_json.get("file_kind") if ocr_ok else None,
            },
        )
    except Exception as exc:
        print_result("OCR image upload + extraction", False, {"error": str(exc)})

    # Audio test via observations/process
    if not AUDIO_PATH.exists():
        print_result("Audio observation processing", False, {"error": "sample_audio.wav not found"})
    else:
        audio_b64 = base64.b64encode(AUDIO_PATH.read_bytes()).decode("utf-8")
        audio_resp = requests.post(
            f"{BASE}/observations/process",
            headers=headers,
            json={
                "student_id": student_id,
                "text": None,
                "audio_base64": audio_b64,
                "audio_mime_type": "audio/wav",
            },
            timeout=180,
        )
        audio_ok = audio_resp.status_code == 200
        audio_json = audio_resp.json() if audio_ok else {"error": audio_resp.text}
        print_result(
            "Audio observation processing",
            audio_ok,
            {
                "status_code": audio_resp.status_code,
                "domain": audio_json.get("domain") if audio_ok else None,
                "confidence": audio_json.get("confidence") if audio_ok else None,
                "tags": audio_json.get("tags") if audio_ok else None,
                "raw_text_len": len(audio_json.get("raw_text", "")) if audio_ok else 0,
            },
        )

    # Video test via observations/video-process (using lightweight bytes)
    fake_video_b64 = base64.b64encode(b"not-real-video").decode("utf-8")
    video_resp = requests.post(
        f"{BASE}/observations/video-process",
        headers=headers,
        json={
            "student_id": student_id,
            "video_base64": fake_video_b64,
            "video_mime_type": "video/mp4",
            "teacher_note": "Student attempted puzzle and accepted peer help.",
        },
        timeout=120,
    )
    video_ok = video_resp.status_code == 200
    video_json = video_resp.json() if video_ok else {"error": video_resp.text}
    print_result(
        "Video observation processing",
        video_ok,
        {
            "status_code": video_resp.status_code,
            "modality": video_json.get("modality") if video_ok else None,
            "timeline_count": len(video_json.get("behavior_timeline", [])) if video_ok else 0,
            "behavioral_insights": video_json.get("behavioral_insights") if video_ok else None,
            "video_meta": video_json.get("video_meta") if video_ok else None,
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
