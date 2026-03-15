import json
from typing import Any

from groq import Groq
from groq import BadRequestError, GroqError

from ..config import get_settings


class GroqService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.groq_api_key) if self.settings.groq_api_key else None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def chat_json(self, prompt: str, model: str) -> dict[str, Any]:
        if not self.client:
            return {}
        try:
            completion = self.client.chat.completions.create(
                model=model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content or "{}"
            return json.loads(content)
        except (BadRequestError, GroqError, json.JSONDecodeError, KeyError, TypeError):
            return {}

    def chat_text(self, prompt: str, model: str) -> str:
        if not self.client:
            return ""
        try:
            completion = self.client.chat.completions.create(
                model=model,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": "You are an education assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
            return completion.choices[0].message.content or ""
        except (BadRequestError, GroqError, KeyError, TypeError):
            return ""


_groq = GroqService()


def get_groq_service() -> GroqService:
    return _groq
