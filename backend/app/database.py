from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from .config import get_settings


class MongoManager:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = MongoClient(settings.mongo_uri)
        self.db = self.client[settings.mongo_db]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        try:
            self.students.create_index([("class_id", 1), ("created_at", -1)])
            self.students.create_index([("parent_id", 1), ("created_at", -1)])

            self.observations.create_index([("student_id", 1), ("timestamp", -1)])

            self.reports.create_index([("student_id", 1), ("generated_at", -1)])
            self.reports.create_index([("student_id", 1), ("period", 1), ("generated_at", -1)])
            self.reports.create_index([("approved", 1), ("generated_at", -1)])

            self.class_reports.create_index([("class_id", 1), ("generated_at", -1)])
            self.class_reports.create_index([("class_id", 1), ("period", 1), ("generated_at", -1)])

            self.users.create_index([("user_id", 1)], unique=True)

            self.notes.create_index([("owner_type", 1), ("owner_id", 1), ("created_at", -1)])
            self.notes.create_index([("created_at", -1)])
        except PyMongoError:
            # Keep startup resilient when Mongo is temporarily unavailable.
            pass

    @property
    def students(self) -> Collection:
        return self.db["students"]

    @property
    def observations(self) -> Collection:
        return self.db["observations"]

    @property
    def reports(self) -> Collection:
        return self.db["reports"]

    @property
    def users(self) -> Collection:
        return self.db["users"]

    @property
    def notes(self) -> Collection:
        return self.db["notes"]

    @property
    def class_reports(self) -> Collection:
        return self.db["class_reports"]


mongo = MongoManager()
