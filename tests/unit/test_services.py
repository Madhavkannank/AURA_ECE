from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from backend.app.services.reasoning_service import ReasoningService, VALID_DOMAINS
from backend.app.services.privacy_service import PrivacyService
from backend.app.services.notes_service import NotesService
from backend.app.services.auth_service import AuthService
from backend.app.services.input_engine import InputEngine
from backend.app.config import Settings


def test_reasoning_heuristic_classification():
    service = ReasoningService()

    # Cognitive
    res = service._heuristic_classification("The student solved a difficult puzzle and was counting numbers.")
    assert res["domain"] == "Cognitive Development"
    assert res["confidence"] >= 0.5
    assert "problem-solving" in res["tags"]

    # Social-Emotional
    res = service._heuristic_classification("Shared crayons with a friend and waited for turn calmly.")
    assert res["domain"] == "Social-Emotional Development"
    assert "peer-interaction" in res["tags"]

    # Physical
    res = service._heuristic_classification("Demonstrated great balance while jumping and running.")
    assert res["domain"] == "Physical Development"
    assert "motor-skills" in res["tags"]

    # Language
    res = service._heuristic_classification("Spoke in complete sentences with broad vocabulary during story time.")
    assert res["domain"] == "Language Development"
    assert "communication" in res["tags"]

    # Uncategorized fallback
    res = service._heuristic_classification("Routine day.")
    assert res["domain"] == "Uncategorized"


def test_reasoning_trend_analysis():
    service = ReasoningService()
    now = datetime.now(timezone.utc)

    # 1 observation in first half, 2 high-confidence in second half -> Excelling
    obs = [
        {"domain": "Cognitive Development", "confidence": 0.5, "timestamp": now - timedelta(days=20)},
        {"domain": "Cognitive Development", "confidence": 0.9, "timestamp": now - timedelta(days=5)},
        {"domain": "Cognitive Development", "confidence": 0.95, "timestamp": now - timedelta(days=2)},
    ]

    trends = service.analyze_trends(obs)
    assert len(trends) == len(VALID_DOMAINS)

    cog_trend = next(t for t in trends if t["domain"] == "Cognitive Development")
    assert cog_trend["trend"] == "Excelling"
    assert cog_trend["observation_count"] == 3


def test_privacy_masking():
    service = PrivacyService()

    text = "Teacher contact: john.doe@school.edu, phone: +1 (555) 234-5678, SSN: 123-45-6789."
    masked = service.mask_text(text)

    assert "john.doe@school.edu" not in masked["text"]
    assert "123-45-6789" not in masked["text"]
    assert "[EMAIL]" in masked["text"] or "[SSN]" in masked["text"] or "<" in masked["text"] or "*" in masked["text"]


def test_notes_file_kind_detection():
    service = NotesService()

    assert service.detect_file_kind("child_notes.pdf", "application/pdf") == "document"
    assert service.detect_file_kind("observations.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == "document"
    assert service.detect_file_kind("playground.mp4", "video/mp4") == "video"
    assert service.detect_file_kind("voice_memo.wav", "audio/wav") == "audio"
    assert service.detect_file_kind("drawing.jpg", "image/jpeg") == "image"
    assert service.detect_file_kind("unknown.xyz", "application/octet-stream") == "other"


def test_auth_service_hashing_and_tokens():
    auth = AuthService()

    hashed = auth.hash_password("mypassword123")
    assert auth.verify_password("mypassword123", hashed)
    assert not auth.verify_password("wrongpassword", hashed)

    user = {
        "user_id": "teacher-test",
        "role": "teacher",
        "parent_id": None,
    }
    token = auth.create_access_token(user)
    assert token

    decoded = auth.decode_token(token)
    assert decoded["sub"] == "teacher-test"
    assert decoded["role"] == "teacher"


def test_input_engine_audio_error_handling():
    engine = InputEngine()

    # Empty audio
    assert engine.transcribe_audio("") == ""

    # Malformed base64
    res = engine.transcribe_audio("not_a_valid_base64_payload!@#$%^")
    assert "malformed" in res.lower() or "unavailable" in res.lower()


def test_report_service_generation_fallback():
    from backend.app.services.report_service import ReportService
    service = ReportService()

    student = {
        "_id": "507f1f77bcf86cd799439011",
        "full_name": "Maya Lin",
        "class_id": "class-1",
        "parent_language": "es",
    }
    observations = [
        {
            "domain": "Cognitive Development",
            "confidence": 0.8,
            "corrected_text": "Counted up to 20 blocks enthusiastically.",
            "timestamp": datetime.now(timezone.utc) - timedelta(days=2),
        }
    ]

    report = service.generate_reports(
        student=student,
        observations=observations,
        period="weekly",
        include_trends=True,
        include_activity_suggestions=True,
    )

    assert report["student_id"] == "507f1f77bcf86cd799439011"
    assert report["period"] == "weekly"
    assert "teacher_assessment" in report
    assert "Maya Lin" in report["teacher_assessment"]
    assert "parent_summary" in report
    assert report["approved"] is False


def test_settings_validation():
    # Dev mode allows default URI
    dev_settings = Settings(app_env="dev", mongo_uri="mongodb://localhost:27017")
    assert dev_settings.app_env == "dev"

    # Non-dev mode enforces credentials in MONGO_URI
    with pytest.raises(ValueError, match="credentials"):
        Settings(app_env="prod", mongo_uri="mongodb://localhost:27017")

