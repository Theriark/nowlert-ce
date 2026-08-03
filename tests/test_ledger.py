from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "ledger.py"
spec = importlib.util.spec_from_file_location("nowlert_ledger", SCRIPT)
assert spec and spec.loader
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


def test_normalize_run_id_accepts_id_and_url() -> None:
    assert ledger.normalize_run_id("30776030212") == "30776030212"
    assert (
        ledger.normalize_run_id(
            "https://github.com/Theriark/nowlert-ce/actions/runs/30776030212"
        )
        == "30776030212"
    )


def test_build_current_record_is_edition_scoped() -> None:
    args = Namespace(
        environment="production-reference",
        image=ledger.IMAGE_PREFIX + "a" * 64,
        source_commit="b" * 40,
        promotion_run="30776030212",
        application_id="-Qb71PLUZmBHLJ_Iv68Oo",
        schedule_id="JVSEdTk4tt4vKPbG3cKFZ",
        schedule_deployment_id="LWwEp6HTGfGYvpw7m0Gzo",
        qa_marker="PRODUCTION REFERENCE CE POST-PROMOTION SMOKE PASSED",
    )

    key, payload = ledger.build_current(args)

    assert key == f"{ledger.PREFIX}/production-reference/current.json"
    assert payload["edition"] == ledger.EDITION
    assert payload["image"] == args.image
    assert payload["source_commit"] == args.source_commit
    assert payload["promotion_run"] == "30776030212"
