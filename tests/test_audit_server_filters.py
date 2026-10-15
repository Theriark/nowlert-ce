"""Audit search, filters, range and sort apply to the full visible history before paging."""
import time

import pytest

from test_platform_api import call, login, platform_api

DAY = 86400


@pytest.fixture
def audit_history(platform_api):
    platform = platform_api
    headers = login(platform)
    admin = platform["admin"]
    now = int(time.time())
    with platform["database"].transaction() as connection:
        connection.execute("DELETE FROM audit_events")
        username = connection.execute(
            "SELECT username FROM users WHERE id = ?", (admin.id,)
        ).fetchone()[0]
        # 120 old events (older than 30 days): the oldest ones are the only 'backup.run' failures.
        for index in range(120):
            connection.execute(
                "INSERT INTO audit_events(actor_user_id,action,resource_type,resource_id,outcome,details_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    admin.id,
                    "backup.run" if index < 3 else "session.login",
                    "platform",
                    None,
                    "failed" if index < 3 else "success",
                    '{"note":"ancient-marker"}' if index == 5 else "{}",
                    now - 60 * DAY - index,
                ),
            )
        # 4 recent events across the two windows.
        recent = [
            ("token.create", "success", '{"note":"needle-detail"}', now - 60),
            ("token.delete", "success", "{}", now - 2 * DAY),
            ("backup.run", "failed", "{}", now - 10 * DAY),
            ("housekeeping.update", "warning", "{}", now - 20 * DAY),
        ]
        for action, outcome, details, created in recent:
            connection.execute(
                "INSERT INTO audit_events(actor_user_id,action,resource_type,resource_id,outcome,details_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (admin.id, action, "platform", None, outcome, details, created),
            )
    return platform, headers, username


def page(platform, headers, query="", number=1, size=25):
    suffix = f"?{query}" if query else ""
    response = call(platform, "GET", f"/api/v2/audit-events/page/{number}/size/{size}{suffix}", headers=headers)
    assert response.status == 200, response.payload
    return response.payload


def test_recent_range_counts_only_matching_events_and_last_page_is_not_falsely_empty(audit_history):
    platform, headers, _username = audit_history
    everything = page(platform, headers, size=25)
    assert everything["pagination"]["total"] == 124
    week = page(platform, headers, "range=7d")
    assert week["pagination"]["total"] == 2
    assert week["pagination"]["total_pages"] == 1
    assert [event["action"] for event in week["audit_events"]] == ["token.delete", "token.create"]
    deep_page = page(platform, headers, "range=7d", number=999)
    assert deep_page["pagination"]["page"] == 1
    assert len(deep_page["audit_events"]) == 2
    month = page(platform, headers, "range=30d")
    assert month["pagination"]["total"] == 4


def test_action_outcome_search_and_sort_apply_before_paging(audit_history):
    platform, headers, username = audit_history
    failed_backups = page(platform, headers, "action=backup.run&outcome=failed")
    assert failed_backups["pagination"]["total"] == 4
    oldest = page(platform, headers, "action=backup.run&sort=oldest")
    newest = page(platform, headers, "action=backup.run&sort=newest")
    assert [event["id"] for event in oldest["audit_events"]] == sorted(event["id"] for event in newest["audit_events"])
    assert oldest["audit_events"][0]["id"] < newest["audit_events"][0]["id"]
    # A match that sits on the oldest page of the full history is found from page 1.
    ancient = page(platform, headers, "search=ancient-marker")
    assert ancient["pagination"]["total"] == 1
    detail = page(platform, headers, "search=needle-detail")
    assert [event["action"] for event in detail["audit_events"]] == ["token.create"]
    by_user = page(platform, headers, f"search={username}&range=7d")
    assert by_user["pagination"]["total"] == 2
    case_insensitive = page(platform, headers, "search=NEEDLE-DETAIL")
    assert case_insensitive["pagination"]["total"] == 1
    none = page(platform, headers, "search=no-such-audit-text")
    assert none["pagination"]["total"] == 0
    assert none["audit_events"] == []


def test_filter_options_span_complete_visible_history(audit_history):
    platform, headers, _username = audit_history
    options = page(platform, headers, "range=7d")["filter_options"]
    assert options["actions"] == ["backup.run", "housekeeping.update", "session.login", "token.create", "token.delete"]
    assert options["outcomes"] == ["failed", "success", "warning"]


def test_ordinary_users_see_no_events_options_or_matches(audit_history):
    platform, _headers, _username = audit_history
    other = login(platform, "owner-user", "owner secure password")
    payload = page(platform, other, "search=token")
    assert payload["pagination"]["total"] == 0
    assert payload["audit_events"] == []
    assert payload["filter_options"] == {"actions": [], "outcomes": []}


@pytest.mark.parametrize(
    "query",
    ["sort=invalid", "range=invalid", "search=x&search=y", "unknown=x", "search=" + "x" * 1001],
)
def test_invalid_audit_queries_are_rejected(audit_history, query):
    platform, headers, _username = audit_history
    response = call(platform, "GET", "/api/v2/audit-events/page/1/size/25?" + query, headers=headers)
    assert response.status == 400
