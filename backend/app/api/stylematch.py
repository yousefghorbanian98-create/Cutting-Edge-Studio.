"""Style Match endpoints: artifacts, DNA, EDL and Golden-Set scoring."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.deps import SessionDep
from app.logging import get_logger
from app.models import Artifact, Project
from app.schemas_media import JobRead  # noqa: F401 - re-exported for the UI client
from app.services.stylematch.dna import extract_style_dna
from app.services.stylematch.edl import build_edl, snap_to_beats, validate_edl
from app.services.stylematch.pipeline import run_pipeline, score_against_reference

router = APIRouter(prefix="/projects/{project_id}/stylematch", tags=["style-match"])
LOG = get_logger(__name__)


class AnalysisPayload(BaseModel):
    """Reference or source analysis produced by the OSS adapters."""

    model_config = ConfigDict(extra="allow")

    analysis: dict[str, Any] = Field(default_factory=dict)


class ScorePayload(BaseModel):
    """Optional ground truth used when scoring a produced edit."""

    model_config = ConfigDict(extra="forbid")

    shot_confusion: dict[str, dict[str, int]] = Field(default_factory=dict)
    generated_color: dict[str, float] = Field(default_factory=dict)


def _project_or_404(session: SessionDep, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _store(session: SessionDep, project_id: str, kind: str, payload: dict[str, Any]) -> Artifact:
    revision = session.query(Artifact).filter_by(project_id=project_id, kind=kind).count() + 1
    artifact = Artifact(
        project_id=project_id,
        kind=kind,
        revision=revision,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    session.add(artifact)
    session.flush()
    LOG.info("stylematch.artifact", project_id=project_id, kind=kind, revision=revision)
    return artifact


def _latest(session: SessionDep, project_id: str, kind: str) -> dict[str, Any] | None:
    row = session.scalars(
        select(Artifact)
        .where(Artifact.project_id == project_id, Artifact.kind == kind)
        .order_by(Artifact.revision.desc())
        .limit(1)
    ).first()
    return json.loads(row.payload_json) if row is not None else None


@router.get("/artifacts", summary="List artifact kinds and revisions")
def list_artifacts(project_id: str, session: SessionDep) -> list[dict[str, Any]]:
    _project_or_404(session, project_id)
    rows = session.scalars(
        select(Artifact).where(Artifact.project_id == project_id).order_by(Artifact.created_at)
    ).all()
    return [
        {"kind": row.kind, "revision": row.revision, "created_at": row.created_at.isoformat()}
        for row in rows
    ]


@router.get("/artifacts/{kind}", summary="Latest artifact payload")
def get_artifact(project_id: str, kind: str, session: SessionDep) -> dict[str, Any]:
    _project_or_404(session, project_id)
    payload = _latest(session, project_id, kind)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"artifact '{kind}' not found"
        )
    return payload


@router.post(
    "/reference",
    status_code=status.HTTP_201_CREATED,
    summary="Stage 1 — register reference DNA source",
)
def save_reference(
    project_id: str, payload: AnalysisPayload, session: SessionDep
) -> dict[str, Any]:
    _project_or_404(session, project_id)
    artifact = _store(session, project_id, "reference-manifest", payload.analysis)
    return {"kind": artifact.kind, "revision": artifact.revision}


@router.post("/dna", status_code=status.HTTP_201_CREATED, summary="Stage 2 — extract StyleDNA")
def extract_dna(project_id: str, payload: AnalysisPayload, session: SessionDep) -> dict[str, Any]:
    _project_or_404(session, project_id)
    dna = extract_style_dna(payload.analysis)
    _store(session, project_id, "style-dna", dict(dna))
    return dict(dna)


@router.post("/edl", status_code=status.HTTP_201_CREATED, summary="Stages 3-6 — build the EDL")
def create_edl(
    project_id: str,
    payload: AnalysisPayload,
    session: SessionDep,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
) -> dict[str, Any]:
    _project_or_404(session, project_id)
    reference = _latest(session, project_id, "reference-manifest")
    if reference is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="run stage 1 (reference) first"
        )
    result = run_pipeline(reference, payload.analysis, fps=fps, width=width, height=height)
    _store(session, project_id, "source-analysis", result.source)
    _store(session, project_id, "compatibility-report", result.compatibility)
    _store(session, project_id, "edl", dict(result.edl))
    _store(session, project_id, "edl-v2", dict(result.edl_v2))
    if result.problems:
        LOG.warning("stylematch.problems", project_id=project_id, problems=result.problems)
    return {
        "edl": result.edl,
        "edl_v2": result.edl_v2,
        "compatibility": result.compatibility,
        "problems": result.problems,
    }


@router.post("/score", summary="G12 — score an EDL against the reference DNA")
def score(project_id: str, payload: ScorePayload, session: SessionDep) -> dict[str, Any]:
    _project_or_404(session, project_id)
    dna = _latest(session, project_id, "style-dna")
    edl = _latest(session, project_id, "edl-v2") or _latest(session, project_id, "edl")
    if dna is None or edl is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="dna and edl are required")
    result = score_against_reference(
        edl,
        dna,
        shot_confusion=payload.shot_confusion,
        generated_color=payload.generated_color or None,
    )
    _store(session, project_id, "match-score", result)
    return result


@router.get("/edl/validate", summary="Validate the stored EDL")
def validate(project_id: str, session: SessionDep) -> dict[str, Any]:
    _project_or_404(session, project_id)
    edl = _latest(session, project_id, "edl-v2")
    if edl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no EDL stored")
    return {"problems": validate_edl(edl)}


_ = (build_edl, snap_to_beats)  # imported for type-checkers/readers of this module
