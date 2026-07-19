from __future__ import annotations

import argparse

from researchsensei import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="researchsensei",
        description="ResearchSensei backend command line tools.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("healthcheck", help="Check that the package imports and CLI work.")
    serve = subparsers.add_parser("serve", help="Start the configured local API server.")
    serve.add_argument("--host", default=None, help="Override server.host from configuration.")
    serve.add_argument("--port", default=None, type=int, help="Override server.port from configuration.")
    serve.add_argument("--reload", action="store_true", default=None, help="Enable Uvicorn reload mode.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "healthcheck":
        print("ResearchSensei healthcheck: ok")
        return 0

    if args.command == "serve":
        import uvicorn

        from researchsensei.core.config import ConfigService

        config = ConfigService().load()
        host = args.host or config.server.host
        port = args.port or config.server.port
        reload_enabled = config.server.reload if args.reload is None else args.reload
        uvicorn.run(
            "researchsensei.web.app:create_app",
            factory=True,
            host=host,
            port=port,
            reload=reload_enabled,
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
