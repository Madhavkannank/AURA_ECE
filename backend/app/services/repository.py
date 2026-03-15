from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from ..database import mongo


def to_object_id(value: str) -> ObjectId:
    return ObjectId(value)


def serialize_mongo_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    out = {**doc}
    out["_id"] = str(doc["_id"])
    return out


def create_student(payload: dict[str, Any]) -> dict[str, Any]:
    existing = mongo.students.find_one(
        {
            "full_name": payload.get("full_name"),
            "class_id": payload.get("class_id"),
            "parent_id": payload.get("parent_id"),
        }
    )
    if existing:
        return serialize_mongo_doc(existing)
    data = {**payload, "created_at": datetime.now(timezone.utc)}
    result = mongo.students.insert_one(data)
    return serialize_mongo_doc(mongo.students.find_one({"_id": result.inserted_id}))


def list_students() -> list[dict[str, Any]]:
    return [serialize_mongo_doc(doc) for doc in mongo.students.find().sort("created_at", -1)]


def list_students_by_class(class_id: str) -> list[dict[str, Any]]:
    docs = mongo.students.find({"class_id": class_id}).sort("created_at", -1)
    return [serialize_mongo_doc(doc) for doc in docs]


def get_students_by_parent(parent_id: str) -> list[dict[str, Any]]:
    docs = mongo.students.find({"parent_id": parent_id}).sort("created_at", -1)
    return [serialize_mongo_doc(doc) for doc in docs]


def get_student(student_id: str) -> dict[str, Any] | None:
    return serialize_mongo_doc(mongo.students.find_one({"_id": to_object_id(student_id)}))


def get_class_roster_names(class_id: str) -> list[str]:
    return [s["full_name"] for s in mongo.students.find({"class_id": class_id}, {"full_name": 1})]


def create_observation(payload: dict[str, Any]) -> dict[str, Any]:
    result = mongo.observations.insert_one(payload)
    return serialize_mongo_doc(mongo.observations.find_one({"_id": result.inserted_id}))


def get_observations_for_student(student_id: str) -> list[dict[str, Any]]:
    docs = mongo.observations.find({"student_id": student_id}).sort("timestamp", -1)
    return [serialize_mongo_doc(doc) for doc in docs]


def create_report(payload: dict[str, Any]) -> dict[str, Any]:
    result = mongo.reports.insert_one(payload)
    return serialize_mongo_doc(mongo.reports.find_one({"_id": result.inserted_id}))


def create_class_report(payload: dict[str, Any]) -> dict[str, Any]:
    result = mongo.class_reports.insert_one(payload)
    return serialize_mongo_doc(mongo.class_reports.find_one({"_id": result.inserted_id}))


def approve_report(report_id: str, teacher_id: str, approved: bool) -> dict[str, Any] | None:
    mongo.reports.update_one(
        {"_id": to_object_id(report_id)},
        {
            "$set": {
                "approved": approved,
                "approved_by": teacher_id,
                "approved_at": datetime.now(timezone.utc),
            }
        },
    )
    return serialize_mongo_doc(mongo.reports.find_one({"_id": to_object_id(report_id)}))


def get_reports_for_parent(parent_id: str) -> list[dict[str, Any]]:
    student_ids = [str(s["_id"]) for s in mongo.students.find({"parent_id": parent_id}, {"_id": 1})]
    docs = mongo.reports.find({"student_id": {"$in": student_ids}, "approved": True}).sort("generated_at", -1)
    return [serialize_mongo_doc(doc) for doc in docs]


def get_reports_for_student(student_id: str) -> list[dict[str, Any]]:
    docs = mongo.reports.find({"student_id": student_id}).sort("generated_at", -1)
    return [serialize_mongo_doc(doc) for doc in docs]


def get_latest_report_for_student_period(student_id: str, period: str) -> dict[str, Any] | None:
    doc = mongo.reports.find_one(
        {"student_id": student_id, "period": period},
        sort=[("generated_at", -1)],
    )
    return serialize_mongo_doc(doc)


def get_latest_class_report(class_id: str, period: str) -> dict[str, Any] | None:
    doc = mongo.class_reports.find_one(
        {"class_id": class_id, "period": period},
        sort=[("generated_at", -1)],
    )
    return serialize_mongo_doc(doc)


def get_user_by_user_id(user_id: str) -> dict[str, Any] | None:
    return serialize_mongo_doc(mongo.users.find_one({"user_id": user_id}))


def create_user(payload: dict[str, Any]) -> dict[str, Any]:
    existing = mongo.users.find_one({"user_id": payload.get("user_id")})
    if existing:
        return serialize_mongo_doc(existing)
    data = {**payload, "created_at": datetime.now(timezone.utc)}
    result = mongo.users.insert_one(data)
    return serialize_mongo_doc(mongo.users.find_one({"_id": result.inserted_id}))


def upsert_user_by_user_id(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    existing = mongo.users.find_one({"user_id": user_id})
    if existing:
        mongo.users.update_one({"_id": existing["_id"]}, {"$set": payload})
        return serialize_mongo_doc(mongo.users.find_one({"_id": existing["_id"]}))

    data = {"user_id": user_id, **payload, "created_at": datetime.now(timezone.utc)}
    result = mongo.users.insert_one(data)
    return serialize_mongo_doc(mongo.users.find_one({"_id": result.inserted_id}))


def create_note(payload: dict[str, Any]) -> dict[str, Any]:
    data = {**payload, "created_at": datetime.now(timezone.utc)}
    result = mongo.notes.insert_one(data)
    return serialize_mongo_doc(mongo.notes.find_one({"_id": result.inserted_id}))


def get_note(note_id: str) -> dict[str, Any] | None:
    return serialize_mongo_doc(mongo.notes.find_one({"_id": to_object_id(note_id)}))


def search_notes(
    query: str,
    owner_type: str | None = None,
    owner_id: str | None = None,
    file_kind: str | None = None,
) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {}
    if owner_type:
        filters["owner_type"] = owner_type
    if owner_id:
        filters["owner_id"] = owner_id
    if file_kind:
        filters["file_kind"] = file_kind

    if query.strip():
        regex = {"$regex": query.strip(), "$options": "i"}
        filters["$or"] = [
            {"file_name": regex},
            {"category": regex},
            {"summary": regex},
            {"keywords": regex},
            {"text_preview": regex},
        ]

    docs = mongo.notes.find(filters).sort("created_at", -1)
    return [serialize_mongo_doc(doc) for doc in docs]
