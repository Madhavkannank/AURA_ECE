from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


DomainType = Literal[
    "Cognitive Development",
    "Social-Emotional Development",
    "Physical Development",
    "Language Development",
    "Uncategorized",
]

TrendType = Literal["Progressing", "Stagnating", "Excelling"]
UserRole = Literal["teacher", "parent", "student"]
NoteOwnerType = Literal["student", "teacher"]


class LoginRequest(BaseModel):
    user_id: str
    password: str


class FirebaseLoginRequest(BaseModel):
    id_token: str
    requested_role: Optional[UserRole] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    student_id: Optional[str] = None
    parent_id: Optional[str] = None


class StudentCreate(BaseModel):
    full_name: str
    class_id: str
    parent_id: str
    parent_name: Optional[str] = None
    parent_language: str = "en"


class StudentOut(StudentCreate):
    id: str = Field(alias="_id")


class ObservationProcessRequest(BaseModel):
    student_id: str
    teacher_id: Optional[str] = None
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_mime_type: Optional[str] = "audio/wav"


class VideoObservationProcessRequest(BaseModel):
    student_id: str
    video_base64: str
    video_mime_type: Optional[str] = "video/mp4"
    teacher_note: Optional[str] = None


class ObservationOut(BaseModel):
    id: str = Field(alias="_id")
    student_id: str
    teacher_id: str
    timestamp: datetime
    raw_text: str
    pii_masked_text: str
    corrected_text: str
    domain: DomainType
    confidence: float
    tags: list[str]


class ReportGenerationRequest(BaseModel):
    period: Literal["weekly", "monthly"] = "weekly"
    include_trends: bool = True
    include_activity_suggestions: bool = True
    include_parent_translation: bool = True
    max_observations: int = Field(default=15, ge=5, le=50)


class ClassReportGenerationRequest(BaseModel):
    period: Literal["weekly", "monthly"] = "weekly"


class RoleBasedClassViewRequest(BaseModel):
    role: UserRole
    period: Literal["weekly", "monthly"] = "weekly"
    student_id: Optional[str] = None
    parent_id: Optional[str] = None


class ReportOut(BaseModel):
    id: str = Field(alias="_id")
    student_id: str
    period: str
    generated_at: datetime
    approved: bool
    teacher_assessment: str
    parent_summary: str
    translated_parent_summary: str


class ApproveReportRequest(BaseModel):
    teacher_id: Optional[str] = None
    approved: bool = True


class TrendSummary(BaseModel):
    domain: DomainType
    trend: TrendType
    observation_count: int


class NoteAnalyzeRequest(BaseModel):
    owner_type: NoteOwnerType
    owner_id: str
    embed_metadata: bool = True


class NoteSearchResponse(BaseModel):
    id: str = Field(alias="_id")
    file_name: str
    file_kind: str = "document"
    owner_type: NoteOwnerType
    owner_id: str
    category: str
    summary: str
    keywords: list[str]
    created_at: datetime
