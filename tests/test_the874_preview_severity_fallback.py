"""THE-874 G1: destination Preview must offer severities for every route source.

Sources whose route-filter catalog declares no severities (for example Xen
Orchestra) previously left the Preview severity select empty, so no preview
was generated. The WebUI now falls back to a default severity list.
"""

from __future__ import annotations

import re
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src" / "webui" / "reference_acceptance.js"


def _function_body(text: str, name: str) -> str:
    match = re.search(rf"function {name}\(.*?\) \{{", text)
    assert match, f"{name} is missing from reference_acceptance.js"
    depth = 0
    for index in range(match.end() - 1, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise AssertionError(f"{name} is not balanced")


def test_default_preview_severities_are_defined() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    match = re.search(r"PREVIEW_DEFAULT_SEVERITIES = \[(.*?)\];", text)
    assert match, "PREVIEW_DEFAULT_SEVERITIES is missing"
    values = re.findall(r'"([a-z]+)"', match.group(1))
    assert values == ["critical", "warning", "info"]


def test_default_severities_are_used_only_when_no_route_declares_any() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    body = _function_body(text, "previewAvailableSeverities")
    assert "PREVIEW_DEFAULT_SEVERITIES" in body
    assert "previewDeclaredSeverities(route)" in body
    declared = _function_body(text, "previewDeclaredSeverities")
    # Declared catalog values still take precedence and are not replaced.
    assert 'routeFilterValuesForSource(route.source, "severities")' in declared
    assert "route_filters?.severities" in declared
    # Behaviour is covered by tests/webui/test_preview_route_severities.mjs.
