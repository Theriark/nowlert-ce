# Generic Webhook Discord Classic Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Generic Webhook Classic preview and delivery expose the exact approved Discord Classic source-specific card geometry as neutral `classic_card_v1` JSON without changing Discord, Generic Webhook Modern, routing, or transport behavior.

**Architecture:** Reuse the existing `DiscordPlatformAdapter` already owned by `WebhookPlatformAdapter` to render the same sanitized Discord Classic embed that a Discord Classic destination would receive. Convert only the first embed into a destination-neutral presentation object; keep the top-level `nowlert.event.v1` envelope and all existing webhook transport semantics unchanged.

**Tech Stack:** Python 3.13, pytest, existing Nowlert `Notification`/platform output adapters, Discord Classic formatter contract, GitHub Actions CI.

**Spec:** `docs/superpowers/specs/2026-09-21-generic-webhook-discord-classic-parity-design.md`

## Global Constraints

- Discord Classic remains the visual source of truth for Classic presentation.
- Generic Webhook must not send Discord API payloads directly.
- Generic Webhook Classic must emit neutral `classic_card_v1` presentation data derived from the approved Discord Classic embed.
- The stable top-level `nowlert.event.v1` envelope remains unchanged.
- Source parity covers Xen Orchestra, Zabbix, Grafana, Portainer, Proxmox, QNAP, Synology, TrueNAS, UniFi Network, UniFi Protect, UniFi Drive, Home Assistant, Redfish, Supermicro, HPE iLO, Dell iDRAC, and generic/fallback notifications.
- Generic Webhook Modern Card remains unchanged.
- Generic Webhook transport, retry, idempotency, destination health, ownership, authentication, secrets, routing, and Discord-URL compatibility behavior remain unchanged.
- Do not duplicate source-specific Classic rendering logic into a webhook-only formatter.
- Do not change Discord Classic card content or visual geometry.
- Do not change Slack Classic or Microsoft Teams.
- Do not add custom methods, arbitrary headers, body templates, HMAC controls, or private-network options to the normal WebUI editor.
- Use one implementation branch and one atomic implementation commit before the PR CI run, matching the repository workflow for this change.

## Review Focus

- **Malformed Classic renderer output:** if the Discord Classic preview contains no usable first embed, Generic Webhook preview must fail safely with `ValueError` rather than emit an incomplete presentation.
- **Optional embed members:** missing footer, URL, timestamp, or thumbnail must not make conversion fail; only present neutral keys should be emitted.
- **Field defaults:** a Discord field without `inline` must become `inline: false`, while title/value ordering is preserved exactly.
- **Sensitive data:** Classic conversion must operate on the already-sanitized Discord preview so secret-like content cannot reappear in `presentation`.
- **Unknown sources:** a source with no dedicated Discord formatter must reuse `GenericDiscordFormatter` and still produce a valid `classic_card_v1` presentation.

---

### Task 1: Implement Generic Webhook Classic parity as one atomic change

**Files:**
- Modify: `tests/test_platform_outputs.py`
- Modify: `src/outputs/platform.py`
- Modify: `docs/platform-outputs.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `WebhookPlatformAdapter.discord: DiscordPlatformAdapter`; `DiscordPlatformAdapter.preview(destination: Destination, notification: Notification) -> OutputPreview`; existing `WebhookPlatformAdapter._discord_destination(destination: Destination, style: str) -> Destination`.
- Produces: `WebhookPlatformAdapter._classic_card_from_discord_payload(payload: dict) -> dict`, a neutral `classic_card_v1` converter; `WebhookPlatformAdapter._classic_presentation(destination: Destination, notification: Notification) -> dict`, which obtains the sanitized approved Discord Classic preview and converts it.
- Preserves: `WebhookPlatformAdapter.preview(...)` return type and top-level `nowlert.event.v1` envelope; `WebhookPlatformAdapter.deliver(...)` transport contract.

- [ ] **Step 1: Create the implementation branch from the approved Development head**

Create a new branch from the current green `development` head. Do not reuse the design branch for product code.

Expected branch name:

```text
feature/generic-webhook-discord-classic-parity
```

Before editing, verify that `development` still contains the approved Discord Classic renderer and that the implementation base is not behind the latest green Development commit.

- [ ] **Step 2: Add the failing parity tests first**

In `tests/test_platform_outputs.py`, add these helpers after the existing `notification()` helper:

```python
CLASSIC_PARITY_SOURCES = (
    "xo",
    "zabbix",
    "grafana",
    "portainer",
    "proxmox",
    "qnap",
    "synology",
    "truenas",
    "unifi_network",
    "unifi_protect",
    "unifi_drive",
    "redfish",
    "supermicro",
    "hpe_ilo",
    "dell_idrac",
    "home_assistant",
    "unknown_product",
)


