"""The only configuration loader (T-2.1.1, R-03, R-06).

Read once from environment variables and validated at start. A missing or
malformed value stops the process with a clear message. ``fingerprint()`` is a
hash of the validated non-secret settings; API and workers compare it (I-21).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

SECRET_FIELDS = frozenset({"session_secret", "totp_encryption_key", "smtp_password", "s3_secret_access_key",
                           "s3_access_key_id"})


class ConfigError(SystemExit):
    pass


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    env: Literal["local", "test", "staging", "production"]
    database_url: str
    migration_database_url: str
    redis_url: str
    public_base_url: str
    object_store_root: str
    session_secret: str = Field(min_length=32)
    llm_provider: Literal["fake"] = "fake"
    llm_model_id: str = "fake-llm-0"
    asr_provider: Literal["fake"] = "fake"
    asr_model_id: str = "fake-asr-0"
    prompt_version: str = "prompt-2026.11.1"
    retention_audio_days_after_approval_default: int = Field(default=14, ge=1, le=60)
    api_port: int = 8106
    session_idle_seconds: int = 60 * 60
    session_absolute_seconds: int = 12 * 60 * 60
    # Sign-in (B2, TRD "Identity and tenancy"): emailed link plus authenticator code.
    totp_encryption_key: str
    sign_in_link_seconds: int = 10 * 60
    # Email through SMTP; local Mailpit by default, a real provider later by settings only.
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    email_from: str = "StrataScribe <sign-in@stratascribe.example>"
    # Object storage: the local file store or any S3-compatible store (local MinIO).
    storage_backend: Literal["local", "s3"] = "local"
    s3_endpoint_url: str = ""
    s3_region: str = "us-east-1"
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    object_store_prefix: str = ""

    @field_validator("public_base_url")
    @classmethod
    def _base_url(cls, v: str) -> str:
        u = urlparse(v)
        if u.scheme not in ("http", "https") or not u.netloc or u.path not in ("", "/"):
            raise ValueError("PUBLIC_BASE_URL must be an origin such as https://app.example.ca")
        return v.rstrip("/")

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def _db(cls, v: str) -> str:
        if not v.startswith("postgresql+psycopg://"):
            raise ValueError("must start with postgresql+psycopg://")
        return v

    @field_validator("totp_encryption_key")
    @classmethod
    def _totp_key(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("must be base64 of 32 random bytes") from None
        if len(raw) != 32:
            raise ValueError("must be base64 of 32 random bytes")
        return v

    @field_validator("object_store_prefix")
    @classmethod
    def _prefix(cls, v: str) -> str:
        if v and (not v.endswith("/") or v.startswith("/") or ".." in v):
            raise ValueError("must be empty or a relative prefix ending in /")
        return v

    @model_validator(mode="after")
    def _s3_complete(self) -> Settings:
        if self.storage_backend == "s3":
            missing = [n for n in ("s3_endpoint_url", "s3_bucket", "s3_access_key_id", "s3_secret_access_key")
                       if not getattr(self, n)]
            if missing:
                raise ValueError("STORAGE_BACKEND=s3 needs " + ", ".join(ENV_MAP[n] for n in missing))
        return self

    def fingerprint(self) -> str:
        data = {k: v for k, v in self.model_dump().items() if k not in SECRET_FIELDS}
        raw = json.dumps(data, sort_keys=True, default=str).encode()
        return hashlib.sha256(raw).hexdigest()[:16]


ENV_MAP = {
    "env": "STRATASCRIBE_ENV",
    "database_url": "DATABASE_URL",
    "migration_database_url": "MIGRATION_DATABASE_URL",
    "redis_url": "REDIS_URL",
    "public_base_url": "PUBLIC_BASE_URL",
    "object_store_root": "OBJECT_STORE_ROOT",
    "session_secret": "SESSION_SECRET",
    "llm_provider": "LLM_PROVIDER",
    "llm_model_id": "LLM_MODEL_ID",
    "asr_provider": "ASR_PROVIDER",
    "asr_model_id": "ASR_MODEL_ID",
    "prompt_version": "PROMPT_VERSION",
    "retention_audio_days_after_approval_default": "RETENTION_AUDIO_DAYS_AFTER_APPROVAL_DEFAULT",
    "api_port": "API_PORT",
    "totp_encryption_key": "TOTP_ENCRYPTION_KEY",
    "smtp_host": "SMTP_HOST",
    "smtp_port": "SMTP_PORT",
    "smtp_username": "SMTP_USERNAME",
    "smtp_password": "SMTP_PASSWORD",
    "smtp_starttls": "SMTP_STARTTLS",
    "email_from": "EMAIL_FROM",
    "storage_backend": "STORAGE_BACKEND",
    "s3_endpoint_url": "S3_ENDPOINT_URL",
    "s3_region": "S3_REGION",
    "s3_bucket": "S3_BUCKET",
    "s3_access_key_id": "S3_ACCESS_KEY_ID",
    "s3_secret_access_key": "S3_SECRET_ACCESS_KEY",
    "object_store_prefix": "OBJECT_STORE_PREFIX",
}


def load(environ: dict[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    raw = {field: source[var] for field, var in ENV_MAP.items() if var in source}
    try:
        return Settings.model_validate(raw)
    except ValidationError as exc:
        lines = []
        for err in exc.errors():
            field = str(err["loc"][0]) if err["loc"] else "settings"
            lines.append(f"  {ENV_MAP.get(field, field)}: {err['msg']}")
        raise ConfigError("Invalid configuration:\n" + "\n".join(lines)) from None


@lru_cache(maxsize=1)
def settings() -> Settings:
    return load()


def reset() -> None:
    settings.cache_clear()
