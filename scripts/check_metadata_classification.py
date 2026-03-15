import json
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"


def main() -> int:
    # Health check
    health = requests.get(f"{BASE}/health", timeout=10)
    if health.status_code != 200:
        print(json.dumps({"ok": False, "step": "health", "status_code": health.status_code, "body": health.text}, indent=2))
        return 1

    # Bootstrap/login
    requests.post(f"{BASE}/auth/bootstrap", timeout=15)
    login = requests.post(
        f"{BASE}/auth/login",
        json={"user_id": "teacher-001", "password": "teacher123"},
        timeout=15,
    )
    if login.status_code != 200:
        print(json.dumps({"ok": False, "step": "login", "status_code": login.status_code, "body": login.text}, indent=2))
        return 1

    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Prepare a deterministic test document
    note_text = (
        "Student completed counting blocks activity, practiced number recognition, "
        "and demonstrated fine motor control during shape tracing."
    )
    note_path = Path("scripts/metadata_probe.txt")
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(note_text, encoding="utf-8")

    with note_path.open("rb") as f:
        upload = requests.post(
            f"{BASE}/notes/analyze-upload",
            headers=headers,
            data={
                "owner_type": "teacher",
                "owner_id": "teacher-001",
                "embed_metadata": "true",
            },
            files={"file": (note_path.name, f, "text/plain")},
            timeout=120,
        )

    if upload.status_code != 200:
        print(json.dumps({"ok": False, "step": "upload", "status_code": upload.status_code, "body": upload.text}, indent=2))
        return 1

    note = upload.json()
    keywords = note.get("keywords", [])
    category = note.get("category")
    metadata_embedded = note.get("metadata_embedded")
    note_id = note.get("_id")

    if not keywords:
        print(json.dumps({"ok": False, "step": "classification", "reason": "no keywords returned", "note": note}, indent=2))
        return 1

    # Verify keyword-driven retrieval via search endpoint
    search_term = keywords[0]
    search = requests.get(
        f"{BASE}/notes/search",
        headers=headers,
        params={
            "q": search_term,
            "owner_type": "teacher",
            "owner_id": "teacher-001",
        },
        timeout=60,
    )

    if search.status_code != 200:
        print(json.dumps({"ok": False, "step": "search", "status_code": search.status_code, "body": search.text}, indent=2))
        return 1

    results = search.json()
    found = any(item.get("_id") == note_id for item in results)

    output = {
        "ok": True,
        "classification": {
            "note_id": note_id,
            "category": category,
            "keywords": keywords,
            "metadata_embedded": metadata_embedded,
            "file_name": note.get("file_name"),
            "file_kind": note.get("file_kind"),
        },
        "search_verification": {
            "search_term": search_term,
            "matched_note": found,
            "results_count": len(results),
        },
        "note": "For text files, metadata embedding into file is expected to be false; classification/search should still work via stored DB metadata.",
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
