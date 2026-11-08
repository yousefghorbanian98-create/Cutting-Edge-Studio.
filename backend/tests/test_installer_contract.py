"""Static checks for the staged Windows installer hooks.

The NSIS script is only *compiled* by the Windows installer job, which does not run
on pull requests. These tests catch the structural mistakes that would otherwise be
discovered hours later on a Windows runner, and pin the two rules that matter most:
the installer never downloads anything, and it never re-implements what Tauri already
does.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / "src-tauri" / "installer-hooks.nsh"
TAURI_CONF = REPO / "src-tauri" / "tauri.conf.json"
PINS = REPO / "scripts" / "pins.json"
BUILD_SCRIPT = REPO / "scripts" / "build-installer.ps1"

REQUIRED_HOOKS = (
    "NSIS_HOOK_PREINSTALL",
    "NSIS_HOOK_POSTINSTALL",
    "NSIS_HOOK_PREUNINSTALL",
    "NSIS_HOOK_POSTUNINSTALL",
)


@pytest.fixture(scope="module")
def hooks() -> str:
    return HOOKS.read_text(encoding="utf-8")


def test_tauri_config_points_at_the_hooks_file() -> None:
    config = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    nsis = config["bundle"]["windows"]["nsis"]
    assert nsis.get("installerHooks") == "./installer-hooks.nsh"
    assert HOOKS.is_file(), "installerHooks points at a file that does not exist"


@pytest.mark.parametrize("hook", REQUIRED_HOOKS)
def test_every_tauri_hook_is_defined(hooks: str, hook: str) -> None:
    assert f"!macro {hook}" in hooks, f"{hook} is not defined"


def test_macros_and_functions_are_balanced(hooks: str) -> None:
    assert hooks.count("!macro ") == hooks.count("!macroend"), "unbalanced !macro/!macroend"
    opens = len(re.findall(r"^Function ", hooks, re.MULTILINE))
    closes = len(re.findall(r"^FunctionEnd", hooks, re.MULTILINE))
    assert opens == closes, f"unbalanced Function/FunctionEnd ({opens}/{closes})"


def test_logiclib_blocks_are_balanced(hooks: str) -> None:
    opens = len(re.findall(r"\$\{If\}|\$\{IfNot\}", hooks))
    closes = len(re.findall(r"\$\{EndIf\}", hooks))
    assert opens == closes, f"unbalanced LogicLib If/EndIf ({opens}/{closes})"


def test_preprocessor_conditionals_are_balanced(hooks: str) -> None:
    opens = len(re.findall(r"^\s*!if(?:macrodef|def|ndef|\s|/)", hooks, re.MULTILINE))
    closes = len(re.findall(r"^\s*!endif", hooks, re.MULTILINE))
    assert opens == closes, f"unbalanced !if/!endif ({opens}/{closes})"


def test_installer_never_downloads_at_runtime(hooks: str) -> None:
    """LOCK-05 / README: the shipped product performs no network access, ever."""
    forbidden = (
        "inetc::",
        "NSISdl::",
        "INetLoad::",
        "http://",
        "https://",
        "DownloadFile",
    )
    offenders = [token for token in forbidden if token.lower() in hooks.lower()]
    assert offenders == [], f"installer hook reaches the network: {offenders}"


def test_hooks_do_not_duplicate_what_tauri_owns(hooks: str) -> None:
    """Tauri's template owns WebView2 installation, shortcuts and the uninstaller.

    Re-implementing them in a hook makes two code paths fight over the same state,
    which is exactly the overlap this file is meant to avoid.
    """
    body = hooks.lower()
    assert "createshortcut" not in body, "shortcut creation belongs to Tauri's template"
    assert "writeuninstaller" not in body, "the uninstaller belongs to Tauri's template"
    # Reading WebView2 state is fine; launching its installer is Tauri's job.
    assert "microsoftedgewebview2setup" not in body
    assert "webview2 installer" not in body


def test_prerequisite_is_sha256_pinned() -> None:
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    entry = pins["vc_redist_x64"]
    assert entry["target"] == "src-tauri/prerequisites"
    assert entry["url"].startswith("https://")
    # sha256 may be null until an operator runs -UpdatePins, but the build script
    # refuses to build in that state, so the field must at least exist.
    assert "sha256" in entry


def test_build_script_stages_the_prerequisite_and_exports_the_path() -> None:
    script = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "vc_redist_x64" in script, "build script never fetches the pinned redistributable"
    assert "CE_PREREQ_DIR" in script, "build script never exports CE_PREREQ_DIR for the NSIS hook"
    assert "$env:CE_PREREQ_DIR = ''" in script, "light build must clear CE_PREREQ_DIR"


def test_prerequisites_directory_is_not_committed() -> None:
    ignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "src-tauri/prerequisites/" in ignore, "the staged redistributable could be committed"


def test_stage_counter_matches_the_declared_total(hooks: str) -> None:
    """A mislabelled 'step 6 of 5' is the kind of detail that makes an installer feel cheap."""
    match = re.search(r"!define CE_TOTAL_STAGES (\d+)", hooks)
    assert match, "CE_TOTAL_STAGES is not defined"
    declared = int(match.group(1))
    actual = len(re.findall(r"!insertmacro CE_Stage ", hooks))
    assert actual == declared, f"{actual} stages are emitted but CE_TOTAL_STAGES is {declared}"


def test_hook_script_is_pure_ascii() -> None:
    """Tauri compiles the NSIS script with `Unicode true`.

    A UTF-8 include without a BOM is read using the system ANSI codepage, which
    silently garbles any non-ASCII character in a user-visible DetailPrint. Staying
    ASCII removes the dependency on byte-order marks entirely.
    """
    raw = HOOKS.read_bytes()
    offenders = [(i, b) for i, b in enumerate(raw) if b > 0x7F]
    assert offenders == [], f"non-ASCII bytes at offsets {[o[0] for o in offenders[:5]]}"
