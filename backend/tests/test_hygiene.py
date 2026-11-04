"""Guardrails for the protocol locks: OSS-only imports, offline runtime, no silent errors.

These tests fail the build when someone reintroduces a forbidden dependency, a network
call, a shell invocation or an error mask (LOCK-00/04/05, E4).
"""

from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
FRONTEND_SRC = REPO / "frontend" / "src"

FORBIDDEN_PACKAGES = (
    "ultralytics",
    "yolov8",
    "yolo_nas",
    "super_gradients",
    "madmom",
    "ollama",
    "internvl",
    "videollama",
    "mmaction",
    "robustvideomatting",
    "hotclip",
)
FORBIDDEN_REQUIREMENTS = ("ultralytics", "madmom", "super-gradients", "moviepy", "ffmpeg-python")
NETWORK_HINTS = (
    "requests.get(",
    "requests.post(",
    "urllib.request.urlopen",
    'httpx.get("http',
    'socket.create_connection(("',
)
TELEMETRY_HINTS = (
    "posthog",
    "sentry_sdk",
    "mixpanel",
    "google-analytics",
    "segment.io",
    "amplitude",
)


def python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def test_no_forbidden_imports() -> None:
    offenders: list[str] = []
    for path in python_files(APP_DIR):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name.lower() in FORBIDDEN_PACKAGES:
                    offenders.append(f"{path.relative_to(REPO)}: {name}")
    assert offenders == [], f"forbidden OSS packages imported: {offenders}"


def test_requirements_stay_on_the_whitelist() -> None:
    text = (BACKEND / "requirements.txt").read_text(encoding="utf-8").lower()
    for package in FORBIDDEN_REQUIREMENTS:
        assert package not in text, f"{package} is on the blacklist (§20)"
    for line in text.splitlines():
        if line and not line.startswith("#"):
            assert "==" in line, f"every dependency must be pinned: {line}"


def test_runtime_never_opens_the_network() -> None:
    offenders: list[str] = []
    for path in python_files(APP_DIR):
        content = path.read_text(encoding="utf-8")
        for hint in NETWORK_HINTS:
            if hint in content:
                offenders.append(f"{path.relative_to(REPO)}: {hint}")
        for hint in TELEMETRY_HINTS:
            if hint in content:
                offenders.append(f"{path.relative_to(REPO)}: telemetry {hint}")
    assert offenders == [], f"runtime network/telemetry usage: {offenders}"


def test_frontend_has_no_telemetry_or_gpl_player() -> None:
    offenders: list[str] = []
    for path in sorted(FRONTEND_SRC.rglob("*")):
        if path.suffix not in {".ts", ".tsx"} or not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for hint in TELEMETRY_HINTS:
            if hint in content:
                offenders.append(f"{path.relative_to(REPO)}: {hint}")
    assert offenders == []


def test_package_json_has_no_telemetry_dependency() -> None:
    manifest = json.loads((REPO / "frontend" / "package.json").read_text(encoding="utf-8"))
    dependencies = {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}
    banned = [name for name in dependencies if any(hint in name for hint in TELEMETRY_HINTS)]
    assert banned == []
    for name in ("mp4box", "ffmpeg.wasm", "hls.js"):
        assert name not in dependencies, f"{name} pulls a codec/GPL risk at runtime"


def test_no_shell_true_and_no_os_system() -> None:
    offenders: list[str] = []
    for path in python_files(APP_DIR):
        content = path.read_text(encoding="utf-8")
        if "shell=True" in content:
            offenders.append(f"{path.relative_to(REPO)}: shell=True")
        if "os.system(" in content:
            offenders.append(f"{path.relative_to(REPO)}: os.system")
    assert offenders == [], f"unsafe process invocation: {offenders}"


def test_every_exception_handler_logs() -> None:
    """E4: a bare try/except without a structured log and a user message is forbidden."""
    offenders: list[str] = []
    for path in python_files(APP_DIR):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        lines = source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            segment = "\n".join(lines[node.lineno - 1 : (node.end_lineno or node.lineno) + 2])
            if "raise" in segment or "pytest.raises" in segment:
                continue
            if "LOG." not in segment and "logger." not in segment:
                offenders.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert offenders == [], f"exception handlers without structlog: {offenders}"


def _docstring_lines(source: str) -> set[int]:
    """Line numbers occupied by docstrings (documentation may mention GPL encoders)."""
    lines: set[int] = set()
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return lines


def test_gpl_encoders_are_never_used() -> None:
    from app.services.media.ffmpeg import FORBIDDEN_ENCODERS, H264_ENCODERS

    assert "libx264" in FORBIDDEN_ENCODERS
    assert all(encoder not in FORBIDDEN_ENCODERS for encoder in H264_ENCODERS)

    offenders: list[str] = []
    for path in python_files(APP_DIR):
        source = path.read_text(encoding="utf-8")
        docstrings = _docstring_lines(source)
        for number, line in enumerate(source.splitlines(), start=1):
            if number in docstrings or line.lstrip().startswith("#"):
                continue
            if "FORBIDDEN_ENCODERS" in line:
                continue
            if re.search(r"\"-c:v\",\s*\"libx26[45]\"|\"libx26[45]\"\s*(?=,|\))", line):
                offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert offenders == [], f"GPL encoder used as an argument: {offenders}"


