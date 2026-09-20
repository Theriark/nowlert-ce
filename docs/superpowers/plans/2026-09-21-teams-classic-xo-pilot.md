# Microsoft Teams Classic Xen Orchestra Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-destination Modern/Classic selector to Microsoft Teams while keeping existing Modern cards unchanged, then implement and deploy the first Teams Classic card for Xen Orchestra.

**Architecture:** Teams destinations gain `message_style` with a default of `modern`. `TeamsPlatformAdapter` keeps the existing source-specific Teams formatter path untouched for Modern, while Classic selects a separate Teams-native Adaptive Card formatter registry; the pilot registry contains Xen Orchestra only and temporarily falls back to the existing Modern formatter for unimplemented sources.

**Tech Stack:** Python 3.13, pytest, vanilla WebUI JavaScript, Microsoft Adaptive Card 1.4 payloads, existing `TeamsOutput`/platform adapters, GitHub Actions CI.

**Spec:** `docs/superpowers/specs/2026-09-21-teams-classic-xo-pilot-design.md`

## Global Constraints

- Teams Modern must not change.
- New and existing Teams destinations default to `Modern Card` when no explicit style is stored.
- Users can switch a Teams destination between `Modern Card` and `Classic Card` at any time.
- The selected style is stored per destination and used for preview/test and routed delivery.
- Teams Classic remains a native Adaptive Card 1.4; do not send Discord embeds or legacy Microsoft MessageCards.
- The Xen Orchestra Classic pilot preserves the approved Discord Classic lifecycle semantics, title, description, field names, field ordering, omission rules, and VM detail behavior.
- Classic-specific visual iteration must remain isolated from the existing Modern `TeamsCardFormatter._render_teams_card()` path.
- During the pilot, Classic + XO renders the new Classic card; Classic + any not-yet-implemented source temporarily renders that source's existing Modern Teams card.
- Existing Teams transport behavior remains unchanged: HTTPS webhook resolution, 15-second POST, 28 KiB payload limit, safe errors, and HTTP 202 acceptance semantics.
- Do not change Discord, Slack, Generic Webhook, routing, secrets, or retry behavior.
- Follow the Theriark repository workflow: create a new implementation branch from the current green `development` head, make one atomic product commit after local/test verification, open one PR, wait for CI, fix only exact failures if necessary, merge only when green, then verify post-merge Development deployment.

## Review Focus

- **Legacy Teams destinations with empty settings:** must normalize to Modern and produce the same payload as the current Modern formatter.
- **Classic requested for an unimplemented source:** must fall back to that source's current Modern formatter, not generic XO Classic and not an error.
- **XO events with missing/partial backup fields:** Classic must omit empty sections and still produce a valid bounded Adaptive Card.
- **Long VM lists and failure text:** output must remain bounded and stay under the Teams 28 KiB guard; overflow text must be deterministic.
- **Secret-like event content:** the Classic payload must pass through the same recursive sanitization as Modern and must not expose tokens/API keys.

---

### Task 1: Add the Teams destination message-style contract and WebUI selector

**Files:**
- Modify: `src/outputs/settings.py`
- Modify: `src/webui/app.js`
- Modify: `tests/test_platform_outputs.py`
- Modify: `tests/test_webui.py`

**Interfaces:**
- Consumes: `normalize_output_settings(output_type: str, settings: dict | None, *, require_complete: bool = False) -> dict`
- Produces: normalized Teams settings `{"message_style": "modern" | "classic"}`
- Produces in WebUI: dynamic Teams destination field `message_style` with Modern/Classic select choices.

- [ ] **Step 1: Add failing Teams settings tests**

Add to `tests/test_platform_outputs.py` near the existing output-settings/platform tests:

