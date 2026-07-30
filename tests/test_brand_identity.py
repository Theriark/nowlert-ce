"""Repository-wide Nowlert identity regression."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


def test_repository_contains_no_previous_product_identifier():
    forbidden = (b"noti" + b"finho").lower()
    matches = []

    for path in ROOT.rglob("*"):
        if not path.is_file() or IGNORED_PARTS.intersection(path.parts):
            continue
        if forbidden in path.name.lower().encode():
            matches.append(str(path.relative_to(ROOT)))
            continue
        if forbidden in path.read_bytes().lower():
            matches.append(str(path.relative_to(ROOT)))

    assert not matches, f"previous product identifier found in: {matches}"
