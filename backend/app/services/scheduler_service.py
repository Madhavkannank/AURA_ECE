from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..config import get_settings
from .report_service import report_service
from .repository import (
    create_report,
    get_latest_report_for_student_period,
    get_observations_for_student,
    list_students,
)


class ReportSchedulerService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self._lock = Lock()

    def _period_window(self, period: str) -> timedelta:
        return timedelta(days=7 if period == "weekly" else 30)

    def _should_skip(self, student_id: str, period: str) -> bool:
        latest = get_latest_report_for_student_period(student_id, period)
        if not latest:
            return False
        generated_at = latest.get("generated_at")
        if not isinstance(generated_at, datetime):
            return False

        ts = generated_at if generated_at.tzinfo else generated_at.replace(tzinfo=timezone.utc)
        return ts >= datetime.now(timezone.utc) - self._period_window(period)

    def run_cycle(
        self,
        period: str,
        include_trends: bool = True,
        include_activity_suggestions: bool = True,
        include_parent_translation: bool = True,
        max_observations: int = 15,
    ) -> dict[str, Any]:
        with self._lock:
            students = list_students()
            created = 0
            skipped = 0
            report_ids: list[str] = []

            for student in students:
                student_id = student.get("_id")
                if not student_id:
                    continue

                if self._should_skip(student_id, period):
                    skipped += 1
                    continue

                observations = get_observations_for_student(student_id)
                report = report_service.generate_reports(
                    student,
                    observations,
                    period,
                    include_trends=include_trends,
                    include_activity_suggestions=include_activity_suggestions,
                    include_parent_translation=include_parent_translation,
                    max_observations=max_observations,
                )
                created_doc = create_report(report)
                report_ids.append(created_doc.get("_id", ""))
                created += 1

            return {
                "status": "ok",
                "period": period,
                "students_processed": len(students),
                "reports_created": created,
                "reports_skipped_recent": skipped,
                "report_ids": [rid for rid in report_ids if rid],
            }

    def start(self) -> None:
        if not self.settings.report_scheduler_enabled:
            return
        if self.scheduler.running:
            return

        minutes = max(1, int(self.settings.report_scheduler_interval_minutes))
        self.scheduler.add_job(
            self._scheduled_job,
            trigger=IntervalTrigger(minutes=minutes),
            id="report_cycle",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()

    def _scheduled_job(self) -> None:
        period = self.settings.report_scheduler_period
        self.run_cycle(period)

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.report_scheduler_enabled,
            "running": self.scheduler.running,
            "period": self.settings.report_scheduler_period,
            "interval_minutes": self.settings.report_scheduler_interval_minutes,
        }


report_scheduler_service = ReportSchedulerService()
