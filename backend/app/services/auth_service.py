from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import get_settings
from .repository import get_user_by_user_id


class AuthService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.security = HTTPBearer(auto_error=True)
        if self.settings.app_env.lower() != "dev":
            secret = str(self.settings.auth_secret_key or "")
            weak_markers = ["change-me", "change-in-production", "default", "example", "test"]
            if len(secret) < 24:
                raise RuntimeError("AUTH_SECRET_KEY must be at least 24 characters in non-dev environments")
            if any(marker in secret.lower() for marker in weak_markers):
                raise RuntimeError("AUTH_SECRET_KEY appears to be a placeholder in non-dev environments")

    def hash_password(self, password: str) -> str:
        salted = f"{self.settings.auth_secret_key}:{password}"
        return sha256(salted.encode("utf-8")).hexdigest()

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        return hmac.compare_digest(self.hash_password(plain_password), password_hash)

    def authenticate_user(self, user_id: str, password: str) -> dict[str, Any] | None:
        user = get_user_by_user_id(user_id)
        if not user:
            return None
        if not self.verify_password(password, user.get("password_hash", "")):
            return None
        return user

    def create_access_token(self, user: dict[str, Any]) -> str:
        expires = datetime.now(timezone.utc) + timedelta(minutes=self.settings.auth_token_expire_minutes)
        payload = {
            "sub": user["user_id"],
            "role": user["role"],
            "parent_id": user.get("parent_id"),
            "exp": expires,
            "iat": datetime.now(timezone.utc),
            "iss": self.settings.auth_issuer,
            "aud": self.settings.auth_audience,
        }
        return jwt.encode(payload, self.settings.auth_secret_key, algorithm=self.settings.auth_algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self.settings.auth_secret_key,
                algorithms=[self.settings.auth_algorithm],
                issuer=self.settings.auth_issuer,
                audience=self.settings.auth_audience,
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            ) from exc

    def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
    ) -> dict[str, Any]:
        payload = self.decode_token(credentials.credentials)
        user = get_user_by_user_id(payload.get("sub", ""))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user


auth_service = AuthService()


def require_teacher(user: dict[str, Any] = Depends(auth_service.get_current_user)) -> dict[str, Any]:
    if user.get("role") != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher role required")
    return user


def require_parent_or_teacher(user: dict[str, Any] = Depends(auth_service.get_current_user)) -> dict[str, Any]:
    if user.get("role") not in {"parent", "teacher"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid role")
    return user
