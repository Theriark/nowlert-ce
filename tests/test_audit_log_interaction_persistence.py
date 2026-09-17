from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_audit_refinement_capture_phase_survives_row_and_tab_replacement():
    script = (ROOT / "src" / "webui" / "audit_log_refinement.js").read_text(
        encoding="utf-8"
    )

    # Row and tab handlers synchronously replace the clicked DOM nodes. The
    # refinement listener therefore has to schedule from the capture phase,
    # before event.target becomes detached from #view-audit.
    assert 'document.addEventListener("click",' in script
    assert 'document.addEventListener("keydown",' in script
    assert 'document.addEventListener("change",' in script
    assert 'document.addEventListener("input",' in script
    assert script.count('}, true);') >= 4
