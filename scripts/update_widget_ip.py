#!/usr/bin/env python3
"""Update widget WebSocket URLs for local deployment.

Repository widget files use localhost by default so personal network details
are not committed. Run this script when you need local files pointed at your
current external IP address.
"""

from __future__ import annotations

import argparse
import re
import urllib.request
from pathlib import Path


DEFAULT_FILES = (
    "entries-widget-1col.html",
    "entries-widget.html",
)
DEFAULT_PORT = 64209
IPIFY_URL = "https://api.ipify.org"
WS_URL_RE = re.compile(r'ws://(?:localhost|127\.0\.0\.1|(?:\d{1,3}\.){3}\d{1,3})(?::\d+)?')


def detect_external_ip() -> str:
    with urllib.request.urlopen(IPIFY_URL, timeout=10) as response:
        return response.read().decode("utf-8").strip()


def update_file(path: Path, host: str, port: int) -> bool:
    text = path.read_text(encoding="utf-8")
    replacement = f"ws://{host}:{port}"
    updated = WS_URL_RE.sub(replacement, text)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8", newline="")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replace widget WebSocket URLs with an external IP address."
    )
    parser.add_argument(
        "--ip",
        help="External IP to use. If omitted, the script fetches it from api.ipify.org.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"WebSocket port to use. Default: {DEFAULT_PORT}",
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=DEFAULT_FILES,
        help="Widget HTML files to update.",
    )
    args = parser.parse_args()

    host = args.ip or detect_external_ip()
    changed = []

    for filename in args.files:
        path = Path(filename)
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        if update_file(path, host, args.port):
            changed.append(str(path))

    if changed:
        print(f"Updated {len(changed)} file(s) to ws://{host}:{args.port}")
        for filename in changed:
            print(f"- {filename}")
    else:
        print("No widget WebSocket URLs needed updating.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
