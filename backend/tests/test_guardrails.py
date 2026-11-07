"""Locked-in guarantees: offline, no telemetry, no unlogged exception swallowing."""

from __future__ import annotations

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
FORBIDDEN_MODULES = {"requests", "urllib.request", "socket", "webbrowser", "telemetry"}
FORBIDDEN_STRINGS = ("google-analytics", "segment.io", "sentry", "mixpanel", "posthog")


def _modules() -> list[Path]:
    return sorted(APP_DIR.rglob("*.py"))


def test_no_network_or_telemetry_imports() -> None:
    offenders: list[str] = []
    for path in _modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.name}:{alias.name}"
                    for alias in node.names
                    if alias.name in FORBIDDEN_MODULES
                    and not (
                        path == APP_DIR / "__main__.py"
                        and alias.name == "socket"
                        and alias.asname is None
                    )
                )
            elif isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_MODULES:
                offenders.append(f"{path.name}:{node.module}")
    assert offenders == []


def test_no_telemetry_endpoints_in_source() -> None:
    hits = [
        f"{path.name}:{needle}"
        for path in _modules()
        for needle in FORBIDDEN_STRINGS
        if needle in path.read_text(encoding="utf-8").lower()
    ]
    assert hits == []


def test_bare_except_never_swallows_errors() -> None:
    """Auto-Failure #1: a bare ``except`` that returns a default value is masking."""
    offenders = [
        f"{path.name}:{node.lineno}"
        for path in _modules()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.ExceptHandler) and node.type is None
    ]
    assert offenders == []


def test_desktop_socket_is_listen_only() -> None:
    """Narrow reviewed exception: the native entry binds loopback, never dials out."""
    tree = ast.parse((APP_DIR / "__main__.py").read_text(encoding="utf-8"))
    references = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "socket"
    ]
    assert references
    assert {node.attr for node in references} <= {
        "socket",
        "AF_INET",
        "SOCK_STREAM",
        "SOL_SOCKET",
        "SO_EXCLUSIVEADDRUSE",
        "SO_REUSEADDR",
    }
    assert not any(
        isinstance(node, ast.Attribute)
        and node.attr
        in {
            "connect",
            "connect_ex",
            "send",
            "sendall",
            "sendto",
            "getaddrinfo",
            "create_connection",
        }
        for node in ast.walk(tree)
    )