def notification_for_source(source: str) -> Notification:
    item = notification()
    item.source = source
    item.category = {
        "xo": "backup",
        "zabbix": "monitoring",
        "grafana": "monitoring",
        "portainer": "containers",
        "proxmox": "storage",
        "qnap": "storage",
        "synology": "storage",
        "truenas": "storage",
        "unifi_network": "network",
        "unifi_protect": "security",
        "unifi_drive": "backup",
        "redfish": "hardware",
        "supermicro": "hardware",
        "hpe_ilo": "hardware",
        "dell_idrac": "hardware",
        "home_assistant": "automation",
        "unknown_product": "event",
    }[source]
    item.title = f"Synthetic {source} event"
    item.body = f"Synthetic {source} operational detail."
    item.metadata.update(
        {
            "provider": {
                "supermicro": "Supermicro BMC",
                "hpe_ilo": "HPE iLO",
                "dell_idrac": "Dell iDRAC",
                "home_assistant": "Home Assistant",
                "unknown_product": "Synthetic Generic Provider",
            }.get(source, source),
            "system": "SYNTHETIC-SYSTEM",
            "nas_name": "SYNTHETIC-NAS",
            "model": "SYNTHETIC-MODEL",
            "storage_pool": "SYNTHETIC-POOL",
            "controller": "SYNTHETIC-CONTROLLER",
            "client_display_name": "SYNTHETIC-CLIENT",
            "network_name": "SYNTHETIC-LAN",
            "wifi_name": "SYNTHETIC-WIFI",
            "trigger_key": "motion",
            "trigger_device": "SYNTHETIC-CAMERA",
            "alarm_name": "Synthetic alarm",
            "backup_task": "Synthetic backup",
            "area": "Synthetic area",
            "service": "synthetic.service",
            "entity_id": "sensor.synthetic",
            "sensor": "Synthetic sensor",
            "registry": "Synthetic.Registry",
            "message_id": "Synthetic.Message",
            "origin": "/redfish/v1/Systems/1",
        }
    )
    return item


def neutral_classic_from_embed(embed: dict) -> dict:
    result = {
        "style": "classic_card_v1",
        "title": embed.get("title", ""),
        "description": embed.get("description", ""),
        "color": embed.get("color"),
        "fields": [
            {
                "title": field.get("name", ""),
                "value": field.get("value", ""),
                "inline": bool(field.get("inline", False)),
            }
            for field in embed.get("fields", [])
        ],
    }
    footer = embed.get("footer")
    if isinstance(footer, dict) and footer.get("text"):
        result["footer"] = footer["text"]
    for key in ("timestamp", "url"):
        if embed.get(key):
            result[key] = embed[key]
    return result
