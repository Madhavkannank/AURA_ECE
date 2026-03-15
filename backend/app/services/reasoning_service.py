from datetime import datetime, timedelta, timezone
from typing import Any

from .groq_client import get_groq_service


VALID_DOMAINS = {
    "Cognitive Development",
    "Social-Emotional Development",
    "Physical Development",
    "Language Development",
}


class ReasoningService:
    def __init__(self) -> None:
        self.groq = get_groq_service()

    def _as_utc(self, value: Any) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def classify_observation(self, text: str) -> dict[str, Any]:
        if not text:
            return {"domain": "Uncategorized", "confidence": 0.0, "tags": []}

        prompt = (
            "Classify this early-childhood observation into one domain: Cognitive Development, "
            "Social-Emotional Development, Physical Development, or Language Development. "
            "Return JSON with keys domain, confidence (0-1), and tags (max 4). Observation: "
            f"{text}"
        )

        data = self.groq.chat_json(prompt, self.groq.settings.groq_light_model)
        if data:
            domain = data.get("domain", "Uncategorized")
            if domain not in VALID_DOMAINS:
                domain = "Uncategorized"
            return {
                "domain": domain,
                "confidence": float(data.get("confidence", 0.7)),
                "tags": list(data.get("tags", []))[:4],
            }

        return self._heuristic_classification(text)

    def _heuristic_classification(self, text: str) -> dict[str, Any]:
        lower = text.lower()
        if any(word in lower for word in ["count", "puzzle", "memory", "problem", "sort"]):
            return {"domain": "Cognitive Development", "confidence": 0.65, "tags": ["problem-solving"]}
        if any(word in lower for word in ["shared", "friend", "emotion", "calm", "turn"]):
            return {"domain": "Social-Emotional Development", "confidence": 0.65, "tags": ["peer-interaction"]}
        if any(word in lower for word in ["jump", "run", "grip", "balance", "fine motor"]):
            return {"domain": "Physical Development", "confidence": 0.65, "tags": ["motor-skills"]}
        if any(word in lower for word in ["spoke", "sentence", "vocabulary", "story", "phonics"]):
            return {"domain": "Language Development", "confidence": 0.65, "tags": ["communication"]}
        return {"domain": "Uncategorized", "confidence": 0.5, "tags": ["general"]}

    def analyze_trends(self, observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        recent: list[dict[str, Any]] = []
        for observation in observations:
            ts = self._as_utc(observation.get("timestamp"))
            if ts and ts >= since:
                normalized = {**observation, "timestamp": ts}
                recent.append(normalized)

        by_domain: dict[str, list[dict[str, Any]]] = {}
        for obs in recent:
            by_domain.setdefault(obs.get("domain", "Uncategorized"), []).append(obs)

        trends: list[dict[str, Any]] = []
        for domain, domain_obs in by_domain.items():
            midpoint = since + timedelta(days=15)
            first_half = [o for o in domain_obs if o["timestamp"] < midpoint]
            second_half = [o for o in domain_obs if o["timestamp"] >= midpoint]
            f_score = sum(float(o.get("confidence", 0.5)) for o in first_half) / max(1, len(first_half))
            s_score = sum(float(o.get("confidence", 0.5)) for o in second_half) / max(1, len(second_half))

            trend = "Stagnating"
            if s_score - f_score > 0.08:
                trend = "Progressing"
            if s_score >= 0.85 and len(second_half) >= 2:
                trend = "Excelling"

            trends.append({"domain": domain, "trend": trend, "observation_count": len(domain_obs)})

        missing_domains = VALID_DOMAINS - {t["domain"] for t in trends}
        for domain in missing_domains:
            trends.append({"domain": domain, "trend": "Stagnating", "observation_count": 0})
        return sorted(trends, key=lambda x: x["domain"])


reasoning_service = ReasoningService()
