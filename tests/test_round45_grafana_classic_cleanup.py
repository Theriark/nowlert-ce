"""Round-45 Grafana Discord Classic cleanup contract."""

from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from outputs.discord import DiscordOutput
from parsers.grafana import Parser as GrafanaParser


FIXTURES = Path(__file__).parent / "fixtures" / "grafana"
FOOTER = {"text": "🦉 Nowlert CE • Classic Card"}


def render_fixture(name: str) -> tuple[object, dict]:
    with (FIXTURES / name).open("rb") as fixture:
        message = BytesParser(policy=policy.default).parse(fixture)

    notification = GrafanaParser().parse(message)
    embed = DiscordOutput().source_formatters["grafana"].format(notification)[
        "embeds"
    ][0]
    return notification, embed


@pytest.mark.parametrize(
    (
        "fixture_name",
        "expected_title",
        "expected_color",
        "alert_field",
    ),
    [
        (
            "alert_firing.eml",
            "🚨 Synthetic API Latency — Firing",
            0xE74C3C,
            "🚨 Alert",
        ),
        (
            "alert_pending.eml",
            "⚠️ Synthetic Queue Depth — Pending",
            0xF39C12,
            "📣 Alert",
        ),
        (
            "alert_no_data.eml",
            "⚠️ Synthetic Host Telemetry — No Data",
            0xF39C12,
            "📣 Alert",
        ),
        (
            "datasource_error.eml",
            "🚨 Synthetic Datasource Evaluation — Error",
            0xE74C3C,
            "🚨 Alert",
        ),
        (
            "alert_resolved.eml",
            "✅ Synthetic API Latency — Resolved",
            0x2ECC71,
            "📣 Alert",
        ),
        (
            "test_notification.eml",
            "ℹ️ Synthetic Contact Point Test — Test",
            0x3498DB,
            "📣 Alert",
        ),
        (
            "multiple_alerts.eml",
            "🚨 Synthetic Grouped Alerts (2 alerts) — Firing",
            0xE74C3C,
            "🚨 Alert",
        ),
    ],
)
def test_grafana_classic_lifecycle_states_use_expected_title_and_color(
    fixture_name,
    expected_title,
    expected_color,
    alert_field,
):
    _notification, embed = render_fixture(fixture_name)
    names = [field["name"] for field in embed["fields"]]

    assert embed["title"] == expected_title
    assert embed["color"] == expected_color
    assert alert_field in names
    assert embed["footer"] == FOOTER


def test_grafana_firing_uses_compact_operator_geometry_and_links():
    _notification, embed = render_fixture("alert_firing.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert list(fields) == [
        "🚨 Alert",
        "📂 Rule",
        "📊 Location",
        "🗄️ Datasource",
        "🏷️ Labels",
        "📈 Values",
        "⏱️ Timing",
        "🔗 Links",
    ]
    assert fields["🚨 Alert"] == "**Severity:** `Critical`"
    assert fields["📂 Rule"].splitlines() == [
        "**Rule:** `Synthetic API Latency Rule`",
        "**Folder:** `Synthetic Platform`",
    ]
    assert fields["📊 Location"].splitlines() == [
        "**Dashboard:** `Synthetic Service Overview`",
        "**Panel:** `Synthetic Latency Panel`",
    ]
    assert fields["🗄️ Datasource"] == "`Synthetic Metrics Source`"
    assert fields["🏷️ Labels"] == (
        "`service=synthetic-api, environment=synthetic-lab`"
    )
    assert fields["📈 Values"] == "`A=2.75, threshold=1.50`"
    assert fields["⏱️ Timing"] == (
        "**Started:** `2026-07-12 10:15:00`"
    )
    assert fields["🔗 Links"] == (
        "[Dashboard](https://grafana.synthetic.invalid/d/synthetic-service)"
        " · [Panel](https://grafana.synthetic.invalid/d/synthetic-service?viewPanel=7)"
        " · [Rule](https://grafana.synthetic.invalid/alerting/grafana/synthetic-rule/view)"
        " · [Silence](https://grafana.synthetic.invalid/alerting/silence/new?synthetic=1)"
    )

    rendered = repr(embed)
    assert "SYNTHETIC-ORG" not in rendered
    assert "The invented service remained above the synthetic threshold." not in rendered
    assert "Synthetic API latency is firing for parser development." not in rendered
    assert "📝 Details" not in rendered
    assert "Event Time" not in rendered
    assert "Dashboard Url" not in rendered
    assert "Panel Url" not in rendered
    assert "Silence Url" not in rendered
    assert "Rule Url" not in rendered
    assert "📧 Email" not in rendered
    assert "📎" not in rendered


def test_grafana_error_keeps_evaluation_error_without_raw_field_dump():
    _notification, embed = render_fixture("datasource_error.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert list(fields) == [
        "🚨 Alert",
        "📂 Rule",
        "🗄️ Datasource",
        "❌ Evaluation Error",
        "⏱️ Timing",
        "🔗 Links",
    ]
    assert fields["❌ Evaluation Error"] == (
        "`Synthetic datasource query could not be evaluated.`"
    )
    assert fields["🔗 Links"] == (
        "[Rule](https://grafana.synthetic.invalid/alerting/grafana/"
        "synthetic-datasource-rule/view)"
    )
    assert "📎 Evaluation Error" not in repr(embed)


def test_grafana_resolved_uses_resolved_time_without_event_time_duplicate():
    _notification, embed = render_fixture("alert_resolved.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert fields["⏱️ Timing"] == (
        "**Resolved:** `2026-07-12 10:30:00`"
    )
    assert "Event Time" not in repr(embed)
    assert "📝 Details" not in repr(embed)


def test_grafana_grouped_alerts_collapse_members_into_one_section():
    notification, embed = render_fixture("multiple_alerts.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert notification.metadata["alert_count"] == 2
    assert "📈 Values" not in fields
    assert fields["👥 Alerts · 2"].splitlines() == [
        "**Synthetic Cache Saturation** · Firing · `A=95`",
        "**Synthetic Worker Failure** · Firing · `B=1`",
    ]

    rendered = repr(embed)
    assert "📎 Alert 1" not in rendered
    assert "📎 Alert 1 State" not in rendered
    assert "📎 Alert 1 Values" not in rendered
    assert "📎 Alert 2" not in rendered
    assert "📎 Alert 2 State" not in rendered
    assert "📎 Alert 2 Values" not in rendered


@pytest.mark.parametrize(
    "fixture_name",
    [
        "alert_firing.eml",
        "alert_pending.eml",
        "alert_no_data.eml",
        "datasource_error.eml",
        "alert_resolved.eml",
        "test_notification.eml",
        "multiple_alerts.eml",
    ],
)
def test_grafana_classic_never_emits_details_email_or_raw_source_fields(
    fixture_name,
):
    _notification, embed = render_fixture(fixture_name)
    names = [field["name"] for field in embed["fields"]]

    assert "📝 Details" not in names
    assert "📧 Email" not in names
    assert all(not name.startswith("📎 ") for name in names)
