"""Prove the public-checksum exception cannot suppress other paths or values.

Runs the real pinned CLI against disposable Git history; no secret values are printed.
The deliberate credential-shaped test content is generated only in a temporary repo.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_CHECKSUM = "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"


def run(cli: str) -> None:
    with tempfile.TemporaryDirectory(prefix="gitleaks-boundary-") as folder:
        fixture = Path(folder)
        doc = fixture / "docs" / "RECOVERY-R2B2-REPORT.md"
        doc.parent.mkdir()
        different = hashlib.sha256(b"noncredential negative control").hexdigest()
        doc.write_text(f'api_key = "{PUBLIC_CHECKSUM}"\napi_key = "{different}"\n')
        (fixture / "elsewhere.env").write_text(f'api_key = "{PUBLIC_CHECKSUM}"\n')
        for arguments in (
            ["init", "-q", "--initial-branch=arena/dbb53bc2-cutting-edge-studio"],
            ["add", "."],
            ["-c", "user.name=CI fixture", "-c", "user.email=ci@example.invalid", "commit", "-qm", "boundary fixture"],
        ):
            subprocess.run(["git", *arguments], cwd=fixture, check=True, capture_output=True)
        report = fixture / "results.sarif"
        scan = subprocess.run([
            cli, "git", str(fixture), "--config", str(ROOT / ".gitleaks.toml"),
            "--redact=100", "--report-format=sarif", "--report-path", str(report),
            "--exit-code=2",
        ], capture_output=True, text=True, check=False)
        if scan.returncode != 2:
            raise RuntimeError(f"Boundary scan must reject negative controls (exit {scan.returncode}); scanner values withheld")
        findings = [r for run in json.loads(report.read_text())["runs"] for r in run.get("results", [])]
        locations = set()
        for finding in findings:
            assert finding["ruleId"] == "generic-api-key", "Unexpected fixture rule; values withheld"
            physical = finding["locations"][0]["physicalLocation"]
            locations.add((physical["artifactLocation"]["uri"], physical["region"]["startLine"]))
        assert len(findings) == 2, "Exact exception did not preserve two negative controls; values withheld"
        assert locations == {("docs/RECOVERY-R2B2-REPORT.md", 2), ("elsewhere.env", 1)}, "Exception path/value boundary changed; values withheld"
        print("PASS: exact public checksum/document excluded; another value in that document and the same checksum elsewhere still fail the real scanner.")


if __name__ == "__main__":
    run(sys.argv[1])
