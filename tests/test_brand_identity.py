"""Repository-wide Nowlert identity regression."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def tracked_repository_files():
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )

    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue

        relative = Path(os.fsdecode(raw))
        path = ROOT / relative

        if path.is_file():
            yield relative, path


def test_repository_contains_no_previous_product_identifier():
    forbidden = (b"noti" + b"finho").lower()
    matches = []

    for relative, path in tracked_repository_files():
        if forbidden in path.name.lower().encode():
            matches.append(str(relative))
            continue

        if forbidden in path.read_bytes().lower():
            matches.append(str(relative))

    assert not matches, (
        f"previous product identifier found in: {matches}"
    )
