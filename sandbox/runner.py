from __future__ import annotations

import argparse
import runpy
import socket
import sys
from pathlib import Path


def restrict_network(allowed_host: str) -> None:
    original_getaddrinfo = socket.getaddrinfo

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host not in {allowed_host, "localhost", "127.0.0.1", None}:
            raise OSError(f"network access denied for host: {host}")
        return original_getaddrinfo(host, *args, **kwargs)

    socket.getaddrinfo = guarded_getaddrinfo  # type: ignore[assignment]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--allow-host", default="api.fda.gov")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    restrict_network(args.allow_host)
    sys.path.insert(0, str(workspace))
    runpy.run_path(args.script, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
