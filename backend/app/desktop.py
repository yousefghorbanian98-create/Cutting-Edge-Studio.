"""Same-origin desktop assets and a per-launch readiness receipt, using Starlette/Pydantic.

The receipt is NOT authentication. Only the CLI with an already-owned listening
socket may publish it; a random service on the fixed port is not readiness.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from app.config import Settings
from app.logging import get_logger

LOG = get_logger(__name__)
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self' data:; media-src 'self' blob:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'"
)


class DesktopReceipt(BaseModel):
    """A bounded JSON handshake, not a custom HTTP parser or an authorization token."""

    model_config = ConfigDict(extra="forbid")
    version: int = 1
    instance_id: str
    origin: str
    home: str
    frontend_ready: bool = True


def origin(settings: Settings) -> str:
    return f"http://127.0.0.1:{settings.port}"


class DesktopBoundary(BaseHTTPMiddleware):
    """Desktop-only host/origin boundary; standalone preview keeps same-origin relative URLs."""

    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = settings

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        managed = self.settings.desktop_instance_id is not None
        if managed and (
            request.headers.get("host") != f"127.0.0.1:{self.settings.port}"
            or request.headers.get("origin", origin(self.settings)) != origin(self.settings)
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            LOG.error("desktop.request.rejected", message="Unexpected desktop host/origin")
            return Response("Desktop request host/origin rejected", status_code=403)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP + (
            "; frame-ancestors 'none'" if managed else ""
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


def mount_frontend(app: FastAPI, settings: Settings) -> None:
    """Mount ONLY the built frontend, after API routes; no SPA fallback over API errors."""
    root = settings.home_dir / "frontend"
    if not (root / "index.html").is_file():
        LOG.error("desktop.frontend.missing", path=str(root))
        raise RuntimeError("Built frontend is missing; repair the installed resources")
    app.add_middleware(DesktopBoundary, settings=settings)
    app.mount("/", StaticFiles(directory=root, html=True, follow_symlink=False), name="desktop")


def publish_receipt(settings: Settings, *, listener_owned: bool) -> None:
    """Publish only after application startup with a pre-bound owned desktop socket."""
    if settings.desktop_instance_id is None:
        return
    if not settings.serve_frontend or not listener_owned or settings.desktop_ready_file is None:
        LOG.error(
            "desktop.readiness.invalid", message="Managed desktop requires the native CLI entry"
        )
        raise RuntimeError("Managed desktop startup requires an owned listener and built frontend")
    receipt = DesktopReceipt(
        instance_id=settings.desktop_instance_id,
        origin=origin(settings),
        home=str(settings.home_dir),
    )
    target = settings.desktop_ready_file
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(receipt.model_dump_json())
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
    except OSError as error:
        LOG.error("desktop.readiness.failed", error=str(error))
        raise RuntimeError(
            "Cannot publish desktop readiness; inspect local cache permissions"
        ) from error


def clear_receipt(settings: Settings) -> None:
    """Delete only this launch's receipt, never a different or unrecognized marker."""
    target = settings.desktop_ready_file
    if target is None or not target.exists():
        return
    try:
        with target.open("rb") as stream:
            body = stream.read(4097)
        if (
            len(body) > 4096
            or DesktopReceipt.model_validate_json(body).instance_id != settings.desktop_instance_id
        ):
            LOG.error(
                "desktop.readiness.changed", message="Receipt retained; review local diagnostics"
            )
            return
        target.unlink()
    except (OSError, ValueError) as error:
        LOG.error(
            "desktop.readiness.cleanup_failed",
            error=str(error),
            message="Receipt retained; review local diagnostics",
        )
