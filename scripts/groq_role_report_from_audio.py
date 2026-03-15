import base64
import json
import os
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"
AUDIO_PATH = Path("scripts/tts_probe.wav")
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def load_env_value(key: str, default: str = "") -> str:
    value = os.getenv(key)
    if value:
        return value

    env_path = Path(".env")
    if not env_path.exists():
        return default

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return default


def get_teacher_token() -> str:
    requests.post(f"{BASE_URL}/auth/bootstrap", timeout=20)
    login = requests.post(
        f"{BASE_URL}/auth/login",
        json={"user_id": "teacher-001", "password": "teacher123"},
        timeout=20,
    )
    login.raise_for_status()
    return login.json()["access_token"]


def create_test_student(token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    student = requests.post(
        f"{BASE_URL}/students",
        headers=headers,
        json={
            "full_name": "Groq Audio Report Student",
            "class_id": "groq-audio-class",
            "parent_id": "parent-001",
            "parent_name": "Groq Parent",
            "parent_language": "en",
        },
        timeout=30,
    )
    student.raise_for_status()
    return student.json()


def run_audio_model(token: str, student_id: str, audio_path: Path) -> dict:
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    headers = {"Authorization": f"Bearer {token}"}
    audio_b64 = base64.b64encode(audio_path.read_bytes()).decode("utf-8")
    obs = requests.post(
        f"{BASE_URL}/observations/process",
        headers=headers,
        json={
            "student_id": student_id,
            "audio_base64": audio_b64,
            "audio_mime_type": "audio/wav",
        },
        timeout=180,
    )
    obs.raise_for_status()
    return obs.json()


def build_prompt(observation: dict) -> str:
    payload = {
        "domain": observation.get("domain"),
        "confidence": observation.get("confidence"),
        "tags": observation.get("tags"),
        "raw_text": observation.get("raw_text"),
        "corrected_text": observation.get("corrected_text"),
    }

    return (
        "You are an early-childhood education reporting assistant. "
        "Create ONE report with exactly 3 top-level sections titled: STUDENT, TEACHER, PARENT.\n\n"
        "For STUDENT section include:\n"
        "- strengths in child-friendly language\n"
        "- one growth area phrased positively\n"
        "- one small next-step activity the child can do\n\n"
        "For TEACHER section include:\n"
        "- objective evidence summary from observation\n"
        "- interpretation tied to developmental domain and confidence\n"
        "- two concrete classroom action steps\n"
        "- one monitoring checkpoint for next observation\n\n"
        "For PARENT section include:\n"
        "- plain-language summary of today's observation\n"
        "- two at-home reinforcement activities\n"
        "- one communication note for home-school continuity\n\n"
        "Differentiate tone for each section: child-friendly for STUDENT, professional for TEACHER, supportive plain language for PARENT. "
        "Do not repeat identical lines across sections.\n\n"
        f"Observation JSON:\n{json.dumps(payload, indent=2)}"
    )


def call_groq(prompt: str, system_message: str = "You create structured education reports.") -> str:
    groq_key = load_env_value("GROQ_API_KEY", "")
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY is missing")

    model = load_env_value("GROQ_REASONING_MODEL", DEFAULT_GROQ_MODEL)
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def maybe_translate_report(report_text: str) -> None:
    try:
        wants_translation = input("\nDo you need this report in another language? (y/n): ").strip().lower()
    except EOFError:
        return

    if wants_translation not in {"y", "yes"}:
        return

    try:
        target_language = input("Enter target language (for example: Hindi, Tamil, Spanish): ").strip()
    except EOFError:
        return

    if not target_language:
        print("No language entered. Skipping translation.")
        return

    translate_prompt = (
        f"Translate the following report into {target_language}. "
        "Keep the same three section headers exactly as: STUDENT, TEACHER, PARENT. "
        "Preserve meaning and tone for each audience.\n\n"
        f"Report:\n{report_text}"
    )
    translated = call_groq(
        prompt=translate_prompt,
        system_message="You translate education reports accurately while preserving structure and tone.",
    )
    print(f"\n=== TRANSLATED REPORT ({target_language.upper()}) ===")
    print(translated)


def main() -> int:
    try:
        token = get_teacher_token()
        student = create_test_student(token)
        observation = run_audio_model(token, student["_id"], AUDIO_PATH)
        prompt = build_prompt(observation)
        report_text = call_groq(prompt)

        print("=== AUDIO MODEL OUTPUT USED FOR GROQ ===")
        print(json.dumps(
            {
                "student_id": student["_id"],
                "domain": observation.get("domain"),
                "confidence": observation.get("confidence"),
                "tags": observation.get("tags"),
                "corrected_text": observation.get("corrected_text"),
            },
            indent=2,
        ))
        print("\n=== DIFFERENTIATED SINGLE REPORT (STUDENT / TEACHER / PARENT) ===")
        print(report_text)
        maybe_translate_report(report_text)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
