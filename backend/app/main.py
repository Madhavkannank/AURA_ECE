from datetime import datetime, timezone
from importlib.util import find_spec
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, File, Form, Query, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import get_settings
from .database import mongo
from .models.schemas import (
    ApproveReportRequest,
    ClassReportGenerationRequest,
    FirebaseLoginRequest,
    LoginRequest,
    ObservationProcessRequest,
    RoleBasedClassViewRequest,
    ReportGenerationRequest,
    StudentCreate,
    TokenResponse,
    VideoObservationProcessRequest,
)
from .services.auth_service import auth_service, require_parent_or_teacher, require_teacher
from .services.firebase_auth_service import firebase_auth_service
from .services.groq_client import get_groq_service
from .services.input_engine import input_engine
from .services.privacy_service import privacy_service
from .services.reasoning_service import reasoning_service
from .services.report_service import report_service
from .services.notes_service import notes_service
from .services.scheduler_service import report_scheduler_service
from .services.video_insight_service import video_insight_service
from .services.class_intelligence_service import class_intelligence_service
from .services.repository import (
    create_observation,
    create_note,
    create_report,
    create_student,
    create_user,
    get_note,
    get_class_roster_names,
    get_observations_for_student,
    get_reports_for_parent,
    get_reports_for_student,
    get_student,
    get_students_by_parent,
    get_user_by_user_id,
    get_latest_class_report,
    list_students,
    list_students_by_class,
    search_notes,
    upsert_user_by_user_id,
    approve_report,
    create_class_report,
)

settings = get_settings()
app = FastAPI(title=settings.app_name)

allowed_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/system/self-test")
def system_self_test(response: Response, run_live_models: bool = Query(False)) -> dict:
    checks: dict[str, dict[str, str | bool]] = {}

    try:
        mongo.client.admin.command("ping")
        checks["mongo"] = {"ok": True, "detail": "MongoDB ping succeeded"}
    except Exception as exc:
        checks["mongo"] = {"ok": False, "detail": f"MongoDB ping failed: {exc}"}

    groq = get_groq_service()
    checks["groq_config"] = {
        "ok": bool(groq.enabled),
        "detail": "GROQ_API_KEY is configured" if groq.enabled else "GROQ_API_KEY is missing",
    }

    if run_live_models and groq.enabled:
        probe = groq.chat_json(
            "Return JSON with key status set to ok.",
            settings.groq_light_model,
        )
        checks["groq_live"] = {
            "ok": probe.get("status") == "ok",
            "detail": "Groq live probe succeeded" if probe.get("status") == "ok" else "Groq live probe failed",
        }
    else:
        checks["groq_live"] = {
            "ok": not run_live_models,
            "detail": "Skipped (set run_live_models=true)" if not run_live_models else "Skipped (Groq not configured)",
        }

    checks["privacy"] = {
        "ok": bool(privacy_service.analyzer and privacy_service.anonymizer),
        "detail": "Presidio engines loaded"
        if privacy_service.analyzer and privacy_service.anonymizer
        else "Using regex fallback masking",
    }

    checks["ocr"] = {
        "ok": bool(find_spec("pytesseract") or find_spec("rapidocr_onnxruntime")),
        "detail": "OCR dependency available"
        if (find_spec("pytesseract") or find_spec("rapidocr_onnxruntime"))
        else "No OCR dependency available",
    }

    checks["scheduler"] = {
        "ok": True,
        "detail": str(report_scheduler_service.status()),
    }

    failed_checks = [name for name, item in checks.items() if not item.get("ok")]
    if failed_checks:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if not failed_checks else "degraded",
        "service": settings.app_name,
        "failed_checks": failed_checks,
        "checks": checks,
    }


@app.on_event("startup")
def startup_event() -> None:
    report_scheduler_service.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    report_scheduler_service.stop()


@app.get("/auth/firebase-client-config")
def firebase_client_config() -> dict[str, str]:
    if not settings.firebase_project_id or not settings.firebase_web_api_key:
        raise HTTPException(status_code=500, detail="Firebase client configuration is incomplete")

    auth_domain = settings.firebase_auth_domain or f"{settings.firebase_project_id}.firebaseapp.com"
    return {
        "apiKey": settings.firebase_web_api_key,
        "authDomain": auth_domain,
        "projectId": settings.firebase_project_id,
        "appId": settings.firebase_app_id,
    }