```python
def test_teams_message_style_defaults_to_modern_and_accepts_classic():
    assert normalize_output_settings("teams", {}) == {
        "message_style": "modern"
    }
    assert normalize_output_settings(
        "teams",
        {"message_style": "modern"},
    ) == {"message_style": "modern"}
    assert normalize_output_settings(
        "teams",
        {"message_style": "classic"},
    ) == {"message_style": "classic"}


def test_teams_message_style_rejects_unknown_values():
    with pytest.raises(ValueError, match="teams message_style"):
        normalize_output_settings(
            "teams",
            {"message_style": "legacy"},
        )
```

- [ ] **Step 2: Run the focused settings tests and verify RED**

Run:

```bash
pytest -q   tests/test_platform_outputs.py::test_teams_message_style_defaults_to_modern_and_accepts_classic   tests/test_platform_outputs.py::test_teams_message_style_rejects_unknown_values
```

Expected before implementation: FAIL because Teams currently rejects `message_style` and normalizes to `{}`.

- [ ] **Step 3: Implement the bounded Teams settings validator**

Replace `_teams()` in `src/outputs/settings.py` with:

```python
def _teams(settings, _complete):
    _unknown(settings, {"message_style"})
    style = str(
        settings.get("message_style", "modern") or ""
    ).strip().casefold()
    if style not in {"modern", "classic"}:
        raise ValueError(
            "teams message_style must be modern or classic"
        )
    return {"message_style": style}
```

This keeps old destinations compatible because a missing setting becomes Modern.

- [ ] **Step 4: Re-run the focused settings tests and verify GREEN**

Run the same command from Step 2.

Expected: both tests pass.

- [ ] **Step 5: Add a failing WebUI selector regression**

In `tests/test_webui.py`, add:

```python
def test_teams_destination_editor_exposes_modern_and_classic_message_style():
    script = (
        ROOT / "src" / "webui" / "app.js"
    ).read_text(encoding="utf-8")

    teams_start = script.index("teams: {")
    slack_start = script.index("slack: {", teams_start)
    teams_block = script[teams_start:slack_start]

    assert 'key: "message_style"' in teams_block
    assert 'label: "Message style"' in teams_block
    assert '["modern", "Modern Card"]' in teams_block
    assert '["classic", "Classic Card"]' in teams_block
    assert 'default: "modern"' in teams_block
```

- [ ] **Step 6: Run the WebUI regression and verify RED**

Run:

```bash
pytest -q tests/test_webui.py::test_teams_destination_editor_exposes_modern_and_classic_message_style
```

Expected before implementation: FAIL because the Teams definition currently contains only `Channel / destination`.

- [ ] **Step 7: Add the Teams message-style select to the destination editor**

Change the Teams definition in `src/webui/app.js` to:

```javascript
teams: {
  help: "Microsoft Teams workflow or incoming webhook delivery.",
  settings: [
    presentation,
    {
      key: "message_style",
      label: "Message style",
      kind: "select",
      choices: [
        ["modern", "Modern Card"],
        ["classic", "Classic Card"],
      ],
      default: "modern",
    },
  ],
  secrets: [
    {
      key: "url",
      label: "Webhook URL",
      kind: "password",
      required: true,
      wide: true,
    },
  ],
},
```

Do not change the shared field renderer. Existing editor behavior already loads stored setting values and falls back to a field's `default` when absent.

- [ ] **Step 8: Re-run the WebUI regression and verify GREEN**

Run the command from Step 6.

Expected: PASS.

- [ ] **Step 9: Run existing destination/WebUI safety tests**

Run:

```bash
pytest -q   tests/test_webui.py   tests/test_route_destination_webui.py
```

Expected: all pass.

**Repository workflow checkpoint:** do not commit or push yet. Continue to Task 2 on the same implementation branch so the feature lands as one atomic product commit.

---

### Task 2: Add the isolated Teams Classic Xen Orchestra renderer

**Files:**
- Create: `src/formatters/teams_classic_v1.py`
- Create: `tests/test_teams_classic_xo.py`

