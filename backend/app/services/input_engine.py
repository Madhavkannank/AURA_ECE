import base64
import os
import tempfile
from typing import Any

from .groq_client import get_groq_service


class InputEngine:
    def __init__(self) -> None:
        self.groq = get_groq_service()

    def transcribe_audio(self, audio_b64: str, mime_type: str = "audio/wav") -> str:
        if not audio_b64:
            return ""
        raw = base64.b64decode(audio_b64)
        if not self.groq.enabled:
            return "Transcription unavailable: missing GROQ_API_KEY."

        suffix = ".wav" if "wav" in mime_type else ".mp3"
        model_candidates = [
            self.groq.settings.groq_whisper_model,
            "whisper-large-v3",
            "whisper-large-v3-turbo",
            "distil-whisper-large-v3-en",
        ]
        # Preserve order while removing duplicates.
        unique_models: list[str] = []
        for model in model_candidates:
            if model and model not in unique_models:
                unique_models.append(model)

        last_error = "unknown"
        temp_path = ""
        try:
            fd, temp_path = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, "wb") as temp_file:
                temp_file.write(raw)

            for model in unique_models:
                try:
                    with open(temp_path, "rb") as audio_file:
                        response = self.groq.client.audio.transcriptions.create(
                            model=model,
                            file=audio_file,
                            temperature=0,
                            prompt="Early childhood classroom observation with names and developmental details.",
                        )
                    text = (getattr(response, "text", "") or "").strip()
                    if text:
                        return text
                except Exception as exc:
                    last_error = str(exc)
                    continue
        except Exception as exc:
            last_error = str(exc)
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        return f"Transcription unavailable for provided audio ({last_error[:160]})."

    def correct_transcription(self, text: str, roster_names: list[str], target_name: str) -> str:
        if not text:
            return ""
        prompt = (
            "Correct the classroom observation transcription. Keep meaning unchanged, fix grammar and likely speech-to-text errors, "
            "and resolve student-name ambiguity using this roster: "
            f"{roster_names}. The observation is for student: {target_name}. "
            f"Return JSON with key corrected_text. Input text: {text}"
        )
        model = self.groq.settings.groq_light_model
        data: dict[str, Any] = self.groq.chat_json(prompt, model)
        corrected = data.get("corrected_text") if isinstance(data, dict) else None
        return corrected.strip() if corrected else text.strip()


input_engine = InputEngine()
