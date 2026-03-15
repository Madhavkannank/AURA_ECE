from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Aura-ECE API"
    app_env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:8501,http://127.0.0.1:8501"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "aura_ece"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_reasoning_model: str = "llama-3.3-70b-versatile"
    groq_light_model: str = "llama-3.1-8b-instant"
    groq_whisper_model: str = "whisper-large-v3"

    default_report_frequency: str = "weekly"
    fallback_parent_language: str = "en"
    report_scheduler_enabled: bool = False
    report_scheduler_period: str = "weekly"
    report_scheduler_interval_minutes: int = 60

    auth_secret_key: str = "change-me-in-production"
    auth_algorithm: str = "HS256"
    auth_token_expire_minutes: int = 480
    auth_issuer: str = "aura-ece"
    auth_audience: str = "aura-ece-clients"
    allow_bootstrap_auth: bool = True

    firebase_project_id: str = ""
    firebase_web_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_app_id: str = ""
    firebase_credentials_path: str = ""
    teacher_email_domain: str = ""

    notes_storage_path: str = "data/notes"
    notes_max_chars: int = 12000
    notes_chunk_chars: int = 3000

    @field_validator("allow_bootstrap_auth", mode="before")
    @classmethod
    def default_bootstrap_for_env(cls, value: bool | str | None, info):
        if value is not None:
            return value
        app_env = str(info.data.get("app_env", "dev")).lower()
        return app_env == "dev"

    @model_validator(mode="after")
    def validate_non_dev_mongo_uri(self):
        if self.app_env.lower() == "dev":
            return self

        # In non-dev, require credentials in URI to avoid accidental open Mongo usage.
        if "@" not in self.mongo_uri:
            raise ValueError("MONGO_URI must include credentials in non-dev environments")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
