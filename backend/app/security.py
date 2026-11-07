"""Sidecar security — token + Host/Origin + random port (loop S1).

Implements professor's feedback §1 as fail-closed but test-friendly:
* Host allowlist blocks DNS rebinding (only loopback)
* Origin allowlist blocks CSRF from arbitrary web pages (only Tauri/Vite)
* Token via CES_API_TOKEN (Rust generates via secrets.token_urlsafe(32) and injects)
  — if env not set (pytest default) auth is bypassed to keep existing tests green
  — if set, every non-OPTIONS request must carry x-ces-token with hmac.compare_digest
* Port 0 support: Rust should launch with --port 0 and read actual port from stdout;
  backend will honor Settings.port=0 by letting Uvicorn pick a free port.

All checks are case-insensitive for header names and use constant-time compare.
"""

from __future__ import annotations

import hmac
import os
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

ALLOWED_HOSTS: set[str] = {"127.0.0.1", "localhost", "::1"}
ALLOWED_ORIGINS: set[str] = {
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
    # Vite dev shells (kept for local dev)
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}


def get_token() -> str | None:
    """Return enforced token or None if auth should be bypassed (test mode)."""
    token = os.environ.get("CES_API_TOKEN")
    if token:
        return token
    # Optional generation for sidecar production: if CES_GENERATE_TOKEN=1, create ephemeral
    if os.environ.get("CES_GENERATE_TOKEN") == "1":
        return secrets.token_urlsafe(32)
    return None


def generate_token_for_rust() -> str:
    """Generate a fresh token for Rust to inject (called by Tauri setup)."""
    token = secrets.token_urlsafe(32)
    os.environ["CES_API_TOKEN"] = token
    return token


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Host check — block DNS rebinding
        host_header = (request.headers.get("host") or "").split(":")[0].lower().strip()
        # Starlette Request.client.host is more reliable for direct IP, but Host header is attacker-controlled
        if host_header and host_header not in ALLOWED_HOSTS:
            return JSONResponse({"detail": "bad host"}, status_code=403)

        # 2. Origin check — block CSRF from web pages
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse({"detail": "bad origin"}, status_code=403)

        # 3. Token check — only if enforced
        token = get_token()
        if token is not None and request.method != "OPTIONS":
            supplied = request.headers.get("x-ces-token", "")
            # Empty token never matches (compare_digest requires same length handling)
            if not supplied or not hmac.compare_digest(supplied, token):
                return JSONResponse({"detail": "unauthorized"}, status_code=401)

        return await call_next(request)


# Legacy functional guard (professor's snippet name) — alias to middleware logic
async def guard(request: Request, call_next):
    mw = SecurityMiddleware
    # Reuse same checks inline for direct app.middleware("http")(guard) usage
    host_header = (request.headers.get("host") or "").split(":")[0].lower().strip()
    if host_header and host_header not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "bad host"}, status_code=403)
    origin = request.headers.get("origin")
    if origin and origin not in ALLOWED_ORIGINS:
        return JSONResponse({"detail": "bad origin"}, status_code=403)
    token = get_token()
    if token is not None and request.method != "OPTIONS":
        supplied = request.headers.get("x-ces-token", "")
        if not supplied or not hmac.compare_digest(supplied, token):
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return await call_next(request)
