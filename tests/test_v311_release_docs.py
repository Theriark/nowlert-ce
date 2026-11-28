"""Historical Nowlert CE v3.1.1 release/documentation contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v311_release_documents_are_preserved():
    release = (ROOT / "docs" / "releases" / "v3.1.1.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "docs" / "releases" / "validation" / "v3.1.1-qa-checklist.md").read_text(
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
    checklist = (ROOT / "docs" / "releases" / "validation" / "v3.1.1-qa-checklist.md").read_text(
        encoding="utf-8"
    )

    for change in (
        "administrator user deletion",
        "private state backup deletion",
        "environment branch and immutable promotion alignment",
        "authoritative administrator role display",
        "Delivery History presentation regression correction",
        "Delivery History/Audit Log pagination footer refinement",
        "remove redundant excluded severity/status route controls",
        "use native selection highlighting",
        "normal single-click additive/subtractive route selection",
        "accurate full-list route criteria display",
    ):
        assert change in release
    # Public notes carry no internal tracker keys.
    assert "NCE-" not in release and "NCE-" not in checklist

    assert "without rebuild" in release.casefold()
