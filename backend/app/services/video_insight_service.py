import base64
import tempfile
from pathlib import Path
from typing import Any

from .groq_client import get_groq_service

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


class VideoInsightService:
    def __init__(self) -> None:
        self.groq = get_groq_service()

    def _decode_video_to_temp(self, video_b64: str, suffix: str) -> Path:
        raw = base64.b64decode(video_b64)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(raw)
        return tmp_path

    def _label_from_signals(self, motion: float, brightness: float, edge_density: float) -> str:
        if motion >= 22.0 and edge_density >= 0.08:
            return "Active peer interaction observed"
        if motion >= 10.0:
            return "Focused task attempt observed"
        if brightness < 70.0:
            return "Quiet attention period observed"
        return "Calm attention/listening observed"

    def _infer_insights(self, timeline: list[dict[str, Any]]) -> list[str]:
        labels = " ".join(item.get("event", "").lower() for item in timeline)
        insights: list[str] = []

        if "peer" in labels or "interaction" in labels:
            insights.append("Social collaboration")
        if "task attempt" in labels or "focused" in labels:
            insights.append("Persistence in problem solving")
        if "calm" in labels or "listening" in labels:
            insights.append("Self-regulation and attention")

        if not insights:
            insights = ["Classroom engagement"]
        return insights

    def _ai_refine_timeline(self, timeline: list[dict[str, Any]], signals: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        if not self.groq.enabled or not timeline:
            return timeline, self._infer_insights(timeline)

        prompt = (
            "You are analyzing preschool classroom video segment signals. "
            "Convert these segments into concise micro-moment events and developmental insights. "
            "Return JSON with keys timeline and behavioral_insights. "
            "timeline must keep the same start_sec/end_sec structure and provide an event text for each segment. "
            "behavioral_insights should have 2-5 short educational insights. "
            f"Segments: {signals}"
        )
        data = self.groq.chat_json(prompt, self.groq.settings.groq_light_model)

        ai_timeline = data.get("timeline", []) if isinstance(data, dict) else []
        ai_insights = data.get("behavioral_insights", []) if isinstance(data, dict) else []

        normalized_timeline: list[dict[str, Any]] = []
        if isinstance(ai_timeline, list):
            for i, item in enumerate(ai_timeline[: len(timeline)]):
                base = timeline[i]
                if isinstance(item, dict):
                    normalized_timeline.append(
                        {
                            "start_sec": int(item.get("start_sec", base.get("start_sec", 0))),
                            "end_sec": int(item.get("end_sec", base.get("end_sec", 0))),
                            "event": str(item.get("event", base.get("event", "Classroom activity observed"))).strip(),
                        }
                    )
        if not normalized_timeline:
            normalized_timeline = timeline

        insights: list[str] = []
        if isinstance(ai_insights, list):
            insights = [str(x).strip() for x in ai_insights if str(x).strip()][:5]
        if not insights:
            insights = self._infer_insights(normalized_timeline)

        return normalized_timeline, insights

    def analyze_video(self, video_b64: str, mime_type: str = "video/mp4") -> dict[str, Any]:
        suffix = ".mp4"
        if "webm" in (mime_type or ""):
            suffix = ".webm"
        elif "quicktime" in (mime_type or ""):
            suffix = ".mov"

        video_path = self._decode_video_to_temp(video_b64, suffix)
        try:
            if not cv2:
                timeline = [
                    {"start_sec": 0, "end_sec": 5, "event": "Focused task attempt observed"},
                    {"start_sec": 5, "end_sec": 10, "event": "Active peer interaction observed"},
                    {"start_sec": 10, "end_sec": 15, "event": "Collaborative completion observed"},
                ]
                return {
                    "timeline": timeline,
                    "behavioral_insights": self._infer_insights(timeline),
                    "meta": {"engine": "fallback", "duration_sec": 15.0},
                }

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                timeline = [{"start_sec": 0, "end_sec": 10, "event": "Video uploaded; behavioral sequence unavailable"}]
                return {
                    "timeline": timeline,
                    "behavioral_insights": ["Classroom engagement"],
                    "meta": {"engine": "opencv", "duration_sec": 10.0},
                }

            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            duration_sec = max(1.0, frame_count / fps)

            segment_count = 4
            segment_len = max(2.0, duration_sec / segment_count)
            timeline: list[dict[str, Any]] = []
            signal_segments: list[dict[str, Any]] = []

            for idx in range(segment_count):
                start = int(idx * segment_len)
                end = int(min(duration_sec, (idx + 1) * segment_len))
                mid = int((start + end) / 2)

                cap.set(cv2.CAP_PROP_POS_MSEC, max(0, (mid - 1) * 1000))
                ok1, frame1 = cap.read()
                cap.set(cv2.CAP_PROP_POS_MSEC, max(0, (mid + 1) * 1000))
                ok2, frame2 = cap.read()

                motion_score = 0.0
                brightness_score = 120.0
                edge_density = 0.03
                if ok1 and ok2 and frame1 is not None and frame2 is not None:
                    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
                    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
                    diff = cv2.absdiff(gray1, gray2)
                    motion_score = float(diff.mean())
                    brightness_score = float(gray2.mean())
                    edges = cv2.Canny(gray2, 80, 160)
                    edge_density = float((edges > 0).sum()) / float(edges.size)

                signal_segments.append(
                    {
                        "start_sec": start,
                        "end_sec": end,
                        "motion": round(motion_score, 3),
                        "brightness": round(brightness_score, 3),
                        "edge_density": round(edge_density, 5),
                    }
                )

                timeline.append(
                    {
                        "start_sec": start,
                        "end_sec": end,
                        "event": self._label_from_signals(motion_score, brightness_score, edge_density),
                    }
                )

            cap.release()
            refined_timeline, refined_insights = self._ai_refine_timeline(timeline, signal_segments)
            return {
                "timeline": refined_timeline,
                "behavioral_insights": refined_insights,
                "meta": {
                    "engine": "opencv",
                    "duration_sec": round(duration_sec, 2),
                    "segments": signal_segments,
                    "ai_refined": bool(self.groq.enabled),
                },
            }
        finally:
            try:
                video_path.unlink(missing_ok=True)
            except Exception:
                pass


video_insight_service = VideoInsightService()