**Interfaces:**
- Consumes: `models.Notification`
- Consumes safe presentation helpers inherited from `BaseFormatter`, including `_sanitize_payload()`, `_truncate()`, `_teams_header()`
- Produces: `TeamsClassicXenOrchestraFormatter.format(notification: Notification) -> dict[str, Any]`, a Teams message containing one Adaptive Card 1.4 attachment.
- Constant: `CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Card"`

- [ ] **Step 1: Add failing XO Classic semantic tests**

Create `tests/test_teams_classic_xo.py`.

Use a helper that builds a complete XO backup notification:

```python
from __future__ import annotations

import json

import pytest

from formatters.teams_classic_v1 import (
    CLASSIC_FOOTER,
    TeamsClassicXenOrchestraFormatter,
)
from models import Notification
from outputs.teams import TeamsOutput


def xo_notification(status="success") -> Notification:
    return Notification(
        source="xo",
        category="backup",
        status=status,
        title="Daily Production Backup",
        body="Backup completed.",
        job_name="Daily Production Backup",
        job_id="JOB-123",
        mode="full",
        repository="NFS | Backup Repository | Repository-01",
        duration="5 min",
        transfer_size="52.06 GiB",
        transfer_speed="33.73 MiB/s",
        vm_total=3,
        vm_success=2,
        vm_failed=1 if status in {"failure", "failed", "error", "critical"} else 0,
        vm_skipped=1 if status in {"skipped", "warning"} else 0,
        successful_vms=["VM-01", "VM-02"],
        failed_vms=["VM-03"] if status in {"failure", "failed", "error", "critical"} else [],
        skipped_vms=["VM-04"] if status in {"skipped", "warning"} else [],
        vm_details={
            "VM-01": {"size": "18 GiB"},
            "VM-02": {"size": "12 GiB"},
            "VM-03": {"size": "22 GiB", "error": "Synthetic timeout"},
            "VM-04": {"size": "8 GiB", "error": "Excluded by policy"},
        },
    )


def card_body(payload):
    return payload["attachments"][0]["content"]["body"]


def flattened_text(payload):
    values = []

    def visit(value):
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                values.append(text)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return "\n".join(values)
```

Add success/failure/skipped tests:

```python
@pytest.mark.parametrize(
    ("status", "expected_title", "expected_description"),
    (
        (
            "success",
            "✅ Backup Successful — Daily Production Backup",
            "2 VMs protected successfully with no failures.",
        ),
        (
            "failure",
            "❌ Backup Failed — Daily Production Backup",
            "Backup operation failed with 1 VM error.",
        ),
        (
            "skipped",
            "⏭️ Backup Skipped — Daily Production Backup",
            "2 VMs protected successfully and 1 VM was skipped by backup policy.",
        ),
    ),
)
def test_xo_classic_lifecycle_title_and_description(
    status,
    expected_title,
    expected_description,
):
    payload = TeamsClassicXenOrchestraFormatter().format(
        xo_notification(status)
    )
    text = flattened_text(payload)

    assert expected_title in text
    assert expected_description in text
    assert CLASSIC_FOOTER in text
```

Add field-order parity:

```python
def test_xo_classic_preserves_approved_field_order():
    payload = TeamsClassicXenOrchestraFormatter().format(
        xo_notification("failure")
    )
    text = flattened_text(payload)

    labels = [
        "⏱️ Duration",
        "📦 Transfer Size",
        "🚀 Transfer Speed",
        "📁 Storage",
        "✅ Successful VMs · 2",
        "❌ Failed VMs · 1",
        "🆔 Job ID",
    ]
    positions = [text.index(label) for label in labels]

    assert positions == sorted(positions)
    assert "Repository-01 · NFS · Backup Repository · Full" in text
    assert "VM-01" in text and "18 GiB" in text
    assert "VM-03" in text and "Synthetic timeout" in text
    assert "JOB-123" in text
```

Add Review Focus tests:

