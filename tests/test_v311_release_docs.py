"""Historical Nowlert CE v3.1.1 release/documentation contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v311_release_documents_are_preserved():
    release = (ROOT / "docs" / "releases" / "v3.1.1.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "docs" / "v3.1.1-qa-checklist.md").read_text(
        encoding="utf-8"
    )

    assert release.startswith("# Nowlert CE v3.1.1 release notes")
    assert checklist.startswith("# Nowlert CE v3.1.1 QA checklist")
    assert "schema **9**" in release
    assert "platform_database_v1" in release
    assert "main == stage == source_commit" in checklist
    assert "alias publication reports `Image rebuild performed: no`" in checklist


def test_v311_release_notes_cover_cumulative_qa_and_immutable_release():
    release = (ROOT / "docs" / "releases" / "v3.1.1.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "docs" / "v3.1.1-qa-checklist.md").read_text(
        encoding="utf-8"
    )

    for issue in (
        "NCE-30",
        "NCE-31",
        "NCE-32",
        "NCE-33",
        "NCE-34",
        "NCE-35",
        "NCE-36",
        "NCE-37",
        "NCE-38",
        "NCE-39",
    ):
        assert issue in release or issue in checklist

    assert "without rebuild" in release.casefold()
