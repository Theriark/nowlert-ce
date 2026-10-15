"""Audit pages and summaries use the same complete, private-safe event set."""
import pytest

from storage.audit_events import AuditEventStore
from test_platform_api import call, login, platform_api


NOW = 1_800_000_000
DAY = 86400


@pytest.fixture
def audit_case(platform_api):
    platform = platform_api
    headers = login(platform)
    api = platform["service"].platform
    admin, owner = platform["admin"], platform["owner"]
    own_private = api.destinations.create(admin.actor, admin.id, "Admin private", "webhook")
    other_private = api.destinations.create(owner.actor, owner.id, "Other private", "webhook")
    shared = api.destinations.create(owner.actor, owner.id, "Other shared", "webhook", shared=True)
    rows = [(owner.id, "older.login", "session", None, "success", NOW - 1, True)] * 620
    rows += [
        (owner.id, "ordinary", "user", other_private.id, "success", NOW, True),
        (owner.id, "own.destination", "destination", own_private.id, "FAILED", NOW - 7 * DAY, True),
        (admin.id, "private.destination", "destination", other_private.id, "error", NOW, False),
        (owner.id, "shared.filter", "destination_filter", shared.id, "warning", NOW - 14 * DAY, True),
        (owner.id, "deleted.user", "destination", "deleted", "failed", NOW, False),
        (admin.id, "deleted.admin", "destination", "deleted", "accepted", NOW - 14 * DAY - 1, True),
        (None, "missing.actor", "destination_filter", "deleted", "denied", NOW - 7 * DAY - 1, True),
        (owner.id, "missing.resource", "destination_filter", None, "warning", NOW, False),
        (admin.id, "missing.admin", "destination", None, "healthy", NOW - 14 * DAY, True),
        (None, "shared.anonymous", "destination", shared.id, "retrying", NOW - 7 * DAY - 1, True),
        (None, "private.anonymous", "destination_filter", other_private.id, "failed", NOW, False),
        (admin.id, "sync", "platform", None, "custom", NOW, True),
        (admin.id, "future", "platform", None, "success", NOW + 1, True),
    ]
    with platform["database"].transaction() as connection:
        connection.execute("DELETE FROM audit_events")
        for actor, action, resource, resource_id, outcome, timestamp, _visible in rows:
            connection.execute(
                "INSERT INTO audit_events(actor_user_id,action,resource_type,resource_id,outcome,details_json,created_at) VALUES(?,?,?,?,?,'{}',?)",
                (actor, action, resource, resource_id, outcome, timestamp),
            )
        stored = connection.execute("SELECT * FROM audit_events ORDER BY id DESC").fetchall()
    expected = [dict(record) for record, row in zip(stored, reversed(rows)) if row[-1]]
    api.audit.clock = lambda: NOW
    return platform, headers, api, rows, expected


@pytest.mark.parametrize("size", [25, 50, 100, 150, 250, 500])
def test_all_visible_events_are_paged_beyond_500_with_last_page_clamped(audit_case, size):
    platform, headers, _api, _rows, expected = audit_case
    first = call(platform, "GET", f"/api/v2/audit-events/page/1/size/{size}", headers=headers)
    assert first.status == 200
    assert first.payload["pagination"]["total"] == len(expected) > 500
    assert [event["id"] for event in first.payload["audit_events"]] == [row["id"] for row in expected[:size]]
    last = call(platform, "GET", f"/api/v2/audit-events/page/999/size/{size}", headers=headers)
    last_page = (len(expected) + size - 1) // size
    assert last.payload["pagination"] == {"page": last_page, "page_size": size, "total": len(expected), "total_pages": last_page}
    assert [event["id"] for event in last.payload["audit_events"]] == [row["id"] for row in expected[(last_page - 1) * size:]]