```python
def test_xo_classic_omits_empty_optional_sections():
    item = xo_notification("success")
    item.transfer_speed = ""
    item.failed_vms = []
    item.skipped_vms = []
    item.job_id = ""

    payload = TeamsClassicXenOrchestraFormatter().format(item)
    text = flattened_text(payload)

    assert "🚀 Transfer Speed" not in text
    assert "❌ Failed VMs" not in text
    assert "⏭️ Skipped VMs" not in text
    assert "🆔 Job ID" not in text


def test_xo_classic_bounds_long_vm_lists_and_payload_size():
    item = xo_notification("success")
    item.successful_vms = [f"VM-{index:02d}" for index in range(20)]
    item.vm_success = 20
    item.vm_total = 20
    item.vm_details = {
        name: {"size": "10 GiB"}
        for name in item.successful_vms
    }

    formatter = TeamsClassicXenOrchestraFormatter()
    payload = formatter._sanitize_payload(formatter.format(item))
    text = flattened_text(payload)

    assert "… and 10 more" in text
    assert TeamsOutput.payload_size(payload) <= TeamsOutput.MAX_PAYLOAD_BYTES


def test_xo_classic_sanitizes_secret_like_text():
    item = xo_notification("failure")
    item.vm_details["VM-03"]["error"] = "token=private-token timeout"

    formatter = TeamsClassicXenOrchestraFormatter()
    payload = formatter._sanitize_payload(formatter.format(item))
    encoded = json.dumps(payload)

    assert "private-token" not in encoded
    assert "<redacted>" in encoded
```

- [ ] **Step 2: Run the new formatter tests and verify RED**

Run:

```bash
pytest -q tests/test_teams_classic_xo.py
```

Expected before implementation: collection/import failure because `formatters.teams_classic_v1` does not exist.

- [ ] **Step 3: Implement the isolated Classic formatter**

Create `src/formatters/teams_classic_v1.py` with this public structure:

```python
"""Teams-native Classic Card v1 formatters."""

from __future__ import annotations

from typing import Any

from formatters.base import BaseFormatter
from models import Notification


CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Card"


class TeamsClassicXenOrchestraFormatter(BaseFormatter):
    MAX_VMS = 10

    def format(self, notification: Notification) -> dict[str, Any]:
        lifecycle = self._lifecycle(notification)
        title = (
            f"{lifecycle['icon']} {lifecycle['label']} — "
            f"{self._job_name(notification)}"
        )
        description = self._description(notification, lifecycle["state"])

        body = [
            self._teams_header(
                title,
                lifecycle["color"],
                "xo",
            ),
            {
                "type": "TextBlock",
                "text": self._truncate(description, 1200),
                "wrap": True,
                "spacing": "Small",
            },
        ]

        metrics = self._metric_columns(notification)
        if metrics:
            body.append(
                {
                    "type": "ColumnSet",
                    "spacing": "Medium",
                    "separator": True,
                    "columns": metrics,
                }
            )

        for section in self._sections(notification):
            body.append(section)

        body.append(
            {
                "type": "TextBlock",
                "text": CLASSIC_FOOTER,
                "isSubtle": True,
                "size": "Small",
                "spacing": "Medium",
                "separator": True,
                "wrap": True,
            }
        )

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": (
                            "http://adaptivecards.io/schemas/adaptive-card.json"
                        ),
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "msteams": {"width": "Full"},
                        "body": body,
                    },
                }
            ],
        }
```

Implement private helpers in the same class:

