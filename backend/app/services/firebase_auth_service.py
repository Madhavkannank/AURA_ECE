from typing import Any

from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from ..config import get_settings

try:
    import firebase_admin
    from firebase_admin import auth, credentials
except ImportError:  # pragma: no cover
    firebase_admin = None
    auth = None
    credentials = None


class FirebaseAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        if not firebase_admin or not auth or not credentials:
            raise HTTPException(status_code=500, detail="firebase-admin is not installed")

        if firebase_admin._apps:
            self._initialized = True
            return

        cred_path = (self.settings.firebase_credentials_path or "").strip()
        if cred_path:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
        self._initialized = True

    def verify_google_id_token(self, id_token: str) -> dict[str, Any]:
        if not id_token:
            raise HTTPException(status_code=400, detail="id_token is required")

        decoded: dict[str, Any] | None = None
        try:
            self._ensure_initialized()
            decoded = auth.verify_id_token(id_token, check_revoked=False)
        except Exception as exc:  # noqa: BLE001
            try:
                request = google_requests.Request()
                decoded = google_id_token.verify_firebase_token(id_token, request)
            except Exception as fallback_exc:  # noqa: BLE001
                raise HTTPException(status_code=401, detail="Invalid Firebase ID token") from fallback_exc

        if not decoded:
            raise HTTPException(status_code=401, detail="Invalid Firebase ID token")

        if self.settings.firebase_project_id and decoded.get("aud") != self.settings.firebase_project_id:
            raise HTTPException(status_code=401, detail="Token audience does not match Firebase project")

        return decoded


firebase_auth_service = FirebaseAuthService()
