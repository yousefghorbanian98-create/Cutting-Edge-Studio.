"""ORM behaviour: cascades and serialization helpers."""

from __future__ import annotations

from pathlib import Path

from app.db import create_db_engine, create_session_factory, init_db
from app.models import Artifact, Bookmark, MediaAsset, Project, as_dict
from sqlalchemy import select


def _factory(tmp_path: Path):
    engine = create_db_engine(f"sqlite+pysqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    return engine, create_session_factory(engine)


def test_cascade_delete_removes_children(tmp_path: Path) -> None:
    engine, factory = _factory(tmp_path)
    with factory() as session:
        project = Project(name="Cascade")
        project.assets.append(MediaAsset(path="a.mp4", role="source"))
        project.bookmarks.append(Bookmark(timecode=1.5, label="peak"))
        project.artifacts.append(Artifact(kind="style-dna", payload_json="{}"))
        session.add(project)
        session.commit()
        project_id = project.id

    with factory() as session:
        session.delete(session.get(Project, project_id))
        session.commit()

    with factory() as session:
        assert session.scalars(select(MediaAsset)).all() == []
        assert session.scalars(select(Bookmark)).all() == []
        assert session.scalars(select(Artifact)).all() == []
    engine.dispose()


def test_artifact_revision_and_kind_index(tmp_path: Path) -> None:
    engine, factory = _factory(tmp_path)
    with factory() as session:
        project = Project(name="Artifacts")
        session.add(project)
        session.flush()
        for revision in (1, 2):
            session.add(Artifact(project_id=project.id, kind="edl", revision=revision))
        session.commit()
        rows = session.scalars(select(Artifact).order_by(Artifact.revision)).all()
        assert [row.revision for row in rows] == [1, 2]
    engine.dispose()


def test_as_dict_drops_excluded_columns(tmp_path: Path) -> None:
    engine, factory = _factory(tmp_path)
    with factory() as session:
        project = Project(name="Serialize")
        session.add(project)
        session.commit()
        payload = as_dict(project, exclude={"created_at", "updated_at"})
        assert set(payload) == {
            "id",
            "name",
            "mode",
            "sport",
            "language",
            "width",
            "height",
            "fps",
            "state_json",
        }
    engine.dispose()


def test_sqlite_pragmas_are_applied(tmp_path: Path) -> None:
    engine, factory = _factory(tmp_path)
    with factory() as session:
        assert session.execute(select(1)).scalar_one() == 1
        journal_mode = session.connection().exec_driver_sql("PRAGMA journal_mode").scalar_one()
        foreign_keys = session.connection().exec_driver_sql("PRAGMA foreign_keys").scalar_one()
    assert str(journal_mode).lower() == "wal"
    assert foreign_keys == 1
    engine.dispose()