```python
    def _lifecycle(self, notification):
        status = str(notification.status or "").strip().casefold()
        failed = status in {"failure", "failed", "error", "critical"}
        skipped_count = int(notification.vm_skipped or 0)
        skipped = (
            status == "skipped"
            or (not failed and skipped_count > 0)
        )

        if failed:
            return {
                "state": "failed",
                "icon": "❌",
                "label": "Backup Failed",
                "color": "Attention",
            }
        if skipped:
            return {
                "state": "skipped",
                "icon": "⏭️",
                "label": "Backup Skipped",
                "color": "Accent",
            }
        return {
            "state": "success",
            "icon": "✅",
            "label": "Backup Successful",
            "color": "Good",
        }

    @staticmethod
    def _job_name(notification):
        return str(
            notification.job_name
            or notification.title
            or notification.subject
            or "Xen Orchestra backup"
        ).strip()

    @staticmethod
    def _description(notification, state):
        vm_success = int(notification.vm_success or 0)
        vm_failed = int(notification.vm_failed or 0)
        vm_total = int(notification.vm_total or 0)
        vm_skipped = int(notification.vm_skipped or 0)

        if state == "failed":
            count = max(1, vm_failed)
            suffix = "VM error" if count == 1 else "VM errors"
            return f"Backup operation failed with {count} {suffix}."

        if state == "skipped":
            protected = vm_success
            protected_label = "VM" if protected == 1 else "VMs"
            skipped_label = "VM was" if vm_skipped == 1 else "VMs were"
            return (
                f"{protected} {protected_label} protected successfully and "
                f"{vm_skipped} {skipped_label} skipped by backup policy."
            )

        protected = vm_success or vm_total
        protected_label = "VM" if protected == 1 else "VMs"
        return (
            f"{protected} {protected_label} protected successfully "
            "with no failures."
        )
```

Use `_metric_columns()` for the first three inline items in exactly this order:

1. Duration
2. Transfer Size
3. Transfer Speed

Each present metric is one stretch column with a bold label and value.

Use `_storage_value()` with the approved XO transformation:

```python
repository_parts = [
    part.strip()
    for part in str(notification.repository or "").split("|")
    if part.strip()
]
if len(repository_parts) >= 3:
    repository_parts = [
        repository_parts[-1],
        *repository_parts[:-1],
    ]
mode = str(notification.mode or "").strip()
if mode:
    mode = mode[:1].upper() + mode[1:]
if mode:
    repository_parts.append(mode)
return " · ".join(repository_parts)
```

Use `_sections()` to append, in this exact order when non-empty:

1. Storage
2. Successful VMs
3. Failed VMs
4. Skipped VMs
5. Job ID

Each section is a Teams `Container` with `separator: True`, a bold heading `TextBlock`, and one wrapped value `TextBlock`.

Use a VM helper with:

```python
shown = names[: self.MAX_VMS]
...
remaining = len(names) - len(shown)
if remaining:
    lines.append(f"… and {remaining} more")
```

Each VM line includes the VM name and size when present. Failed/skipped sections add a following `Error:` line when `vm_details[name]["error"]` is present.

Do not import or call `TeamsCardFormatter._render_teams_card()`. Reusing neutral safety/presentation helpers inherited from `BaseFormatter` is allowed.

- [ ] **Step 4: Run the new formatter tests and verify GREEN**

Run:

```bash
pytest -q tests/test_teams_classic_xo.py
```

Expected: all pass.

- [ ] **Step 5: Run existing XO Modern tests as an isolation gate**

Run the existing formatter/presentation tests that exercise XO/Teams:

```bash
pytest -q   tests/test_presentation_contract.py   tests/test_v255_teams_delivery_and_icons.py
```

Expected: all pass with no changes to expected Modern payloads.

**Repository workflow checkpoint:** do not commit or push yet. Continue to Task 3.

---

### Task 3: Select Classic only for XO and preserve Modern fallback for all other Teams sources

**Files:**
- Modify: `src/outputs/teams.py`
- Modify: `src/outputs/platform.py`
- Modify: `tests/test_platform_outputs.py`

**Interfaces:**
- Consumes: `TeamsClassicXenOrchestraFormatter.format(notification) -> dict`
- Produces: `TeamsOutput.classic_source_formatters: dict[str, BaseFormatter]`
- Produces preview metadata:
  - `message_style`: requested normalized style
  - `rendered_style`: actual renderer path (`modern` or `classic`)
  - `formatter`: selected formatter class name

