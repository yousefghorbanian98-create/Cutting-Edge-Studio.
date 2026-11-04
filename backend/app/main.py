"""FastAPI application factory for the Cutting Edge v2 backend sidecar."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    assets,
    health,
    inspection,
    post,
    projects,
    settings_api,
    stylematch,
    system,
    uploads,
    workspace,
)
from app.config import ALLOWED_ORIGINS, API_PREFIX, Settings, get_settings
from app.db import create_db_engine, create_session_factory, init_db
from app.logging import configure_logging, get_logger
from app.services.audio.processor import FFmpegRhythmInspector
from app.services.media.inspection import FFmpegInspector, InspectionService
from app.services.media.jobs import JobRegistry
from app.services.media.scenes import FFmpegSceneInspector
from app.services.media.service import MediaService, Prober

LOG = get_logger(__name__)


def create_app(settings: Settings | None = None, prober: Prober | None = None) -> FastAPI:
    """Build the ASGI app bound to ``settings`` (explicit settings help tests)."""
    resolved = settings or get_settings()
    resolved.ensure_dirs()
    configure_logging(
        resolved.log_level,
        resolved.logs_dir / "backend.jsonl" if resolved.log_to_file else None,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_db_engine(resolved.database_url)
        init_db(engine)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.inspection = InspectionService(
            app.state.session_factory,
            app.state.jobs,
            FFmpegInspector(resolved),
            rhythm_inspector=FFmpegRhythmInspector(resolved),
            scene_inspector=FFmpegSceneInspector(resolved),
        )
        LOG.info(
            "backend.startup",
            version=resolved.version,
            data_dir=str(resolved.data_dir),
            offline=resolved.offline,
        )
        try:
            yield
        finally:
            app.state.inspection.shutdown()
            engine.dispose()
            LOG.info("backend.shutdown")

    app = FastAPI(
        title="Cutting Edge v2",
        version=resolved.version,
        description="Local-first sports video editor backend. No telemetry, no network at runtime.",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.media_service = MediaService(resolved, prober)
    app.state.jobs = JobRegistry()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["content-type"],
    )
    for module in (
        health,
        settings_api,
        projects,
        assets,
        uploads,
        stylematch,
        post,
        system,
        workspace,
        inspection,
    ):
        app.include_router(module.router, prefix=API_PREFIX)
    return app


app = create_app()
