"""Security helpers: environment checks, OAuth allowlist, CSRF, blob path validation."""

from __future__ import annotations

import logging
import os
import secrets
from typing import FrozenSet, Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def is_production_runtime() -> bool:
    """True when running on Cloud Run or when ENVIRONMENT is production."""
    if os.environ.get("K_SERVICE"):
        return True
    env = os.environ.get("ENVIRONMENT", "").lower()
    return env in ("production", "prod")


def parse_admin_email_allowlist(admin_emails: str) -> Optional[FrozenSet[str]]:
    """Return a lowercase email set, or None if unset (not configured)."""
    raw = (admin_emails or "").strip()
    if not raw:
        return None
    return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())


def oauth_email_allowed(email: Optional[str], admin_emails: str) -> bool:
    """
    If ADMIN_EMAILS is set, only listed emails may sign in.

    If unset: allow any Google account in non-production; in production, deny
    (configure ADMIN_EMAILS for production deploys).
    """
    allow = parse_admin_email_allowlist(admin_emails)
    if allow is not None:
        if not email:
            return False
        return email.lower() in allow
    if is_production_runtime():
        return False
    return True


def ensure_csrf_token(request: Request) -> str:
    """Ensure session has a CSRF token and return it."""
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def verify_csrf_token(request: Request, submitted: str) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not secrets.compare_digest(expected, submitted):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def trusted_proxy_hosts_from_setting(value: str) -> list[str] | str:
    """Parse TRUSTED_PROXY_HOSTS: '*' or comma-separated host/IP list."""
    v = (value or "*").strip()
    if v == "*":
        return "*"
    parts = [p.strip() for p in v.split(",") if p.strip()]
    return parts if parts else "*"


def validate_image_blob_path(image_path: str) -> None:
    """
    Reject empty, absolute, traversal-like, or control-character paths for GCS object names.
    """
    if not image_path or image_path.strip() != image_path:
        raise HTTPException(status_code=400, detail="Invalid image path")
    if image_path.startswith(("/", "\\")) or ".." in image_path:
        raise HTTPException(status_code=400, detail="Invalid image path")
    if "\x00" in image_path or any(ord(c) < 32 for c in image_path):
        raise HTTPException(status_code=400, detail="Invalid image path")
    if len(image_path) > 1024:
        raise HTTPException(status_code=400, detail="Invalid image path")