- [ ] **Step 1: Add failing platform selection tests**

Add to `tests/test_platform_outputs.py`:

```python
def test_teams_default_and_explicit_modern_xo_use_existing_formatter():
    item = notification_for_source("xo")
    adapter = TeamsPlatformAdapter(resolver=public_resolver)

    default_preview = adapter.preview(
        destination("teams"),
        item,
    )
    explicit_preview = adapter.preview(
        destination("teams", {"message_style": "modern"}),
        item,
    )

    assert default_preview.metadata["message_style"] == "modern"
    assert default_preview.metadata["rendered_style"] == "modern"
    assert default_preview.metadata["formatter"] == "TeamsFormatter"
    assert explicit_preview.payload == default_preview.payload


def test_teams_classic_xo_uses_isolated_classic_formatter():
    item = notification_for_source("xo")
    preview = TeamsPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("teams", {"message_style": "classic"}),
        item,
    )

    assert preview.metadata["message_style"] == "classic"
    assert preview.metadata["rendered_style"] == "classic"
    assert (
        preview.metadata["formatter"]
        == "TeamsClassicXenOrchestraFormatter"
    )
    assert "🦉 Nowlert CE • Classic Card" in json.dumps(
        preview.payload,
        ensure_ascii=False,
    )


def test_teams_classic_unimplemented_source_temporarily_falls_back_to_modern():
    item = notification_for_source("grafana")
    adapter = TeamsPlatformAdapter(resolver=public_resolver)

    requested_classic = adapter.preview(
        destination("teams", {"message_style": "classic"}),
        item,
    )
    modern = adapter.preview(
        destination("teams", {"message_style": "modern"}),
        item,
    )

    assert requested_classic.metadata["message_style"] == "classic"
    assert requested_classic.metadata["rendered_style"] == "modern"
    assert requested_classic.metadata["formatter"] == "GrafanaTeamsFormatter"
    assert requested_classic.payload == modern.payload
```

Add sanitization/payload-size regression:

```python
def test_teams_classic_xo_is_sanitized_and_bounded():
    item = notification_for_source("xo")
    item.failed_vms = ["VM-FAILED"]
    item.vm_details = {
        "VM-FAILED": {
            "error": "Bearer private-token",
            "size": "22 GiB",
        }
    }
    item.status = "failure"
    item.vm_failed = 1

    preview = TeamsPlatformAdapter(
        resolver=public_resolver
    ).preview(
        destination("teams", {"message_style": "classic"}),
        item,
    )
    encoded = json.dumps(preview.payload)

    assert "private-token" not in encoded
    assert "<redacted>" in encoded
    assert (
        preview.metadata["payload_bytes"]
        <= preview.metadata["payload_limit_bytes"]
    )
```

- [ ] **Step 2: Run the new selection tests and verify RED**

Run:

```bash
pytest -q tests/test_platform_outputs.py -k 'teams_default_and_explicit_modern_xo or teams_classic_xo or teams_classic_unimplemented_source'
```

Expected before implementation: FAIL because Teams preview does not expose style selection and `TeamsOutput` has no Classic registry.

- [ ] **Step 3: Register the pilot Classic formatter without changing legacy send behavior**

In `src/outputs/teams.py`, import:

```python
from formatters.teams_classic_v1 import (
    TeamsClassicXenOrchestraFormatter,
)
```

In `TeamsOutput.__init__()`, after the existing Modern `source_formatters` mapping, add:

```python
self.classic_source_formatters = {
    "xo": TeamsClassicXenOrchestraFormatter(),
}
```

Do not change `TeamsOutput.send()`; the legacy output/config path remains Modern.

- [ ] **Step 4: Implement adapter-level style selection**

Change `TeamsPlatformAdapter.preview()` in `src/outputs/platform.py` to this selection flow:

