"""Entry point for the packaged sidecar: ``python -m app --port 8756 --host 127.0.0.1``."""

from __future__ import annotations

import argparse

import uvicorn

from app.config import get_settings
from app.main import create_app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Only loopback arguments are accepted; anything else is rejected by argparse."""
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="cutting-edge-backend", description="Cutting Edge v2 sidecar"
    )
    parser.add_argument("--host", default=settings.host, help="bind address (loopback only)")
    parser.add_argument("--port", type=int, default=settings.port, help="loopback port")
    parser.add_argument("--log-level", default=settings.log_level, help="DEBUG/INFO/WARNING/ERROR")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the backend on loopback only (never exposed to the LAN)."""
    args = parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        msg = f"refusing to bind {args.host}: the sidecar is loopback-only (LOCK-05)"
        raise SystemExit(msg)
    settings = get_settings().model_copy(
        update={"host": args.host, "port": args.port, "log_level": args.log_level}
    )
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
