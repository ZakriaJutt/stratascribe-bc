"""The only configuration loader (T-2.1.1, R-03, R-06).

Read once from environment variables and validated at start. A missing or
malformed value stops the process with a clear message. ``fingerprint()`` is a
hash of the validated non-secret settings; API and workers compare it (I-21).
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

SECRET_FIELDS = frozenset({"session_secret"})


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
}


def load(environ: dict[str, str] | None = None) -> Settings:
    source = os.environ if environ is None else environ
    raw = {field: source[var] for field, var in ENV_MAP.items() if var in source}
    try:
        return Settings.model_validate(raw)
    except ValidationError as exc:
        lines = []
        for err in exc.errors():
            field = str(err["loc"][0]) if err["loc"] else "?"
            lines.append(f"  {ENV_MAP.get(field, field)}: {err['msg']}")
        raise ConfigError("Invalid configuration:\n" + "\n".join(lines)) from None


@lru_cache(maxsize=1)
def settings() -> Settings:
    return load()


def reset() -> None:
    settings.cache_clear()
