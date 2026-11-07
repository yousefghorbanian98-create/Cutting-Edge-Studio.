"""Entry point for the packaged sidecar: ``python -m app --port 8756 --host 127.0.0.1``."""

from __future__ import annotations

import argparse
import socket
import sys

import uvicorn

from app.config import Settings, get_settings
from app.logging import get_logger

LOG = get_logger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Only loopback arguments are accepted; anything else is rejected by argparse."""
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="cutting-edge-backend", description="Cutting Edge v2 sidecar"
    )
    parser.add_argument("--host", default=settings.host, help="bind address (loopback only)")
    parser.add_argument("--port", type=int, default=settings.port, help="loopback port")
    parser.add_argument("--serve-frontend", action="store_true", default=settings.serve_frontend)
    parser.add_argument("--log-level", default=settings.log_level, help="DEBUG/INFO/WARNING/ERROR")
    return parser.parse_args(argv)


def desktop_listener(settings: Settings) -> socket.socket:
    """Reserve the desktop port before lifespan can publish its readiness receipt.

    Windows exclusive address use prevents another listener sharing the port.
    Unix reuse permits restart after TIME_WAIT, not a second active listener.
    """
    if settings.host != "127.0.0.1":
        LOG.error("desktop.listener.rejected", host=settings.host)
        raise SystemExit("Desktop serving requires the IPv4 loopback address 127.0.0.1")
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if sys.platform == "win32":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((settings.host, settings.port))
        listener.listen(128)
    except OSError as error:
        listener.close()
        LOG.error("desktop.listener.failed", error=str(error), port=settings.port)
        raise SystemExit("Desktop port unavailable; close the other instance and retry") from error
    else:
        return listener


def main(argv: list[str] | None = None) -> None:
    """Run the backend on loopback only (never exposed to the LAN)."""
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] == "--audio-rhythm-worker":
        from app.services.audio.worker import worker_main

        worker_main(arguments[1:])
        return
    from app.main import create_app

    args = parse_args(arguments)
    if not 0 <= args.port <= 65535:
        raise SystemExit("Port must be between 0 and 65535")
    # Random port guard: --port 0 lets OS pick a free port, published via receipt + stdout PORT=...
    if args.port == 0:
        print("CES: random port requested — OS will assign free port", file=sys.stderr)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        msg = f"refusing to bind {args.host}: the sidecar is loopback-only (LOCK-05)"
        raise SystemExit(msg)
    settings = get_settings().model_copy(
        update={
            "host": args.host,
            "port": args.port,
            "log_level": args.log_level,
            "serve_frontend": args.serve_frontend,
        }
    )
    try:
        application = create_app(settings)
    except (RuntimeError, OSError) as error:
        LOG.error("desktop.application.failed", error=str(error))
        raise SystemExit(f"Local application could not start: {error}") from error
    if settings.serve_frontend:
        with desktop_listener(settings) as listener:
            # If --port 0 was requested, update settings with actual OS-assigned port
            actual_port = listener.getsockname()[1]
            if actual_port != settings.port:
                settings = settings.model_copy(update={"port": actual_port})
                application.state.settings = settings
                print(f"PORT={actual_port}", flush=True)
                LOG.info("desktop.listener.random_port", port=actual_port)
            application.state.desktop_listener_owned = True
            server = uvicorn.Server(uvicorn.Config(application, log_config=None, access_log=False))
            server.run(sockets=[listener])
        return
    uvicorn.run(
        application,
        host=settings.host,
        port=settings.port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
