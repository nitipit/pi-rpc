"""Broker process entrypoint."""

from __future__ import annotations

import argparse
import asyncio

from pi_rpc.broker.server import BrokerServer
from pi_rpc.paths import paths_for_session


def build_parser() -> argparse.ArgumentParser:
    """Create the broker argument parser."""
    parser = argparse.ArgumentParser(description="Run a pi-rpc broker process.")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--name")
    return parser


async def run_broker(*, session_id: str, cwd: str, name: str | None) -> None:
    """Run a broker for one session id."""
    server = BrokerServer(paths=paths_for_session(session_id), cwd=cwd, name=name)
    await server.serve()


def main() -> None:
    """Run the broker process."""
    args = build_parser().parse_args()
    asyncio.run(run_broker(session_id=args.session_id, cwd=args.cwd, name=args.name))


if __name__ == "__main__":
    main()
