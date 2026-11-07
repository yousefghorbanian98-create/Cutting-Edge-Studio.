#!/usr/bin/env python3
"""Local verification runner: the same gates CI enforces, in one command.

Usage: ``python scripts/verify.py [--skip-frontend] [--skip-installer]``
Exit code 0 means every executed gate passed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def run(name: str, command: list[str], cwd: Path) -> bool:
    """Run one gate and report pass/fail without raising."""
    print(f"\n=== {name} ===", flush=True)
    print("$", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, check=False)  # noqa: S603 - fixed argv, local repo
    status = "PASS" if result.returncode == 0 else "FAIL"
    print(f"[{status}] {name}", flush=True)
    return result.returncode == 0


def python_executable(backend: Path) -> list[str]:
    """Prefer the project venv, fall back to the current interpreter."""
    venv = backend / (".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python")
    return [str(venv)] if venv.exists() else [sys.executable]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-installer", action="store_true")
    args = parser.parse_args()

    py = python_executable(BACKEND)
    results: dict[str, bool] = {}
    results["backend lint"] = run("backend lint", [*py, "-m", "ruff", "check", "."], BACKEND)
    results["backend format"] = run("backend format", [*py, "-m", "ruff", "format", "--check", "."], BACKEND)
    results["backend tests"] = run("backend tests", [*py, "-m", "pytest", "--cov=app", "-q"], BACKEND)
    results["pip-audit"] = run("pip-audit", [*py, "-m", "pip_audit", "-r", "requirements.txt", "--strict"], BACKEND)

    if not args.skip_frontend and (FRONTEND / "node_modules").exists():
        npx = shutil.which("npx") or "npx"
        results["frontend lint"] = run("frontend lint", ["npm", "run", "lint"], FRONTEND)
        results["frontend tests"] = run("frontend tests", [npx, "vitest", "run"], FRONTEND)
        results["frontend build"] = run("frontend build", ["npm", "run", "build"], FRONTEND)
        results["npm audit"] = run("npm audit", ["npm", "audit", "--audit-level=high"], FRONTEND)

    if not args.skip_installer:
        script = ROOT / "scripts" / "build-installer.ps1"
        print(f"\n[i] installer build stays manual/CI only: pwsh -File {script} -WithoutPinnedBinaries")

    print("\n=== summary ===")
    for name, passed in results.items():
        print(f"{'PASS' if passed else 'FAIL'}  {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