def test_page_decodes_only_requested_rows_and_matches_existing_visibility_policy(audit_case, monkeypatch):
    platform, headers, api, _rows, expected = audit_case
    with platform["database"].connect() as connection:
        rows = connection.execute("SELECT * FROM audit_events ORDER BY id DESC").fetchall()
    policy_ids = [row["id"] for row in rows if api._access_store().audit_event_visible(platform["admin"].actor, AuditEventStore._event(row))]
    assert policy_ids == [row["id"] for row in expected]
    decode = AuditEventStore._event
    decoded = []
    def track(row):
        decoded.append(row["id"])
        return decode(row)
    monkeypatch.setattr(AuditEventStore, "_event", staticmethod(track))
    response = call(platform, "GET", "/api/v2/audit-events/page/2/size/25", headers=headers)
    assert response.status == 200
    assert len(decoded) == len(response.payload["audit_events"]) == 25


def test_summary_has_complete_visible_total_and_exact_7_and_14_day_boundaries(audit_case):
    platform, headers, _api, rows, expected = audit_case
    response = call(platform, "GET", "/api/v2/audit-events/summary", headers=headers)
    assert response.status == 200
    summary = response.payload["summary"]
    assert summary["total"] == len(expected)
    assert summary["current"] == {"success": 621, "warning": 0, "failed": 1, "other": 1}
    assert summary["previous"] == {"success": 1, "warning": 2, "failed": 1, "other": 0}
    assert len(str(response.payload)) < 500


def test_nonadmin_audit_pages_legacy_and_summary_stay_empty(audit_case):
    platform, _headers, _api, _rows, _expected = audit_case
    user_headers = login(platform, "owner-user", "owner secure password")
    for path in ("/audit-events", "/audit-events/page/2/size/500"):
        response = call(platform, "GET", "/api/v2" + path, headers=user_headers)
        assert response.status == 200
        assert response.payload["audit_events"] == []
        if "pagination" in response.payload:
            assert response.payload["pagination"]["total"] == 0
    summary = call(platform, "GET", "/api/v2/audit-events/summary", headers=user_headers)
    assert summary.status == 200
    assert summary.payload["summary"] == {"total": 0, "current": {"success": 0, "warning": 0, "failed": 0, "other": 0}, "previous": {"success": 0, "warning": 0, "failed": 0, "other": 0}}


def test_legacy_audit_list_remains_bounded_and_private_safe(audit_case):
    platform, headers, _api, _rows, expected = audit_case
    response = call(platform, "GET", "/api/v2/audit-events", headers=headers)
    assert response.status == 200
    assert [event["id"] for event in response.payload["audit_events"]] == [row["id"] for row in expected[:500]]


def test_deleted_actor_uses_missing_actor_visibility_and_invalid_size_keeps_default(audit_case):
    platform, headers, _api, _rows, expected = audit_case
    deleted = platform["service"].platform.users.create("deleted-actor", "deleted actor secure password")
    with platform["database"].transaction() as connection:
        connection.execute("INSERT INTO audit_events(actor_user_id,action,resource_type,resource_id,outcome,created_at) VALUES(?,'deleted.actor','destination','missing','success',?)", (deleted.id, NOW))
    before = call(platform, "GET", "/api/v2/audit-events/page/0/size/7", headers=headers)
    assert before.payload["pagination"] == {"page": 1, "page_size": 25, "total": len(expected), "total_pages": (len(expected) + 24) // 25}
    with platform["database"].transaction() as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (deleted.id,))
    after = call(platform, "GET", "/api/v2/audit-events/page/1", headers=headers)
    assert after.payload["pagination"]["total"] == len(expected) + 1
    assert after.payload["audit_events"][0]["actor_user_id"] is None


def test_summary_requires_session_and_preserves_safe_server_errors(audit_case, monkeypatch):
    platform, headers, _api, _rows, _expected = audit_case
    assert call(platform, "GET", "/api/v2/audit-events/summary").status == 401
    assert call(platform, "POST", "/api/v2/audit-events/summary", headers=headers).status == 405
    def unavailable(_self, _actor):
        raise RuntimeError("synthetic private database detail")
    monkeypatch.setattr(AuditEventStore, "summary_visible", unavailable)
    response = call(platform, "GET", "/api/v2/audit-events/summary", headers=headers)
    assert response.status == 500
    assert "summary" not in response.payload
    assert "synthetic private database detail" not in str(response.payload)
