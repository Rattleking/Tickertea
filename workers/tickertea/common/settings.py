"""Worker runtime settings.

Loaded from the environment, with a tiny built-in `.env` loader so the workers read the
same `.env.local` the Next.js app uses (no extra dependency on python-dotenv). Precedence:
real environment variables win; then `.env.local`; then `.env` at the repo root.

The write path connects as the TRUSTED role via DATABASE_ADMIN_URL (the Neon owner / table
owner), which bypasses RLS by the standard Postgres table-owner rule. See migration 0011.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# common/ -> tickertea/ -> workers/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILES = (".env.local", ".env")


def _load_env_files() -> None:
    """Populate os.environ from repo-root .env files without overriding real env vars."""
    for name in _ENV_FILES:
        path = _REPO_ROOT / name
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


class SettingsError(RuntimeError):
    """A required setting is missing."""


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise SettingsError(
            f"missing required env var {key!r}. Set it in {_REPO_ROOT / '.env.local'}"
        )
    return value


@dataclass(frozen=True)
class Settings:
    database_admin_url: str
    db_pool_max: int
    s3_endpoint: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str
    s3_region: str
    claude_api_key: str | None

    @property
    def has_claude(self) -> bool:
        return bool(self.claude_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_files()
    return Settings(
        database_admin_url=_require("DATABASE_ADMIN_URL"),
        db_pool_max=int(os.environ.get("DB_POOL_MAX", "10")),
        s3_endpoint=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
        s3_bucket=os.environ.get("S3_BUCKET", "tickertea-raw"),
        s3_access_key=os.environ.get("S3_ACCESS_KEY", "tickertea"),
        s3_secret_key=os.environ.get("S3_SECRET_KEY", "tickertea-secret"),
        s3_region=os.environ.get("S3_REGION", "us-east-1"),
        claude_api_key=os.environ.get("CLAUDE_API_KEY") or None,
    )
