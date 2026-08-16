#!/usr/bin/env python3
"""Write the mutable discovery pointer for an immutable Owner Feed snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED_PATH = ROOT / "miki-public" / "index.json"
LATEST_PATH = ROOT / "miki-public" / "latest.json"
REPOSITORY = "mirrorlious/miki-clean-publisher"


def build_pointer(feed_commit: str, feed_bytes: bytes) -> dict:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", feed_commit or ""):
        raise SystemExit("feed commit must be full 40-hex SHA")
    return {
        "schemaVersion": 1,
        "repository": REPOSITORY,
        "feedCommit": feed_commit.lower(),
        "feedPath": "miki-public/index.json",
        "feedSha256": hashlib.sha256(feed_bytes).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed-commit", required=True)
    args = parser.parse_args()
    feed_bytes = FEED_PATH.read_bytes()
    pointer = build_pointer(args.feed_commit, feed_bytes)
    LATEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_PATH.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"latest pointer -> {pointer['feedCommit']} sha256:{pointer['feedSha256']}")


if __name__ == "__main__":
    main()
