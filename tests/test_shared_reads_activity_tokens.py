"""Shared read connections, Users page account activity and the token picker."""
from pathlib import Path

from storage.database import Database
from test_platform_api import call, login, platform_api  # noqa: F401  (fixture)


ROOT = Path(__file__).resolve().parents[1]


def test_reads_share_one_connection_but_transactions_get_their_own(tmp_path):
    database = Database(tmp_path / "nowlert.db")
    database.migrate()
    with database.connect() as first, database.connect() as second:
        assert first is not second
    with database.reading():
        with database.connect() as first, database.connect() as second:
            assert first is second
        with database.reading(), database.connect() as nested:
            assert nested is first
        with database.transaction() as writer:
            assert writer is not first
            writer.execute("CREATE TABLE shared_read_probe (value INTEGER)")
            writer.execute("INSERT INTO shared_read_probe VALUES (1)")
        with database.connect() as reader:
            assert reader.execute("SELECT value FROM shared_read_probe").fetchone()[0] == 1
    with database.connect() as after:
        assert after is not first


def test_account_category_returns_sign_ins_even_when_noise_is_newer(platform_api):  # noqa: F811
    platform = platform_api
    headers = login(platform)
    with platform["database"].transaction() as connection:
        connection.execute("DELETE FROM audit_events")
        connection.execute(
            "INSERT INTO audit_events(actor_user_id,action,resource_type,resource_id,outcome,details_json,created_at) VALUES(?,?,?,?,?,'{}',?)",
            (platform["admin"].id, "session.login", "session", None, "success", 1),
        )
        connection.execute(
            "INSERT INTO audit_events(actor_user_id,action,resource_type,resource_id,outcome,details_json,created_at) VALUES(?,?,?,?,?,'{}',?)",
            (platform["admin"].id, "user.password", "user", platform["owner"].id, "success", 2),
        )
        for index in range(600):
            connection.execute(
                "INSERT INTO audit_events(actor_user_id,action,resource_type,resource_id,outcome,details_json,created_at) VALUES(NULL,'email.mailbox.sync','mailbox',NULL,'success','{}',?)",
                (10 + index,),
            )
    noisy = call(platform, "GET", "/api/v2/audit-events/page/1/size/500", headers=headers)
    assert {event["action"] for event in noisy.payload["audit_events"]} == {"email.mailbox.sync"}
    account = call(platform, "GET", "/api/v2/audit-events/page/1/size/50?category=account", headers=headers)
    assert account.status == 200
    assert [event["action"] for event in account.payload["audit_events"]] == ["user.password", "session.login"]
    assert account.payload["pagination"]["total"] == 2
    invalid = call(platform, "GET", "/api/v2/audit-events/page/1/size/50?category=mail", headers=headers)
    assert invalid.status == 400


def test_users_page_reads_account_activity_from_its_own_query():
    script = (ROOT / "src/webui/reference_acceptance.js").read_text(encoding="utf-8")
    assert 'request("/audit-events/page/1/size/50?category=account")' in script
    assert "loadUserActivity();" in script


def test_token_integrations_toggle_with_a_plain_click():
    script = (ROOT / "src/webui/qa_patch.js").read_text(encoding="utf-8")
    markup = (ROOT / "src/webui/index.html").read_text(encoding="utf-8")
    assert 'qaBindRouteChoiceList("token-sources");' in script
    assert "openToken = function openTokenWithChoiceState()" in script
    assert "Click to add or remove each integration" in markup


def test_destinations_build_the_route_list_once_per_read_request(platform_api, monkeypatch):  # noqa: F811
    from storage.destination_access import SystemRoutingRouteStore

    platform = platform_api
    headers = login(platform)
    api = platform["service"].platform
    for index in range(3):
        api.destinations.create(platform["admin"].actor, platform["admin"].id, f"Hook {index}", "webhook")
    calls = []
    original = SystemRoutingRouteStore._reconcile_catalogue_route_matrix
    monkeypatch.setattr(
        SystemRoutingRouteStore,
        "_reconcile_catalogue_route_matrix",
        lambda self: calls.append(1) or original(self),
    )
    listed = call(platform, "GET", "/api/v2/destinations", headers=headers)
    assert listed.status == 200 and len(listed.payload["destinations"]) >= 3
    assert len(calls) == 1
    # Outside a read request nothing is cached.
    store = SystemRoutingRouteStore(platform["database"])
    store.list_visible_safe(platform["admin"].actor)
    store.list_visible_safe(platform["admin"].actor)
    assert len(calls) == 3