```

Add a parity test for every dedicated source plus fallback:

```python
@pytest.mark.parametrize("source", CLASSIC_PARITY_SOURCES)
def test_webhook_classic_preview_matches_approved_discord_classic_geometry(source):
    item = notification_for_source(source)
    webhook_adapter = WebhookPlatformAdapter(resolver=public_resolver)
    discord_adapter = DiscordPlatformAdapter(resolver=public_resolver)

    webhook_preview = webhook_adapter.preview(
        destination("webhook", {"message_style": "classic"}),
        item,
    )
    discord_preview = discord_adapter.preview(
        destination("discord", {"components_v2": False}),
        item,
    )

    embed = discord_preview.payload["embeds"][0]
    presentation = webhook_preview.payload["presentation"]

    assert webhook_preview.payload["schema"] == "nowlert.event.v1"
    assert presentation == neutral_classic_from_embed(embed), source
    assert "embeds" not in webhook_preview.payload
    assert "attachments" not in webhook_preview.payload
```

Add an explicit complex-source regression so the test proves the old four-field Generic Webhook Classic output is gone:

```python
def test_webhook_classic_grafana_contains_source_specific_sections():
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "classic"}),
        notification(),
    )
    names = [
        field["title"]
        for field in preview.payload["presentation"]["fields"]
    ]

    assert preview.payload["presentation"]["style"] == "classic_card_v1"
    assert "🚨 Alert" in names
    assert "📂 Rule" in names
    assert "⏱️ Timing" in names
    assert names != ["severity", "status", "source", "category"]
```

Add a hardware-family regression:

```python
@pytest.mark.parametrize(
    ("source", "identity"),
    (
        ("supermicro", "🖥️ Supermicro BMC"),
        ("hpe_ilo", "🖥️ HPE iLO"),
        ("dell_idrac", "🖥️ Dell iDRAC"),
    ),
)
def test_webhook_classic_hardware_reuses_discord_hardware_sections(source, identity):
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "classic"}),
        notification_for_source(source),
    )
    names = [
        field["title"]
        for field in preview.payload["presentation"]["fields"]
    ]

    assert identity in names
    assert "🔎 Hardware Event" in names
```

Add an exact Modern preservation test:

```python
def test_webhook_modern_presentation_contract_is_unchanged():
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "modern"}),
        notification(),
    )

    assert preview.payload["presentation"] == {
        "style": "modern_card",
        "title": "Database latency",
        "message": "token=<redacted> latency is high",
        "facts": [
            {"label": "Severity", "value": "critical"},
            {"label": "Status", "value": "firing"},
            {"label": "Source", "value": "grafana"},
            {"label": "Category", "value": "alert"},
        ],
    }
```

Add the five Review Focus regressions:

```python
def test_classic_card_conversion_rejects_missing_embed():
    with pytest.raises(ValueError, match="Classic preview"):
        WebhookPlatformAdapter._classic_card_from_discord_payload({})


def test_classic_card_conversion_omits_missing_optional_members_and_defaults_inline():
    converted = WebhookPlatformAdapter._classic_card_from_discord_payload(
        {
            "embeds": [
                {
                    "title": "Synthetic",
                    "description": "Synthetic detail",
                    "color": 123,
                    "fields": [{"name": "Field", "value": "Value"}],
                }
            ]
        }
    )

    assert converted == {
        "style": "classic_card_v1",
        "title": "Synthetic",
        "description": "Synthetic detail",
        "color": 123,
        "fields": [
            {"title": "Field", "value": "Value", "inline": False}
        ],
    }


def test_webhook_classic_presentation_remains_secret_safe():
    item = notification()
    item.body = "Bearer private-token must be scrubbed"
    item.metadata["api_key"] = "private-api-key"

    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "classic"}),
        item,
    )
    encoded = json.dumps(preview.payload, sort_keys=True)

    assert "private-token" not in encoded
    assert "private-api-key" not in encoded
    assert "<redacted>" in encoded


def test_webhook_classic_unknown_source_uses_generic_fallback():
    preview = WebhookPlatformAdapter(resolver=public_resolver).preview(
        destination("webhook", {"message_style": "classic"}),
        notification_for_source("unknown_product"),
    )
    names = [
        field["title"]
        for field in preview.payload["presentation"]["fields"]
    ]

    assert "📍 Source" in names
    assert preview.payload["presentation"]["footer"] == (
        "🦉 Nowlert CE • Classic Card"
    )