@app.get("/auth/firebase-google-popup", response_class=HTMLResponse)
def firebase_google_popup_page(
    role: str = Query("teacher"),
    return_to: str = Query("http://localhost:8501"),
) -> HTMLResponse:
    safe_role = role if role in {"teacher", "student", "parent"} else "teacher"
    allowed_prefixes = ("http://127.0.0.1:8501", "http://localhost:8501")
    safe_return = return_to if any(return_to.startswith(p) for p in allowed_prefixes) else "http://localhost:8501"
    safe_return_js = quote(safe_return, safe="/:?=&%.-_")

    html = f"""
<!doctype html>
<html>
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>AURA-ECE Google Sign-In</title>
        <style>
            body {{ font-family: 'Inter', Arial, sans-serif; margin: 0; padding: 24px; background: #efe6dd; color: #1a1a1a; display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
            .card {{ max-width: 460px; width: 100%; background: rgba(239, 230, 221, 0.72); border: 1px solid rgba(0,0,0,0.12); border-radius: 16px; padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.04); text-align: center; }}
            h2 {{ margin: 0 0 12px 0; font-family: 'Playfair Display', serif; font-weight: 500; font-size: 28px; color: #1a1a1a; }}
            p {{ color: #6b6b6b; font-size: 15px; margin-bottom: 24px; }}
            button {{ width: 100%; height: 48px; border: none; border-radius: 999px; font-weight: 500; font-size: 15px; cursor: pointer; color: #fff; background: #1a1a1a; transition: all 0.3s ease; }}
            button:disabled {{ opacity: 0.7; cursor: not-allowed; }}
            #status {{ margin-top: 16px; font-size: 13px; color: #9a9a9a; margin-bottom: 0; }}
        </style>
    </head>
    <body>
        <div class=\"card\">
            <h2>Continue with Google</h2>
            <p>Click once to open the Google popup. You will be redirected back to AURA-ECE.</p>
            <button id=\"google-popup-btn\">Sign in with Google</button>
            <p id=\"status\"></p>
        </div>

        <script src=\"https://www.gstatic.com/firebasejs/10.12.5/firebase-app-compat.js\"></script>
        <script src=\"https://www.gstatic.com/firebasejs/10.12.5/firebase-auth-compat.js\"></script>
        <script>
            (async function() {{
                const status = document.getElementById('status');
                const btn = document.getElementById('google-popup-btn');
                status.textContent = 'Ready to continue with Google.';

                const completeAuth = async (idToken) => {{
                    const dest = new URL('{safe_return_js}', window.location.origin);
                    dest.searchParams.set('g_id_token', idToken);
                    dest.searchParams.set('g_role', '{safe_role}');
                    window.location.replace(dest.toString());
                }};

                try {{
                    const cfgResp = await fetch('/auth/firebase-client-config', {{ credentials: 'omit' }});
                    if (!cfgResp.ok) throw new Error('Firebase config unavailable');
                    const cfg = await cfgResp.json();

                    if (!firebase.apps.length) firebase.initializeApp(cfg);

                    // If returning from redirect flow, complete auth and return to app.
                    const result = await firebase.auth().getRedirectResult();
                    if (result && result.user) {{
                        status.textContent = 'Authenticating...';
                        const idToken = await result.user.getIdToken();
                        await completeAuth(idToken);
                        return;
                    }}

                    btn.onclick = async () => {{
                        try {{
                            btn.disabled = true;
                            status.textContent = 'Opening Google sign-in...';
                            const provider = new firebase.auth.GoogleAuthProvider();
                            const popupResult = await firebase.auth().signInWithPopup(provider);
                            if (popupResult && popupResult.user) {{
                                const idToken = await popupResult.user.getIdToken();
                                await completeAuth(idToken);
                                return;
                            }}
                            throw new Error('Google sign-in did not return a user.');
                        }} catch (popupErr) {{
                            const code = (popupErr && popupErr.code) ? String(popupErr.code) : '';
                            const msg = (popupErr && popupErr.message) ? String(popupErr.message) : String(popupErr);
                            // Fallback to redirect flow for environments where popup is blocked/unsupported.
                            if (code.includes('operation-not-supported') || code.includes('popup-blocked')) {{
                                status.textContent = 'Popup unavailable, redirecting to Google...';
                                const provider = new firebase.auth.GoogleAuthProvider();
                                await firebase.auth().signInWithRedirect(provider);
                                return;
                            }}
                            status.textContent = 'Google sign-in failed: ' + msg;
                            btn.disabled = false;
                        }}
                    }};
                }} catch (err) {{
                    status.textContent = 'Google sign-in failed: ' + (err && err.message ? err.message : err);
                    btn.disabled = false;
                }}
            }})();
        </script>
    </body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> dict:
    user = auth_service.authenticate_user(payload.user_id, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth_service.create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "user_id": user["user_id"],
        "parent_id": user.get("parent_id"),
    }


@app.post("/auth/firebase-google", response_model=TokenResponse)
def firebase_google_login(payload: FirebaseLoginRequest) -> dict:
    decoded = firebase_auth_service.verify_google_id_token(payload.id_token)
    email = str(decoded.get("email", "")).lower()
    email_verified = bool(decoded.get("email_verified", False))
    if not email or not email_verified:
        raise HTTPException(status_code=401, detail="Firebase email is missing or not verified")
    role = payload.requested_role
    if not role:
        domain = email.split("@")[-1] if "@" in email else ""
        if settings.teacher_email_domain and domain == settings.teacher_email_domain.lower():
            role = "teacher"
        else:
            role = "student"

    user_id = f"firebase:{decoded.get('uid')}"
    display_name = decoded.get("name") or email
    parent_id = user_id if role in ("parent", "student") else None
    try:
        user = upsert_user_by_user_id(
            user_id,
            {
                "display_name": display_name,
                "email": email,
                "role": role,
                "auth_provider": "firebase",
                "parent_id": parent_id,
                "firebase_uid": decoded.get("uid"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"User store unavailable: {exc}") from exc

    try:
        token = auth_service.create_access_token(user)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Token generation failed: {exc}") from exc

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "user_id": user["user_id"],
        "student_id": user.get("student_id"),
        "parent_id": user.get("parent_id"),
    }


@app.post("/auth/bootstrap")
def bootstrap_auth() -> dict:
    if settings.app_env.lower() != "dev" and not settings.allow_bootstrap_auth:
        raise HTTPException(status_code=403, detail="Bootstrap auth is disabled")

    teacher = get_user_by_user_id("teacher-001")
    parent = get_user_by_user_id("parent-001")
    if not teacher:
        create_user(
            {
                "user_id": "teacher-001",
                "display_name": "Lead Teacher",
                "role": "teacher",
                "password_hash": auth_service.hash_password("teacher123"),
            }
        )
    if not parent:
        create_user(
            {
                "user_id": "parent-001",
                "display_name": "Sample Parent",
                "role": "parent",
                "parent_id": "parent-001",
                "password_hash": auth_service.hash_password("parent123"),
            }
        )
    return {
        "status": "ok",
        "message": "Bootstrap users ensured. teacher-001/teacher123, parent-001/parent123",
    }


@app.post("/students")
def add_student(payload: StudentCreate, _: dict = Depends(require_teacher)) -> dict:
    return create_student(payload.model_dump())


@app.get("/students")
def students(_: dict = Depends(require_teacher)) -> list[dict]:
    return list_students()


@app.post("/observations/process")
def process_observation(payload: ObservationProcessRequest, user: dict = Depends(require_teacher)) -> dict:
    student = get_student(payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    transcribed = payload.text or ""
    if payload.audio_base64:
        transcribed = input_engine.transcribe_audio(payload.audio_base64, payload.audio_mime_type or "audio/wav")

    pii_result = privacy_service.mask_text(transcribed)
    roster_names = get_class_roster_names(student["class_id"])
    corrected = input_engine.correct_transcription(pii_result["text"], roster_names, student["full_name"])
    classification = reasoning_service.classify_observation(corrected)

    observation = {
        "student_id": payload.student_id,
        "teacher_id": user["user_id"],
        "timestamp": datetime.now(timezone.utc),
        "raw_text": transcribed,
        "pii_masked_text": pii_result["text"],
        "pii_entities": pii_result["entities"],
        "corrected_text": corrected,
        "domain": classification["domain"],
        "confidence": classification["confidence"],
        "tags": classification["tags"],
    }
    return create_observation(observation)


@app.post("/observations/video-process")
def process_video_observation(payload: VideoObservationProcessRequest, user: dict = Depends(require_teacher)) -> dict:
    student = get_student(payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    video_result = video_insight_service.analyze_video(payload.video_base64, payload.video_mime_type or "video/mp4")
    timeline = video_result.get("timeline", [])
    insights = video_result.get("behavioral_insights", [])

    timeline_lines = [
        f"{item.get('start_sec', 0)}-{item.get('end_sec', 0)}s: {item.get('event', '')}"
        for item in timeline
    ]
    source_text = (
        f"Teacher Note: {(payload.teacher_note or '').strip()}\n"
        f"Video Behavioral Timeline:\n{chr(10).join(timeline_lines)}\n"
        f"Inferred Insights: {', '.join(insights)}"
    ).strip()

    pii_result = privacy_service.mask_text(source_text)
    roster_names = get_class_roster_names(student["class_id"])
    corrected = input_engine.correct_transcription(pii_result["text"], roster_names, student["full_name"])
    classification = reasoning_service.classify_observation(corrected)

    observation = {
        "student_id": payload.student_id,
        "teacher_id": user["user_id"],
        "timestamp": datetime.now(timezone.utc),
        "raw_text": source_text,
        "pii_masked_text": pii_result["text"],
        "pii_entities": pii_result["entities"],
        "corrected_text": corrected,
        "domain": classification["domain"],
        "confidence": classification["confidence"],
        "tags": classification["tags"],
        "modality": "video",
        "behavior_timeline": timeline,
        "behavioral_insights": insights,
        "video_meta": video_result.get("meta", {}),
    }
    return create_observation(observation)


@app.get("/students/{student_id}/insights")
def student_insights(student_id: str, _: dict = Depends(require_teacher)) -> dict:
    student = get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    observations = get_observations_for_student(student_id)
    trends = reasoning_service.analyze_trends(observations)
    reports = get_reports_for_student(student_id)
    return {
        "student": student,
        "recent_observations": observations[:20],
        "trends": trends,
        "reports": reports,
    }


@app.post("/reports/generate/{student_id}")
def generate_report(student_id: str, payload: ReportGenerationRequest, _: dict = Depends(require_teacher)) -> dict:
    student = get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    observations = get_observations_for_student(student_id)
    report = report_service.generate_reports(
        student,
        observations,
        payload.period,
        include_trends=payload.include_trends,
        include_activity_suggestions=payload.include_activity_suggestions,
        include_parent_translation=payload.include_parent_translation,
        max_observations=payload.max_observations,
    )
    return create_report(report)


@app.post("/reports/{report_id}/approve")
def review_report(report_id: str, payload: ApproveReportRequest, user: dict = Depends(require_teacher)) -> dict:
    report = approve_report(report_id, user["user_id"], payload.approved)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.post("/reports/run-cycle")
def run_report_cycle(payload: ReportGenerationRequest, _: dict = Depends(require_teacher)) -> dict:
    return report_scheduler_service.run_cycle(
        payload.period,
        include_trends=payload.include_trends,
        include_activity_suggestions=payload.include_activity_suggestions,
        include_parent_translation=payload.include_parent_translation,
        max_observations=payload.max_observations,
    )


@app.get("/reports/scheduler-status")
def scheduler_status(_: dict = Depends(require_teacher)) -> dict:
    return report_scheduler_service.status()


@app.post("/reports/class/generate/{class_id}")
def generate_class_report(
    class_id: str,
    payload: ClassReportGenerationRequest,
    _: dict = Depends(require_teacher),
) -> dict:
    students = list_students_by_class(class_id)
    if not students:
        raise HTTPException(status_code=404, detail="No students found for class")

    observations_by_student: dict[str, list[dict]] = {}
    for student in students:
        sid = str(student.get("_id", ""))
        observations_by_student[sid] = get_observations_for_student(sid)

    report = class_intelligence_service.generate_master_class_report(
        class_id=class_id,
        students=students,
        observations_by_student=observations_by_student,
        period=payload.period,
    )
    return create_class_report(report)


@app.get("/reports/class/{class_id}")
def get_class_report(
    class_id: str,
    period: str = Query("weekly"),
    _: dict = Depends(require_teacher),
) -> dict:
    if period not in {"weekly", "monthly"}:
        raise HTTPException(status_code=400, detail="period must be weekly or monthly")
    report = get_latest_class_report(class_id, period)
    if not report:
        raise HTTPException(status_code=404, detail="Class report not found")
    return report


@app.post("/reports/class/{class_id}/view")
def get_class_role_view(
    class_id: str,
    payload: RoleBasedClassViewRequest,
    user: dict = Depends(auth_service.get_current_user),
) -> dict:
    period = payload.period
    report = get_latest_class_report(class_id, period)
    if not report:
        raise HTTPException(status_code=404, detail="Class report not found")

    role = payload.role
    if role == "teacher" and user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Teacher role required")

    if role == "parent":
        parent_id = payload.parent_id or user.get("parent_id")
        if user.get("role") == "parent" and parent_id != user.get("parent_id"):
            raise HTTPException(status_code=403, detail="Cannot request view for another parent")
        children = get_students_by_parent(parent_id or "")
        return class_intelligence_service.build_role_view(report, "parent", parent_students=children)

    if role == "student":
        sid = payload.student_id
        if not sid:
            raise HTTPException(status_code=400, detail="student_id is required for student view")
        return class_intelligence_service.build_role_view(report, "student", student_id=sid)

    return class_intelligence_service.build_role_view(report, "teacher")


@app.get("/parents/{parent_id}/reports")
def parent_reports(parent_id: str, user: dict = Depends(require_parent_or_teacher)) -> list[dict]:
    if user.get("role") == "parent" and user.get("parent_id") != parent_id:
        raise HTTPException(status_code=403, detail="Cannot access other parent reports")
    return get_reports_for_parent(parent_id)


@app.post("/notes/analyze-upload")
async def analyze_note_upload(
    owner_type: str = Form(...),
    owner_id: str = Form(...),
    embed_metadata: bool = Form(True),
    file: UploadFile = File(...),
    user: dict = Depends(require_teacher),
) -> dict:
    if owner_type not in {"student", "teacher"}:
        raise HTTPException(status_code=400, detail="owner_type must be 'student' or 'teacher'")
    if owner_type == "student" and not get_student(owner_id):
        raise HTTPException(status_code=404, detail="Student not found")
    if owner_type == "teacher" and owner_id != user.get("user_id"):
        raise HTTPException(status_code=403, detail="Teacher notes can only be attached to current teacher")

    file_kind = notes_service.detect_file_kind(file.filename, file.content_type)
    saved_path = await notes_service.save_upload(file, file_kind=file_kind)

    if file_kind == "video":
        extracted = ""
        analysis = {
            "keywords": ["video", "observation", "evidence"],
            "category": "Video Evidence",
            "summary": "Video file uploaded successfully. Text extraction is skipped for video files.",
        }
        embedded = False
    else:
        extracted = notes_service.extract_text(saved_path)
        analysis = notes_service.analyze_text(extracted)
        embedded = notes_service.embed_metadata(saved_path, analysis["keywords"], analysis["category"]) if embed_metadata else False

    note = create_note(
        {
            "owner_type": owner_type,
            "owner_id": owner_id,
            "uploaded_by": user.get("user_id"),
            "file_name": file.filename,
            "file_kind": file_kind,
            "stored_file_path": str(saved_path),
            "content_type": file.content_type or "application/octet-stream",
            "category": analysis["category"],
            "summary": analysis["summary"],
            "keywords": analysis["keywords"],
            "text_preview": extracted[:500],
            "metadata_embedded": embedded,
        }
    )
    return note


@app.get("/notes/search")
def search_notes_endpoint(
    q: str = Query("", description="Search query"),
    owner_type: str | None = Query(None),
    owner_id: str | None = Query(None),
    file_kind: str | None = Query(None),
    _: dict = Depends(require_teacher),
) -> list[dict]:
    if owner_type and owner_type not in {"student", "teacher"}:
        raise HTTPException(status_code=400, detail="owner_type must be 'student' or 'teacher'")
    if file_kind and file_kind not in {"document", "image", "audio", "video", "other"}:
        raise HTTPException(status_code=400, detail="file_kind must be one of document/image/audio/video/other")
    return search_notes(q, owner_type, owner_id, file_kind)


@app.get("/notes/{note_id}")
def get_note_endpoint(note_id: str, _: dict = Depends(require_teacher)) -> dict:
    note = get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