```python
def preview(self, destination, notification):
    settings = normalize_output_settings(
        "teams",
        destination.settings,
    )
    source = str(notification.source or "").casefold()
    modern_formatter = self.output.source_formatters.get(
        source,
        self.output.default_formatter,
    )

    requested_style = settings["message_style"]
    formatter = modern_formatter
    rendered_style = "modern"

    if requested_style == "classic":
        classic_formatter = self.output.classic_source_formatters.get(
            source
        )
        if classic_formatter is not None:
            formatter = classic_formatter
            rendered_style = "classic"

    payload = formatter._sanitize_payload(
        formatter.format(notification)
    )
    payload_bytes = self.output.payload_size(payload)
    return OutputPreview(
        "teams",
        "application/json",
        payload,
        {
            "formatter": formatter.__class__.__name__,
            "message_style": requested_style,
            "rendered_style": rendered_style,
            "payload_bytes": payload_bytes,
            "payload_limit_bytes": self.output.MAX_PAYLOAD_BYTES,
        },
    )
```

Do not modify `deliver()`.

- [ ] **Step 5: Run the selection tests and verify GREEN**

Run the command from Step 2.

Expected: all selected tests pass.

- [ ] **Step 6: Prove existing Modern behavior and transport remain green**

Run:

```bash
pytest -q   tests/test_platform_outputs.py   tests/test_v255_teams_delivery_and_icons.py   tests/test_presentation_contract.py
```

Expected: all pass.

- [ ] **Step 7: Verify the oversized-payload guard still blocks delivery before POST**

Run specifically:

```bash
pytest -q   tests/test_v255_teams_delivery_and_icons.py::test_platform_teams_rejects_oversized_payload_before_posting   tests/test_v255_teams_delivery_and_icons.py::test_http_202_is_accepted_but_webui_does_not_claim_delivery
```

Expected: both pass.

**Repository workflow checkpoint:** do not commit or push yet. Continue to Task 4.

---

### Task 4: Document the pilot, run the full suite, create one atomic commit, PR, merge, and deploy

**Files:**
- Modify: `docs/platform-outputs.md`
- Modify: `CHANGELOG.md`
- Review all files changed by Tasks 1–3.

**Interfaces:**
- Documents the Teams destination contract and temporary pilot fallback.
- No new runtime interface beyond Tasks 1–3.

- [ ] **Step 1: Update Teams output documentation**

In `docs/platform-outputs.md`, update the destination settings table row:

```markdown
| Microsoft Teams | message style and destination label | workflow webhook URL |
```

Replace the Microsoft Teams section with wording that includes:

```markdown
Microsoft Teams uses native Adaptive Card 1.4 payloads.

Operators can choose **Modern Card** or **Classic Card** per destination.
Modern remains the default and preserves the existing standardized Teams
layout. Existing destinations that do not yet store `message_style` normalize
to Modern automatically.

Classic uses a separate Teams-native renderer so Classic layout changes do not
modify Modern cards. The first Classic implementation is Xen Orchestra and
preserves the approved Nowlert Classic backup lifecycle, field ordering, VM
sections, and omission rules.

During the Xen Orchestra pilot, a Teams destination set to Classic temporarily
falls back to the existing Modern Teams renderer when the event source does not
yet have a Teams Classic renderer. Classic coverage will be expanded
integration-by-integration after live Teams acceptance.

Serialized Teams payloads remain bounded to 28 KiB before transport. HTTP 202
means the Teams workflow accepted the request; the UI does not claim that the
card was rendered in the destination channel without operator confirmation.
```

- [ ] **Step 2: Add the changelog entry**

Under `## Unreleased -> ### Changed`, add:

```markdown
- Add per-destination Modern/Classic selection for Microsoft Teams, keeping
  Modern as the backward-compatible default, and introduce the first
  Teams-native Classic Card for Xen Orchestra with temporary Modern fallback
  for integrations whose Teams Classic renderer has not yet been added.
```