```

The optional-member test covers footer/URL/timestamp omission and field `inline` defaulting in one bounded conversion case.

- [ ] **Step 3: Run only the new tests and verify RED**

Run:

```bash
pytest -q tests/test_platform_outputs.py -k 'webhook_classic or classic_card_conversion or webhook_modern_presentation_contract'
```

Expected before implementation:

- parity tests fail because Classic presentation is still `style == "classic_embed"` with generic `severity/status/source/category` fields;
- converter tests fail because `_classic_card_from_discord_payload` does not exist;
- the Modern preservation test should already pass and serves as a guardrail.

Do not change production code until the Classic tests fail for these expected reasons.

- [ ] **Step 4: Implement the minimal neutral Classic converter**

In `src/outputs/platform.py`, keep `WebhookPlatformAdapter.__init__` using the existing `self.discord = DiscordPlatformAdapter(...)`.

Add this converter inside `WebhookPlatformAdapter`:

```python
    @staticmethod
    def _classic_card_from_discord_payload(payload: dict) -> dict:
        embeds = payload.get("embeds") if isinstance(payload, dict) else None
        if (
            not isinstance(embeds, list)
            or not embeds
            or not isinstance(embeds[0], dict)
        ):
            raise ValueError(
                "Discord Classic preview did not produce a Classic preview embed"
            )

        embed = embeds[0]
        fields = embed.get("fields")
        if not isinstance(fields, list):
            fields = []

        presentation = {
            "style": "classic_card_v1",
            "title": str(embed.get("title") or ""),
            "description": str(embed.get("description") or ""),
            "color": embed.get("color"),
            "fields": [
                {
                    "title": str(field.get("name") or ""),
                    "value": str(field.get("value") or ""),
                    "inline": bool(field.get("inline", False)),
                }
                for field in fields
                if isinstance(field, dict)
            ],
        }

        footer = embed.get("footer")
        if isinstance(footer, dict) and footer.get("text"):
            presentation["footer"] = str(footer["text"])

        for key in ("timestamp", "url"):
            if embed.get(key):
                presentation[key] = embed[key]

        return presentation
```

Do **not** copy `thumbnail`, `embeds`, `attachments`, or any Discord transport data into the neutral presentation. This intentionally avoids leaking `nowlert-asset://` Discord media references into arbitrary webhook receivers.

Add the presentation method:

```python
    def _classic_presentation(self, destination, notification) -> dict:
        discord_destination = self._discord_destination(
            destination,
            "classic",
        )
        preview = self.discord.preview(
            discord_destination,
            notification,
        )
        return self._classic_card_from_discord_payload(
            preview.payload
        )
```

The call through `DiscordPlatformAdapter.preview` is intentional: it selects the same dedicated/default formatter, forces `components_v2=False`, and sanitizes the resulting Classic payload before Generic Webhook converts it.

- [ ] **Step 5: Switch only the Classic branch of Generic Webhook preview**

Replace the current Classic branch inside `WebhookPlatformAdapter.preview` with the shared Discord Classic presentation while leaving Modern generation byte-for-byte equivalent.

Use this shape:

```python
        payload = safe_event_envelope(notification)
        if settings["message_style"] == "classic":
            payload["presentation"] = self._classic_presentation(
                destination,
                notification,
            )
        else:
            payload["presentation"] = self._presentation(
                payload,
                settings["message_style"],
            )
```

Leave `_presentation(payload, style)` in place for Modern compatibility. The Classic branch inside that helper may be removed after the new path is green because no new Generic Webhook Classic preview should use the old minimal `classic_embed` object.

Do not modify `deliver()` except where necessary to keep it calling `preview()`; the existing fixed POST, idempotency header, safe URL validation, retries, and Discord-URL delegation must remain unchanged.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run:

```bash
pytest -q tests/test_platform_outputs.py
```

Expected: all tests in `tests/test_platform_outputs.py` pass.

Then run the Discord Classic regression files that own the approved visual geometry:

