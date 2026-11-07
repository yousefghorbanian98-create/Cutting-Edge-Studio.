"""Owned scratch recovery using tempfile, Pydantic and psutil, never age-based deletion.

Only this version's marked directories are eligible. Unknown/launch-gap/live-process
states are retained; no process is killed, no recursive removal or legacy GC occurs.
The private per-user cache is trusted against malicious same-user filesystem races.
"""

from __future__ import annotations

import os
import stat
import tempfile
from itertools import islice
from pathlib import Path
from typing import Literal, Self

import psutil
from pydantic import BaseModel, ConfigDict, Field

from app.logging import get_logger

LOG = get_logger(__name__)
MARKER = ".owner.json"
ALLOWED = {"scenes": {"input"}, "rhythm": {"audio.wav", "result.json"}}
SCAN_LIMIT = 128


class ProcessIdentity(BaseModel):
    """PID alone is insufficient after process reuse."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    pid: int = Field(ge=1)
    created: float = Field(gt=0)

    @classmethod
    def current(cls, pid: int) -> Self:
        return cls(pid=pid, created=psutil.Process(pid).create_time())

    def alive(self) -> bool:
        try:
            process = psutil.Process(self.pid)
            return (
                process.create_time() == self.created and process.status() != psutil.STATUS_ZOMBIE
            )
        except psutil.NoSuchProcess:
            LOG.info("scratch.process.absent", pid=self.pid)
            return False


class Ownership(BaseModel):
    """Small atomic journal, not a source path or a command execution request."""

    model_config = ConfigDict(extra="forbid")
    format: Literal["cutting-edge.scratch.v1"] = "cutting-edge.scratch.v1"
    kind: Literal["scenes", "rhythm"]
    folder: str
    owner: ProcessIdentity
    launching: bool = False
    child: ProcessIdentity | None = None


def ordinary(path: Path, *, directory: bool = False) -> bool:
    """Reject symlinks and Windows reparse/junction entries without following them."""
    info = path.lstat()
    reparse = getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    return not reparse and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))


def remove_owned(path: Path, kind: str) -> None:
    """Remove only fixed known regular scratch files, never a recursive user subtree."""
    if not ordinary(path, directory=True):
        raise ValueError("Scratch path is not an ordinary directory")
    entries = list(islice(path.iterdir(), 6))
    allowed = ALLOWED[kind] | {MARKER, ".owner.tmp"}
    if any(entry.name not in allowed or not ordinary(entry) for entry in entries):
        raise ValueError("Unknown, linked or nested scratch content retained")
    # Preserve the ownership marker until the other files have been removed.
    for entry in sorted(entries, key=lambda p: p.name == MARKER):
        entry.unlink()
    path.rmdir()


class ScratchWorkspace:
    """Journal backend/native identities; let the runner prove reaping before cleanup."""

    def __init__(self, cache: Path, kind: Literal["scenes", "rhythm"]) -> None:
        self.cache, self.kind = cache, kind

    def __enter__(self) -> Self:
        self.path = Path(tempfile.mkdtemp(prefix=f"managed-{self.kind}-", dir=self.cache))
        self.record = Ownership(
            kind=self.kind, folder=self.path.name, owner=ProcessIdentity.current(os.getpid())
        )
        self.checkpoint()
        return self

    def checkpoint(self) -> None:
        """Atomically publish ownership before spawn and after confirmed reaping."""
        try:
            with (self.path / ".owner.tmp").open("w", encoding="utf-8") as stream:
                stream.write(self.record.model_dump_json())
                stream.flush()
                os.fsync(stream.fileno())
            (self.path / ".owner.tmp").replace(self.path / MARKER)
        except OSError as error:
            LOG.error("scratch.journal.failed", folder=self.path.name, error=str(error))
            raise RuntimeError(
                "Cannot journal local scratch ownership; measurement stopped safely"
            ) from error

    def before_spawn(self) -> None:
        self.record.launching, self.record.child = True, None
        self.checkpoint()

    def spawned(self, pid: int) -> None:
        try:
            self.record.child = ProcessIdentity.current(pid)
        except psutil.Error as error:
            LOG.error("scratch.child_identity.failed", error=str(error))
            raise RuntimeError(
                "Cannot identify native process; measurement stopped safely"
            ) from error
        self.record.launching = False
        self.checkpoint()

    def reaped(self) -> None:
        self.record.child, self.record.launching = None, False
        self.checkpoint()

    def __exit__(self, *_args: object) -> None:
        if self.record.launching or self.record.child is not None:
            LOG.error(
                "scratch.cleanup.retained",
                folder=self.path.name,
                message="Scratch retained: child reaping is unconfirmed; inspect local diagnostics",
            )
            return
        try:
            remove_owned(self.path, self.kind)
        except (OSError, ValueError) as error:
            LOG.error("scratch.cleanup.failed", folder=self.path.name, error=str(error))
            raise RuntimeError(
                "Local scratch cleanup failed; retained files need local diagnostics review"
            ) from error


def recover_one(path: Path) -> Literal["removed", "active"]:
    """Recover only proven inactive ownership, including native process identity."""
    if not ordinary(path, directory=True) or not ordinary(path / MARKER):
        raise ValueError("Missing ordinary ownership marker; nothing was deleted")
    with (path / MARKER).open("rb") as stream:
        payload = stream.read(4097)
    if len(payload) > 4096:
        raise ValueError("Oversized ownership marker; nothing was deleted")
    record = Ownership.model_validate_json(payload)
    if record.folder != path.name or not path.name.startswith(f"managed-{record.kind}-"):
        raise ValueError("Scratch folder and ownership disagree; nothing was deleted")
    if record.owner.alive() or (record.child is not None and record.child.alive()):
        return "active"
    if record.launching:
        raise ValueError("Unconfirmed process launch retained; no safe cleanup proof")
    remove_owned(path, record.kind)
    return "removed"


def recover_workspaces(cache: Path) -> dict[str, object]:
    """Bound startup scanning; expose all conservative retention/failure decisions."""
    report: dict[str, object] = {
        "removed": 0,
        "retained": 0,
        "scanned": 0,
        "limited": False,
        "message": "Only proven inactive marked scratch is removed; legacy cache is untouched.",
        "entries": [],
    }
    entries: list[dict[str, str]] = []
    removed = retained = scanned = 0
    try:
        with os.scandir(cache) as listing:
            for index, item in enumerate(islice(listing, SCAN_LIMIT + 1)):
                if index == SCAN_LIMIT:
                    report["limited"] = True
                    break
                if not item.name.startswith(("managed-scenes-", "managed-rhythm-")):
                    continue
                scanned += 1
                try:
                    state = recover_one(Path(item.path))
                    reason = (
                        "Process still active; retained without deletion"
                        if state == "active"
                        else "Inactive owned scratch removed"
                    )
                except (OSError, ValueError, psutil.Error) as error:
                    LOG.error("scratch.recovery.retained", folder=item.name, error=str(error))
                    state, reason = "active", str(error)
                removed += state == "removed"
                retained += state == "active"
                entries.append(
                    {
                        "folder": item.name,
                        "result": "removed" if state == "removed" else "retained",
                        "reason": reason,
                    }
                )
    except OSError as error:
        LOG.error("scratch.recovery.failed", error=str(error))
        report["message"] = (
            "Scratch recovery unavailable; no broad deletion attempted. "
            "Check local permissions/logs."
        )
        report["limited"] = True
    report.update(removed=removed, retained=retained, scanned=scanned, entries=entries)
    LOG.info("scratch.recovery.done", removed=removed, retained=retained, limited=report["limited"])
    return report
