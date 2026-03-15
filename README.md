# Aura-ECE Multimodal Early Childhood Education Intelligence Platform

Aura-ECE is a working prototype that transforms raw classroom observations into structured developmental insights and parent-ready communication.

## Core Features

- Multimodal teacher input: text or voice observations (Whisper-large-v3 via Groq)
- Privacy-aware processing: Presidio PII masking before external AI calls
- Notes AI indexing: upload note files, extract text/OCR, classify with Groq, embed metadata, and search
- AI developmental reasoning: domain classification + confidence tagging
- Trend analysis: 30-day domain trend outcomes (Progressing, Stagnating, Excelling)
- Report generation: Teacher Assessment + Parent Summary
- Multilingual communication: translated parent summaries by preferred language
- Human-in-the-loop: teacher approval before parent delivery
- Parent guidance: structured home activity suggestions in each report
- Automated cycles: batch weekly/monthly report run endpoint + optional scheduler

## Product Blueprint

- Detailed multimodal feature and reporting specification: [docs/AURA_ECE_Multimodal_Feature_Set.md](docs/AURA_ECE_Multimodal_Feature_Set.md)

## Tech Stack

- Frontend: Streamlit (`streamlit_app.py`)
- Backend: FastAPI (`backend/app/main.py`)
- AI inference: Groq API
- LLMs: Llama-3.3-70B (reasoning/reporting), Llama-3.1-8B-Instant (classification/correction/translation)
- Speech recognition: Whisper-large-v3
- Database: MongoDB
- Privacy layer: Microsoft Presidio

## Project Structure

```text
backend/
  app/
    main.py
    config.py
    database.py
    models/schemas.py
    services/
      groq_client.py
      input_engine.py
      privacy_service.py
      reasoning_service.py
      report_service.py
      repository.py
      scheduler_service.py
streamlit_app.py
requirements.txt
.env.example
README.md
```

## Setup

1. Create Python environment and install backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Configure environment:

```powershell
Copy-Item .env.example .env
```

Minimum required keys:

- `MONGO_URI`
- `MONGO_DB`
- `GROQ_API_KEY`
- `AUTH_SECRET_KEY`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_WEB_API_KEY`
- `FIREBASE_AUTH_DOMAIN`
- `FIREBASE_APP_ID`

Optional scheduler keys:

- `REPORT_SCHEDULER_ENABLED` (`true` or `false`)
- `REPORT_SCHEDULER_PERIOD` (`weekly` or `monthly`)
- `REPORT_SCHEDULER_INTERVAL_MINUTES` (default `60`)

Security/auth hardening keys:

- `CORS_ALLOWED_ORIGINS` (comma-separated list, example: `http://localhost:8501`)
- `AUTH_ISSUER` (JWT issuer claim)
- `AUTH_AUDIENCE` (JWT audience claim)
- `ALLOW_BOOTSTRAP_AUTH` (`false` for non-dev environments)

3. Start backend API:

```powershell
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Start frontend UI (Streamlit):

```powershell
streamlit run streamlit_app.py
```

5. Open app:

- Frontend: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`

## Tests

Run integration tests (requires backend + MongoDB reachable):

```powershell
.\.venv\Scripts\python -m pytest -q
```

If backend dependencies are unavailable, integration tests are skipped instead of failing.

## Authentication

- Firebase Google login: `POST /auth/firebase-google`
- Optional demo bootstrap endpoint: `POST /auth/bootstrap`
- Bearer token required for protected routes.

### Firebase Google Auth Setup

1. Create Firebase project and enable Google provider.
2. Add `localhost` to Firebase Authentication authorized domains.
3. Set Firebase env vars listed above.
4. Restart backend and frontend.

## End-to-End Pipeline

1. Teacher submits voice or text observation.
2. Audio is transcribed with Whisper.
3. Observation text is PII-masked with Presidio.
4. Transcript is corrected against class roster context.
5. LLM classifies developmental domain and tags.
6. Observation is stored in MongoDB.
7. Reports are generated (manual student run or batch cycle).
8. Parent summary is translated to preferred language.
9. Teacher approves report before parents can access it.
10. Teachers can upload note files for AI keyword classification and metadata indexing.

## API Highlights

- `POST /auth/firebase-google`
- `POST /students`
- `GET /students`
- `POST /observations/process`
- `POST /observations/video-process`
- `GET /students/{student_id}/insights`
- `POST /reports/generate/{student_id}`
- `POST /reports/class/generate/{class_id}`
- `GET /reports/class/{class_id}`
- `POST /reports/class/{class_id}/view`
- `POST /reports/run-cycle`
- `GET /reports/scheduler-status`
- `GET /system/self-test?run_live_models=false|true`
- `POST /reports/{report_id}/approve`
- `GET /parents/{parent_id}/reports`
- `POST /notes/analyze-upload`
- `GET /notes/search`
- `GET /notes/{note_id}`

## Architecture Note

- Backend is intentionally implemented with FastAPI + PyMongo.

## Notes

- If `GROQ_API_KEY` is missing, fallback logic keeps core flows functional with heuristic behavior.
- Presidio may require additional NLP assets; regex fallback masking is used when unavailable.
- Rotate secrets (`AUTH_SECRET_KEY`, Groq key, Firebase credentials) before any non-local deployment.
- In non-dev environments, do not use the default `AUTH_SECRET_KEY`; the app enforces this at startup.
- In non-dev environments, `MONGO_URI` must include credentials (for example `mongodb://user:pass@host:27017/db`).
- `GET /system/self-test` returns HTTP 200 when healthy and HTTP 503 when one or more checks are degraded.
- MongoDB indexes for core query paths are created automatically at backend startup.
