"""Project CRUD. Everything is stored in the local SQLite file."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.deps import SessionDep
from app.models import Project
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])

NOT_FOUND = "Project not found"


def _get_or_404(session: SessionDep, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return project


@router.get("", response_model=list[ProjectRead], summary="List projects")
def list_projects(session: SessionDep) -> list[Project]:
    """Return every project, newest first."""
    return list(session.scalars(select(Project).order_by(Project.created_at.desc())))


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: SessionDep) -> Project:
    """Create a project. Style Match is the default mode (LOCK-02)."""
    project = Project(**payload.model_dump())
    session.add(project)
    session.flush()
    return project


@router.get("/{project_id}", response_model=ProjectRead, summary="Get one project")
def get_project(project_id: str, session: SessionDep) -> Project:
    """Fetch a single project by id."""
    return _get_or_404(session, project_id)


@router.patch("/{project_id}", response_model=ProjectRead, summary="Update a project")
def update_project(project_id: str, payload: ProjectUpdate, session: SessionDep) -> Project:
    """Apply a partial update; unknown ids raise 404 instead of silently passing."""
    project = _get_or_404(session, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(project, field, value)
    session.flush()
    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete project",
)
def delete_project(project_id: str, session: SessionDep) -> Response:
    """Delete a project and (by cascade) its assets, bookmarks and artifacts."""
    session.delete(_get_or_404(session, project_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
