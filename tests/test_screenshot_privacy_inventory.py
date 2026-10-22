"""Every raster under docs/images is accounted for in the screenshot privacy inventory.

The inventory lives in docs/guides/screenshot-privacy.md. A retained capture has
a table row ``| `images/<path>` | retained | <record> |``; a withdrawn capture is
a bullet ``- `images/<path>` — <reason>`` and must not exist in the checkout.
A raster that is on disk, or linked from a current guide, without a retained
row fails here, so a new image cannot land without a privacy record. PNG and
JPEG files must also be free of EXIF and author/copyright text metadata.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
IMAGES = DOCS / "images"
PRIVACY = DOCS / "guides" / "screenshot-privacy.md"
RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
RETAINED_ROW_RE = re.compile(r"^\| `(images/[^`]+)` \| retained \|", re.MULTILINE)
WITHDRAWN_ROW_RE = re.compile(r"^- `(images/[^`]+)`", re.MULTILINE)
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_TEXT_CHUNKS = {b"tEXt", b"iTXt", b"zTXt"}
PERSONAL_KEYWORDS = {"author", "copyright"}


def rasters_on_disk() -> list[str]:
    return sorted(
        path.relative_to(DOCS).as_posix()
        for path in IMAGES.rglob("*")
        if path.is_file() and path.suffix.lower() in RASTER_SUFFIXES
    )


def retained_inventory() -> set[str]:
    return set(RETAINED_ROW_RE.findall(PRIVACY.read_text(encoding="utf-8")))


def withdrawn_inventory() -> set[str]:
    return set(WITHDRAWN_ROW_RE.findall(PRIVACY.read_text(encoding="utf-8")))


def current_documents() -> list[Path]:
    documents = [ROOT / "README.md", ROOT / "DOCKERHUB_README.md"]
    documents.extend(
        path for path in sorted(DOCS.rglob("*.md"))
        if "releases" not in path.relative_to(ROOT).parts
    )
    return [path for path in documents if path.is_file()]


def linked_rasters() -> dict[str, list[str]]:
    links: dict[str, list[str]] = {}
    images_root = IMAGES.resolve()
    for document in current_documents():
        text = document.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            target = raw.split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (document.parent / target).resolve()
            if resolved.suffix.lower() not in RASTER_SUFFIXES:
                continue
            try:
                relative = resolved.relative_to(images_root)
            except ValueError:
                continue
            key = f"images/{relative.as_posix()}"
            links.setdefault(key, []).append(document.relative_to(ROOT).as_posix())
    return links


def png_metadata_chunks(data: bytes) -> list[tuple[str, str]]:
    """Return (chunk type, keyword) pairs for the textual and EXIF chunks of a PNG."""
    found: list[tuple[str, str]] = []
    offset = len(PNG_SIGNATURE)
    while offset + 8 <= len(data):
        length, chunk_type = struct.unpack(">I4s", data[offset:offset + 8])
        body = data[offset + 8:offset + 8 + length]
        if chunk_type in PNG_TEXT_CHUNKS:
            keyword = body.split(b"\x00", 1)[0].decode("latin-1", "replace")
            found.append((chunk_type.decode("ascii"), keyword))
        elif chunk_type == b"eXIf":
            found.append(("eXIf", ""))
        if chunk_type == b"IEND":
            break
        offset += 12 + length
    return found


def jpeg_has_exif(data: bytes) -> bool:
    """Return True when a JPEG carries an Exif APP1 segment before the scan data."""
    offset = 2
    while offset + 4 <= len(data) and data[offset] == 0xFF:
        marker = data[offset + 1]
        if marker == 0xFF:
            offset += 1
            continue
        if marker == 0xDA:
            break
        length = struct.unpack(">H", data[offset + 2:offset + 4])[0]
        if marker == 0xE1 and data[offset + 4:offset + 10] == b"Exif\x00\x00":
            return True
        offset += 2 + length
    return False


def test_inventory_document_exists_with_entries():
    assert PRIVACY.is_file()
    assert retained_inventory(), "the retained inventory must list the packaged rasters"
    assert withdrawn_inventory(), "the withdrawn capture record must not be empty"


def test_every_raster_on_disk_has_a_retained_row():
    retained = retained_inventory()
    missing = [relative for relative in rasters_on_disk() if relative not in retained]
    assert not missing, f"rasters without a screenshot-privacy inventory row: {missing}"


def test_retained_rows_point_at_existing_files():
    stale = sorted(relative for relative in retained_inventory() if not (DOCS / relative).is_file())
    assert not stale, f"retained inventory rows without a file: {stale}"


def test_withdrawn_captures_are_absent_and_not_retained():
    withdrawn = withdrawn_inventory()
    present = sorted(relative for relative in withdrawn if (DOCS / relative).exists())
    assert not present, f"withdrawn captures still in the checkout: {present}"
    overlap = sorted(withdrawn & retained_inventory())
    assert not overlap, f"captures listed as both retained and withdrawn: {overlap}"


def test_linked_rasters_exist_and_are_retained():
    retained = retained_inventory()
    problems = []
    for relative, documents in sorted(linked_rasters().items()):
        if not (DOCS / relative).is_file():
            problems.append(f"{relative} is missing; linked from {', '.join(documents)}")
        elif relative not in retained:
            problems.append(f"{relative} has no retained row; linked from {', '.join(documents)}")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("relative", rasters_on_disk())
def test_captures_carry_no_exif_or_personal_text_metadata(relative):
    data = (DOCS / relative).read_bytes()
    if data.startswith(PNG_SIGNATURE):
        chunks = png_metadata_chunks(data)
        assert not [chunk for chunk in chunks if chunk[0] == "eXIf"], f"{relative} carries an eXIf chunk"
        personal = [chunk for chunk in chunks if chunk[1].lower() in PERSONAL_KEYWORDS]
        assert not personal, f"{relative} carries personal text metadata: {personal}"
    elif data[:2] == b"\xff\xd8":
        assert not jpeg_has_exif(data), f"{relative} carries an Exif segment"