Do not remove the existing Generic Webhook entry.

- [ ] **Step 3: Run the complete repository test suite**

Run:

```bash
pytest
```

Expected: zero failures.

- [ ] **Step 4: Run the CI-equivalent syntax/build validations**

Run at minimum the same local validations represented by the workflow:

```bash
python -m compileall -q src tests
node --check src/webui/app.js
```

Then run any repository scripts used by CI for public YAML/Compose validation if the workflow invokes dedicated commands. Do not skip a validation simply because the unit suite is green.

Expected: all commands exit 0.

- [ ] **Step 5: Review the final diff for isolation**

Verify the product change is limited to the planned files:

```text
src/outputs/settings.py
src/outputs/teams.py
src/outputs/platform.py
src/formatters/teams_classic_v1.py
src/webui/app.js
tests/test_platform_outputs.py
tests/test_webui.py
tests/test_teams_classic_xo.py
docs/platform-outputs.md
CHANGELOG.md
```

Verify specifically that:

- `src/formatters/teams_common.py` is unchanged;
- `src/formatters/teams.py` is unchanged;
- existing Modern source formatter files are unchanged;
- no Discord/Slack/Generic Webhook formatter changed;
- no deployment/infra file changed.

If any unrelated file changed, remove that change before committing.

- [ ] **Step 6: Create one atomic implementation commit**

Only after the full suite and validations are green:

```bash
git add   src/outputs/settings.py   src/outputs/teams.py   src/outputs/platform.py   src/formatters/teams_classic_v1.py   src/webui/app.js   tests/test_platform_outputs.py   tests/test_webui.py   tests/test_teams_classic_xo.py   docs/platform-outputs.md   CHANGELOG.md

git commit -m "Add Teams Classic Xen Orchestra pilot"
```

This is the only planned product commit before the PR CI run.

- [ ] **Step 7: Open the PR to `development` and wait for exact-head CI**

Use a branch such as:

```text
feature/teams-classic-xo-pilot
```

PR description must state:

- Teams destinations now expose Modern/Classic;
- Modern remains default and behaviorally unchanged;
- XO is the only Classic implementation in this pilot;
- other Classic-requested sources temporarily fall back to their existing Modern Teams cards;
- Teams transport and 28 KiB guard are unchanged;
- real Teams acceptance for XO Success/Failed/Skipped follows deployment.

After pushing/opening the PR, stop changes while CI runs.

- [ ] **Step 8: Handle CI strictly**

If CI is green, continue.

If CI is red:

1. inspect the exact failing test/job;
2. identify the root cause;
3. change only the necessary files;
4. run the focused local regression;
5. push one corrective commit;
6. wait for the replacement CI run.

Do not merge with any failing required check.

- [ ] **Step 9: Merge green PR into `development` and verify post-merge deployment**

Squash-merge only after exact-head CI is green.

Then verify the post-merge workflow on the exact Development merge SHA:

- full tests green;
- syntax validation green;
- production image build green;
- **Build and deploy CE Development** green;
- deployed WebUI acceptance bundle green.

- [ ] **Step 10: Perform live Xen Orchestra Teams Classic acceptance**

After Development deployment is green:

1. open the Teams Development destination;
2. confirm **Message style** shows Modern/Classic and defaults correctly;
3. select **Classic Card** and save;
4. fire an XO successful backup notification;
5. inspect the real rendered Teams card;
6. fire an XO failed backup notification;
7. inspect the real rendered Teams card;
8. fire an XO skipped backup notification;
9. inspect the real rendered Teams card.

Record any visual/layout defects separately from semantic/content defects.

If visual tuning is required, modify only `src/formatters/teams_classic_v1.py` and its Classic tests unless the acceptance finding proves a selector/platform bug. Do not touch the Modern renderer as part of Classic polish.

XO is accepted only when Success, Failed, and Skipped cards are all approved in real Teams. After that, start the next integration as a separate scoped Classic implementation.
