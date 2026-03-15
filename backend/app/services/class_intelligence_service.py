from datetime import datetime, timedelta, timezone
from typing import Any

from .groq_client import get_groq_service
from .reasoning_service import reasoning_service


class ClassIntelligenceService:
    def __init__(self) -> None:
        self.groq = get_groq_service()

    def _window_days(self, period: str) -> int:
        return 7 if period == "weekly" else 30

    def _scoped_observations(self, observations: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=self._window_days(period))
        scoped: list[dict[str, Any]] = []
        for obs in observations:
            ts = obs.get("timestamp")
            if isinstance(ts, datetime):
                ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
                ts_utc = ts_utc.astimezone(timezone.utc)
                if ts_utc >= since:
                    scoped.append({**obs, "timestamp": ts_utc})
        return scoped

    def _student_snapshot(self, student: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
        domains: dict[str, int] = {}
        avg_conf = 0.0
        if observations:
            avg_conf = sum(float(o.get("confidence", 0.5)) for o in observations) / len(observations)
        for obs in observations:
            domain = obs.get("domain", "Uncategorized")
            domains[domain] = domains.get(domain, 0) + 1

        top_domain = "Uncategorized"
        if domains:
            top_domain = sorted(domains.items(), key=lambda x: x[1], reverse=True)[0][0]

        return {
            "student_id": student.get("_id"),
            "student_name": student.get("full_name", "Student"),
            "observation_count": len(observations),
            "average_confidence": round(avg_conf, 3),
            "top_domain": top_domain,
            "domain_distribution": domains,
        }

    def _behavioral_insights(self, observations: list[dict[str, Any]]) -> list[str]:
        seen: list[str] = []
        for obs in observations:
            items = obs.get("behavioral_insights", [])
            if isinstance(items, list):
                for insight in items:
                    text = str(insight).strip()
                    if text and text not in seen:
                        seen.append(text)
        if seen:
            return seen[:6]

        fallback = []
        for obs in observations:
            text = str(obs.get("corrected_text", "")).lower()
            if "shared" in text or "peer" in text or "together" in text:
                fallback.append("Increased peer collaboration")
            if "hesitat" in text or "struggl" in text:
                fallback.append("Hesitation during structured tasks")
            if "story" in text or "discussion" in text:
                fallback.append("High engagement in language activities")

        unique = []
        for item in fallback:
            if item not in unique:
                unique.append(item)
        return unique[:6] if unique else ["Classroom engagement observed across activities"]

    def _rank_students(self, snapshots: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not snapshots:
            return [], []
        ranked = sorted(
            snapshots,
            key=lambda s: (float(s.get("average_confidence", 0.0)), int(s.get("observation_count", 0))),
            reverse=True,
        )
        high = [s for s in ranked if s.get("observation_count", 0) > 0][:3]
        attention = [s for s in reversed(ranked) if s.get("observation_count", 0) > 0][:3]
        return attention, high

    def _suggest_interventions(self, trends: list[dict[str, Any]]) -> list[str]:
        weak = [t.get("domain") for t in trends if t.get("trend") == "Stagnating"]
        interventions: list[str] = []
        for domain in weak:
            if domain == "Cognitive Development":
                interventions.append("Introduce playful counting and sorting mini-games in centers.")
            elif domain == "Language Development":
                interventions.append("Increase short storytelling circles with targeted vocabulary prompts.")
            elif domain == "Social-Emotional Development":
                interventions.append("Use turn-taking partner tasks and explicit emotion-labeling routines.")
            elif domain == "Physical Development":
                interventions.append("Add fine-motor stations (pinching, threading, and tracing tasks).")

        if not interventions:
            interventions = [
                "Continue mixed small-group activities and monitor participation consistency.",
                "Maintain weekly reflection notes to capture growth evidence across domains.",
            ]
        return interventions[:5]

    def generate_master_class_report(
        self,
        class_id: str,
        students: list[dict[str, Any]],
        observations_by_student: dict[str, list[dict[str, Any]]],
        period: str,
    ) -> dict[str, Any]:
        scoped_by_student: dict[str, list[dict[str, Any]]] = {}
        all_scoped: list[dict[str, Any]] = []

        for student in students:
            sid = str(student.get("_id", ""))
            scoped = self._scoped_observations(observations_by_student.get(sid, []), period)
            scoped_by_student[sid] = scoped
            all_scoped.extend(scoped)

        trends = reasoning_service.analyze_trends(all_scoped)
        snapshots = [self._student_snapshot(s, scoped_by_student.get(str(s.get("_id")), [])) for s in students]
        attention, high = self._rank_students(snapshots)
        behaviors = self._behavioral_insights(all_scoped)
        interventions = self._suggest_interventions(trends)

        development_summary = [
            {
                "domain": t.get("domain", "Uncategorized"),
                "trend": t.get("trend", "Stagnating"),
                "observation_count": t.get("observation_count", 0),
            }
            for t in trends
        ]

        report = {
            "class_id": class_id,
            "period": period,
            "generated_at": datetime.now(timezone.utc),
            "class_overview": {
                "class_id": class_id,
                "student_count": len(students),
                "report_period": period,
            },
            "class_development_summary": development_summary,
            "key_behavioral_insights": behaviors,
            "students_requiring_attention": [
                {
                    "student_id": s.get("student_id"),
                    "student_name": s.get("student_name"),
                    "reason": f"Lower trend confidence in {s.get('top_domain', 'core domains')}",
                }
                for s in attention
            ],
            "high_performing_students": [
                {
                    "student_id": s.get("student_id"),
                    "student_name": s.get("student_name"),
                    "highlight": f"Consistent strength in {s.get('top_domain', 'learning activities')}",
                }
                for s in high
            ],
            "suggested_classroom_interventions": interventions,
            "student_snapshots": snapshots,
        }
        return report

    def build_role_view(
        self,
        master_report: dict[str, Any],
        role: str,
        student_id: str | None = None,
        parent_students: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if role == "teacher":
            return {"role": "teacher", "report": master_report}

        snapshots = master_report.get("student_snapshots", [])
        snapshot_map = {str(s.get("student_id")): s for s in snapshots}

        if role == "parent":
            children = parent_students or []
            child_views: list[dict[str, Any]] = []
            for child in children:
                sid = str(child.get("_id", ""))
                snap = snapshot_map.get(sid)
                if not snap:
                    continue
                child_views.append(
                    {
                        "student_id": sid,
                        "student_name": child.get("full_name", "Student"),
                        "strength": f"Showing growth in {snap.get('top_domain', 'class activities')}",
                        "area_to_practice": "Continue guided practice in developing skills.",
                        "suggested_home_activity": "Practice short playful learning activities at home for 10 minutes daily.",
                    }
                )

            return {
                "role": "parent",
                "period": master_report.get("period"),
                "children": child_views,
                "tone": "supportive",
            }

        # student view
        if role == "student":
            snap = snapshot_map.get(str(student_id or ""), {})
            top_domain = snap.get("top_domain", "your activities")
            return {
                "role": "student",
                "message": "Great work this week. Keep trying and learning with your friends.",
                "next_goal": f"Let's practice and grow in {top_domain}.",
            }

        return {"role": role, "report": master_report}


class_intelligence_service = ClassIntelligenceService()