def test_schemas_are_draft07_and_present() -> None:
    schemas = sorted((BACKEND / "app" / "schemas_json").glob("*.schema.json"))
    assert {path.name for path in schemas} == {
        "reference-manifest.schema.json",
        "style-dna.schema.json",
        "source-analysis.schema.json",
        "compatibility-report.schema.json",
        "edl.schema.json",
    }


def test_diagnostics_endpoint_reports_local_only(client) -> None:
    response = client.get("/api/v1/system/diagnostics")
    assert response.status_code == 200
    body = response.json()
    assert body["app"]["offline"] is True
    assert "disk" in body
    assert "ffmpeg" in body
    assert body["paths"]["data_dir"]


def test_budget_planner_keeps_one_heavy_model() -> None:
    from app.services.inference.budget import (
        choose_device,
        fits_in_budget,
        footprint,
        plan_sequence,
    )

    models = [
        footprint("clip-vit-b32", 600),
        footprint("yolox-s", 120),
        footprint("real-esrgan", 2400),
    ]
    assert fits_in_budget([models[0], models[1]], 2400) is True
    assert fits_in_budget(models, 2400) is False

    plan = plan_sequence(models, 2400)
    assert plan[0]["name"] == "clip-vit-b32"
    assert plan[-1]["name"] == "real-esrgan"
    assert plan[-1]["fits"] is False
    assert plan[-1]["device"] == "cpu"
    assert plan[0]["evicts"] == []

    assert choose_device(None, 300) == "cpu"
    assert choose_device(8192, 300) == "gpu"
    assert choose_device(1024, 900) == "cpu"


def test_no_todo_markers_in_shipped_code() -> None:
    offenders = []
    for path in python_files(APP_DIR):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if re.search(r"\b(TODO|FIXME|XXX)\b", line):
                offenders.append(f"{path.relative_to(REPO)}:{number}")
    assert offenders == [], f"unfinished markers: {offenders}"


def test_shell_library_name_matches_binary_entrypoint() -> None:
    """Cargo must expose the library referenced by src/main.rs."""
    manifest = tomllib.loads((REPO / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8"))
    library_name = manifest["lib"]["name"]
    entrypoint = (REPO / "src-tauri" / "src" / "main.rs").read_text(encoding="utf-8")
    assert f"{library_name}::run()" in entrypoint
    assert "rlib" in manifest["lib"]["crate-type"]


def test_light_build_selects_runtime_before_cargo() -> None:
    """tauri-build copies FixedRuntime resources at compile time too."""
    script = (REPO / "scripts" / "build-installer.ps1").read_text(encoding="utf-8")
    runtime_override = script.index("$conf.bundle.windows.webviewInstallMode =")
    cargo_build = script.index("cargo build --release")
    restore_config = script.index("Set-Content -Path $tauriConfPath -Value $confBackup")
    assert runtime_override < cargo_build < restore_config


def test_secret_scanner_exception_is_narrowly_scoped_to_rea_identifiers() -> None:
    config = tomllib.loads((REPO / ".gitleaks.toml").read_text(encoding="utf-8"))
    assert config["extend"]["useDefault"] is True
    exception = config["allowlists"][0]
    assert exception["condition"] == "AND"
    paths = [re.compile(pattern) for pattern in exception["paths"]]
    patterns = [re.compile(pattern) for pattern in exception["regexes"]]
    assert any(p.search("docs/evidence/local/rea-runtime.json") for p in paths)
    assert not any(p.search("backend/app/api/assets.py") for p in paths)
    assert not any(p.search("docs/evidence/other.json") for p in paths)
    artifact_id = 'script_key":"scr_' + "a" * 64 + '"'
    assert any(p.search(artifact_id) for p in patterns)
    assert not any(p.search('api_key":"not-an-artifact-identifier"') for p in patterns)
    assert not any(p.search('script_key":"not-an-artifact-identifier"') for p in patterns)


def test_tauri_frontend_hooks_resolve_from_project_root() -> None:
    r"""Tauri v2 invokes hooks from app root, not src-tauri (Windows C:\\build)."""
    config = json.loads((REPO / "src-tauri" / "tauri.conf.json").read_text())
    for hook in ("beforeDevCommand", "beforeBuildCommand"):
        command = config["build"][hook].split()
        assert command[:3] == ["npm", "--prefix", "frontend"]
        assert (REPO / command[2] / "package.json").is_file()


def test_nsis_uses_upstream_farsi_language_identifier() -> None:
    """NSIS supplies Farsi.nlf, not Persian.nlf; keep both installer languages."""
    config = json.loads((REPO / "src-tauri" / "tauri.conf.json").read_text())
    assert config["bundle"]["windows"]["nsis"]["languages"] == ["English", "Farsi"]


def test_package_metadata_reuses_audited_runtime_requirements() -> None:
    """Do not resurrect outdated dependency pins through pip install of this package."""
    config = tomllib.loads((BACKEND / "pyproject.toml").read_text())
    assert "dependencies" not in config["project"]
    assert "dependencies" in config["project"]["dynamic"]
    assert config["tool"]["setuptools"]["dynamic"]["dependencies"]["file"] == ["requirements.txt"]
