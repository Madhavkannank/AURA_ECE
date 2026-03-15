from datetime import datetime, timedelta, timezone
from typing import Any

from .groq_client import get_groq_service
from .reasoning_service import reasoning_service


class ReportService:
    def __init__(self) -> None:
        self.groq = get_groq_service()

    def _as_utc(self, value: Any) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def generate_reports(
        self,
        student: dict[str, Any],
        observations: list[dict[str, Any]],
        period: str,
        include_trends: bool = True,
        include_activity_suggestions: bool = True,
        include_parent_translation: bool = True,
        max_observations: int = 15,
    ) -> dict[str, Any]:
        window_days = 7 if period == "weekly" else 30
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        scoped: list[dict[str, Any]] = []
        for observation in observations:
            ts = self._as_utc(observation.get("timestamp"))
            if ts and ts >= since:
                normalized = {**observation, "timestamp": ts}
                scoped.append(normalized)

        max_items = max(5, min(int(max_observations or 15), 50))
        trends = reasoning_service.analyze_trends(observations) if include_trends else []
        teacher_assessment = self._build_teacher_assessment(student, scoped[:max_items], trends)
        parent_summary = self._build_parent_summary(student, trends)
        activity_suggestions = self._extract_activity_suggestions(parent_summary) if include_activity_suggestions else []
        translated = (
            self.translate_for_parent(parent_summary, student.get("parent_language", "en"))
            if include_parent_translation
            else parent_summary
        )

        return {
            "student_id": str(student["_id"]),
            "period": period,
            "generated_at": datetime.now(timezone.utc),
            "approved": False,
            "teacher_assessment": teacher_assessment,
            "parent_summary": parent_summary,
            "translated_parent_summary": translated,
            "activity_suggestions": activity_suggestions,
            "trends": trends,
            "report_features": {
                "include_trends": include_trends,
                "include_activity_suggestions": include_activity_suggestions,
                "include_parent_translation": include_parent_translation,
                "max_observations": max_items,
            },
        }

    def _build_teacher_assessment(
        self, student: dict[str, Any], observations: list[dict[str, Any]], trends: list[dict[str, Any]]
    ) -> str:
        obs_lines = [
            f"- [{o.get('domain', 'Uncategorized')}] {o.get('corrected_text', '')}" for o in observations[:15]
        ]
        trend_lines = [f"- {t['domain']}: {t['trend']} ({t['observation_count']} obs)" for t in trends]

        prompt = (
            "Generate a structured Teacher Assessment for early childhood progress. Include strengths, growth areas, and "
            "evidence-based interpretation. Student: "
            f"{student.get('full_name')}. Observations:\n{chr(10).join(obs_lines)}\nTrends:\n{chr(10).join(trend_lines)}"
        )
        text = self.groq.chat_text(prompt, self.groq.settings.groq_reasoning_model)
        if text:
            return text

        return (
            f"Teacher Assessment for {student.get('full_name')}\n\n"
            "Categorized Observations:\n"
            f"{chr(10).join(obs_lines) if obs_lines else '- No observations this period.'}\n\n"
            "Trend Overview:\n"
            f"{chr(10).join(trend_lines)}"
        )

    def _build_parent_summary(self, student: dict[str, Any], trends: list[dict[str, Any]]) -> str:
        weaker = [t for t in trends if t["trend"] == "Stagnating"]
        strength = [t for t in trends if t["trend"] in {"Progressing", "Excelling"}]

        suggestion_seed = ", ".join([w["domain"] for w in weaker]) or "general development"
        prompt = (
            "Write a warm, supportive parent summary from a teacher perspective for early-childhood progress. "
            "Include 2-3 simple at-home activities focused on: "
            f"{suggestion_seed}. Student name: {student.get('full_name')}."
        )
        text = self.groq.chat_text(prompt, self.groq.settings.groq_reasoning_model)
        if text:
            return text

        strengths = ", ".join([s["domain"] for s in strength]) or "steady engagement"
        focus = ", ".join([w["domain"] for w in weaker]) or "continued balanced growth"
        return (
            f"{student.get('full_name')} is showing positive development, especially in {strengths}. "
            f"We will keep supporting growth in {focus}. At home, try short read-aloud sessions, playful counting games, "
            "and turn-taking activities to reinforce classroom learning."
        )

    def _extract_activity_suggestions(self, parent_summary: str) -> list[str]:
        prompt = (
            "Extract 2-4 concise at-home activity suggestions from this parent summary. "
            "Return JSON: {\"activities\": [\"...\"]}. Keep each activity under 100 characters. "
            f"Summary: {parent_summary}"
        )
        data = self.groq.chat_json(prompt, self.groq.settings.groq_light_model)
        if isinstance(data, dict):
            activities = data.get("activities", [])
            if isinstance(activities, list):
                clean = [str(item).strip() for item in activities if str(item).strip()]
                if clean:
                    return clean[:4]

        fallback: list[str] = []
        for line in parent_summary.splitlines():
            stripped = line.strip(" -•\t")
            lower = stripped.lower()
            if any(word in lower for word in ["try ", "practice", "activity", "read", "play", "count"]):
                fallback.append(stripped)
        if fallback:
            return fallback[:4]

        return [
            "Read aloud together for 10 minutes each day.",
            "Play turn-taking games and practice emotion words.",
            "Use counting or sorting games during routine activities.",
        ]

    def translate_for_parent(self, text: str, target_language: str) -> str:
        if not text:
            return ""
        if target_language.lower() in {"en", "english"}:
            return text
        prompt = (
            "Translate the following parent summary into the target language while preserving supportive tone and clarity. "
            "Return only the translated text."
            f"\nTarget language: {target_language}\nText: {text}"
        )
        translated = self.groq.chat_text(prompt, self.groq.settings.groq_light_model)
        return translated or text


report_service = ReportService()
