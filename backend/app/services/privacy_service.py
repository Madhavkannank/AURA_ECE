import re
from typing import Any

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
except ImportError:  # pragma: no cover
    AnalyzerEngine = None
    AnonymizerEngine = None


class PrivacyService:
    def __init__(self) -> None:
        self.analyzer = None
        self.anonymizer = None
        if AnalyzerEngine and AnonymizerEngine:
            try:
                self.analyzer = AnalyzerEngine()
                self.anonymizer = AnonymizerEngine()
            except Exception:
                self.analyzer = None
                self.anonymizer = None

    def _regex_mask(self, text: str) -> str:
        masked = re.sub(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b", "[SSN]", text)
        masked = re.sub(r"\b\+?\d[\d\s().-]{7,}\b", "[PHONE]", masked)
        masked = re.sub(r"[\w.-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", masked)
        return masked

    def mask_text(self, text: str) -> dict[str, Any]:
        if not text:
            return {"text": "", "entities": []}

        if self.analyzer and self.anonymizer:
            try:
                results = self.analyzer.analyze(text=text, language="en")
                anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
                entities = [
                    {"type": r.entity_type, "start": r.start, "end": r.end, "score": r.score}
                    for r in results
                ]
                return {"text": self._regex_mask(anonymized.text), "entities": entities}
            except Exception:
                pass

        return {"text": self._regex_mask(text), "entities": []}


privacy_service = PrivacyService()