```bash
pytest -q   tests/test_round40_discord_classic_embed_v1.py   tests/test_round42_final_ee_classic_v1.py   tests/test_round45_grafana_classic_cleanup.py   tests/test_round49_final_discord_classic_cleanup.py   tests/test_generic_fallback_classic.py   tests/test_classic_discord_and_context_actions.py
```

Expected: all pass with no changes required to their expected Discord payloads.

- [ ] **Step 7: Document the new Generic Webhook Classic contract**

In `docs/platform-outputs.md`, replace the Generic Webhook Classic description with explicit parity language:

```markdown
- **Modern Card** (default) — structured card-style presentation metadata; or
- **Classic Card** — the same approved source-specific Classic information
  hierarchy used by Discord Classic, encoded as destination-neutral
  `classic_card_v1` JSON.

Classic mode does not send a Discord webhook payload. Nowlert renders the
approved Discord Classic presentation first, then converts its title,
description, color, ordered fields, footer, and optional URL/timestamp into the
`presentation` object inside the stable `nowlert.event.v1` envelope.
Discord-only `embeds`, attachments, webhook query parameters, and media upload
semantics are not exposed to generic receivers.
```

Add a compact example:

```json
{
  "schema": "nowlert.event.v1",
  "source": "grafana",
  "presentation": {
    "style": "classic_card_v1",
    "title": "🚨 Database latency — Firing",
    "description": "Database latency is high.",
    "color": 15158332,
    "fields": [
      {
        "title": "🚨 Alert",
        "value": "**Severity:** `critical`",
        "inline": false
      }
    ],
    "footer": "🦉 Nowlert CE • Classic Card"
  }
}
```

State explicitly that users should consume the stable event envelope for automation logic and treat `presentation` as optional rendering metadata.

In `CHANGELOG.md` under `## Unreleased`, replace the current “No unreleased changes…” line with:

```markdown
### Changed

- Generic Webhook Classic now reuses the approved source-specific Discord
  Classic presentation and exposes it as destination-neutral
  `classic_card_v1` metadata inside the existing `nowlert.event.v1`
  envelope, without changing Generic Webhook Modern or transport behavior.
```

- [ ] **Step 8: Run the complete repository test suite before committing**

Run:

```bash
pytest
```

Expected: full suite passes with zero failures.

Then run the syntax/build validations represented in CI if they are separate from pytest. At minimum:

```bash
python -m compileall -q src tests
```

Expected: exit code 0.

Review the final diff and verify the only product/documentation files changed are:

```text
src/outputs/platform.py
tests/test_platform_outputs.py
docs/platform-outputs.md
CHANGELOG.md
```

No Discord formatter file should need modification for this implementation because the existing Discord Classic renderer is being reused directly.

- [ ] **Step 9: Create one atomic implementation commit**

Commit all four files together only after the full suite is green:

```bash
git add   src/outputs/platform.py   tests/test_platform_outputs.py   docs/platform-outputs.md   CHANGELOG.md
git commit -m "Reuse Discord Classic cards for generic webhooks"
```

Do not add a second implementation commit unless CI reveals a defect. If CI is red, fix the exact failure, rerun the relevant tests locally, and add one corrective commit only as required by the established repository workflow.

- [ ] **Step 10: Open the PR, wait for green CI, merge, and verify Development deployment**

Open a PR from `feature/generic-webhook-discord-classic-parity` to `development`.

The PR description must state:

- Generic Webhook Classic now derives from approved Discord Classic;
- Generic Webhook still sends neutral `nowlert.event.v1` JSON, not Discord webhook JSON;
- Modern webhook presentation is unchanged;
- Discord Classic/Modern, Slack, Teams, routing, and transport behavior are unchanged;
- test coverage includes all dedicated Discord Classic sources plus generic fallback.

Wait for the exact PR-head CI run to complete successfully before merging.

Merge into `development` only after green CI, then wait for the post-merge Development CI/deployment tied to the exact merge SHA and verify **Build and deploy CE Development** succeeds before asking for live Generic Webhook acceptance testing.
