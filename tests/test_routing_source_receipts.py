"""Source receipt counts stay independent of destination fanout and retries."""
import time

import pytest

from models import Notification
from storage.delivery import DeliveryResult
from storage.routing_flow import delivery_snapshot
from test_route_destination_api import api, create_destination, create_route, login


def configured(api):
    headers = login(api)
    route = create_route(api, headers, "Source event")
    targets = [create_destination(api, headers, name, [route["id"]])
               for name in ("First", "Second")]
    return api["service"].platform, route, targets


def read(api, actor=None, since=0):
    return delivery_snapshot(api["database"], actor or api["admin"].actor, since)


def event():
    return Notification(source="grafana", title="Identical input",
                        metadata={"severity": "warning", "_input_type": "http"})


def test_source_receipt_is_one_for_two_destinations_and_same_object_is_fresh(api):
    platform, route, targets = configured(api)
    notification = event()
    platform.delivery.deliver(api["admin"].actor, notification)
    data = read(api)
    assert data["metrics"]["received"] == 1
    assert data["metrics"]["delivered"] == 2
    assert data["by_route"][route["id"]]["received"] == 1
    assert all(data["by_destination"][target["id"]]["received"] == 1 for target in targets)
    platform.delivery.deliver(api["admin"].actor, notification)
    assert read(api)["metrics"]["received"] == 2


@pytest.mark.parametrize("blocked", [1, 2])
def test_filtered_fanout_counts_one_receipt_and_each_destination_decision(api, blocked):
    platform, route, targets = configured(api)
    for target in targets[:blocked]:
        platform.filters.set_rules(api["admin"].actor, target["id"], "grafana",
                                  {"policy": [{"action": "block", "conditions": {"severity": ["warning"]}}]})
    platform.delivery.deliver(api["admin"].actor, event())
    data = read(api)
    assert data["metrics"]["received"] == 1
    assert data["metrics"]["filtered"] == blocked
    assert data["metrics"]["delivered"] == 2 - blocked
    assert data["by_route"][route["id"]]["received"] == 1


def test_retries_do_not_become_new_receipts_or_reenter_receive_window(api):
    platform, _route, _targets = configured(api)
    calls = {}
    def adapter(target, _secret, _notification):
        calls[target.id] = calls.get(target.id, 0) + 1
        return DeliveryResult(calls[target.id] > 1, retryable=True)
    platform.delivery.adapters["webhook"] = adapter
    platform.delivery.sleeper = lambda _delay: None
    platform.delivery.deliver(api["admin"].actor, event())
    assert read(api)["metrics"]["received"] == 1
    assert read(api)["metrics"]["delivered"] == 2
    cutoff = int(time.time()) - 20
    with api["database"].transaction() as connection:
        connection.execute("UPDATE routing_flow_events SET created_at = ?", (cutoff - 1,))
        connection.execute("UPDATE delivery_attempts SET created_at = ? WHERE attempt_number = 1", (cutoff - 1,))
    assert read(api, since=cutoff)["metrics"]["received"] == 0


def test_source_receipt_visibility_is_applied_before_deduplication(api):
    platform, _route, targets = configured(api)
    other = platform.users.create("other-owner", "another secure password")
    platform.delivery.deliver(api["admin"].actor, event())
    assert read(api, other.actor)["metrics"]["received"] == 0
    with api["database"].transaction() as connection:
        connection.execute("UPDATE destinations SET shared = 1 WHERE id = ?", (targets[0]["id"],))
    data = read(api, other.actor)
    assert data["metrics"]["received"] == 1
    assert data["metrics"]["delivered"] == 1
    assert targets[1]["id"] not in data["by_destination"]


def test_legacy_source_counts_are_unknown_but_destination_counts_are_preserved(api):
    platform, route, targets = configured(api)
    platform.delivery.deliver(api["admin"].actor, event())
    with api["database"].transaction() as connection:
        connection.execute("UPDATE routing_flow_events SET source_event_id = NULL")
        connection.execute("UPDATE delivery_attempts SET source_event_id = NULL")
    data = read(api)
    assert data["metrics"]["received"] is None
    assert data["by_route"][route["id"]]["received"] is None
    assert data["metrics"]["delivered"] == 2
    assert all(data["by_destination"][target["id"]]["received"] == 1 for target in targets)
    with api["database"].transaction() as connection:
        connection.execute("UPDATE routing_flow_events SET created_at = 1")
        connection.execute("UPDATE delivery_attempts SET created_at = 1")
    platform.delivery.deliver(api["admin"].actor, event())
    recent = read(api, since=int(time.time()) - 10)
    assert recent["metrics"]["received"] == 1
    assert recent["by_route"][route["id"]]["received"] == 1
    assert read(api)["metrics"]["received"] is None


def test_bridge_shares_one_source_identity_across_destination_owners(api):
    from storage.routing_bridge import PlatformRoutingBridge
    from test_configuration_bridge import RecordingAdapter, Registry
    platform, _route, targets = configured(api)
    other = platform.users.create("second-owner", "another secure password")
    with api["database"].transaction() as connection:
        connection.execute("UPDATE destinations SET owner_user_id = ?, shared = 1, secret_id = NULL WHERE id = ?", (other.id, targets[1]["id"]))
        connection.execute("UPDATE destinations SET shared = 1 WHERE id = ?", (targets[0]["id"],))
    bridge = PlatformRoutingBridge(api["database"], registry=Registry(RecordingAdapter()))
    bridge.delivery.adapters["webhook"] = lambda *_args: DeliveryResult(True)
    bridge.route(event())
    assert read(api)["metrics"]["received"] == 1
    assert read(api)["metrics"]["delivered"] == 2
    with api["database"].connect() as connection:
        rows = connection.execute("SELECT DISTINCT source_event_id FROM delivery_attempts").fetchall()
    assert len(rows) == 1 and rows[0][0]


def test_receipt_identity_survives_schema17_backup_upgrade_and_restore(tmp_path, monkeypatch):
    import storage.database as database_module
    import storage.backups as backup_module
    from storage.database import Database
    from storage.users import UserStore
    from test_route_destination_api import fast_hash
    database = Database(tmp_path / "state" / "nowlert.db")
    with monkeypatch.context() as old:
        old.setattr(database_module, "MIGRATIONS", database_module.MIGRATIONS[:17])
        old.setattr(database_module, "LATEST_SCHEMA_VERSION", 17)
        old.setattr(backup_module, "LATEST_SCHEMA_VERSION", 17)
        assert database.migrate() == 17
        admin = UserStore(database, password_hasher=fast_hash).bootstrap_admin("administrator", "correct horse battery staple")
        with database.transaction() as connection:
            connection.execute("INSERT INTO routing_flow_events(owner_user_id,route_id,destination_id,source,filtered,created_at) VALUES (?,?,?,?,?,?)",
                               (admin.id, "legacy-route", "legacy-destination", "grafana", 1, int(time.time())))
        backups = backup_module.StateBackupStore(database)
        backup = backups.create(admin.actor)
    assert database.migrate() == 18
    assert delivery_snapshot(database, admin.actor, 0)["metrics"]["received"] is None
    backups.restore(admin.actor, backup.id, backup.id)
    assert database.schema_version == 18
    assert database.migrate() == 18
    with database.connect() as connection:
        assert connection.execute("SELECT source_event_id FROM routing_flow_events").fetchone()[0] is None
        assert "source_event_id" in {row[1] for row in connection.execute("PRAGMA table_info(delivery_attempts)")}


def test_duplicate_candidate_routes_record_one_destination_filter_decision(api):
    platform, route, targets = configured(api)
    headers = login(api)
    second = create_route(api, headers, "Second candidate")
    with api["database"].transaction() as connection:
        connection.execute("INSERT INTO route_destinations(route_id,destination_id,created_at) VALUES (?,?,?)",
                           (second["id"], targets[0]["id"], int(time.time())))
    platform.delivery.deliver(api["admin"].actor, event())
    data = read(api)
    assert data["metrics"]["received"] == 1
    assert data["by_destination"][targets[0]["id"]]["received"] == 1


def test_unfiltered_delivery_service_records_source_identity_without_filter_telemetry(api):
    from storage.delivery import PlatformDeliveryService
    platform, _route, _targets = configured(api)
    service = PlatformDeliveryService(platform.routes, platform.destinations, platform.secrets,
                                      platform.history, platform.delivery.adapters,
                                      relationships=platform.delivery.relationships)
    service.deliver(api["admin"].actor, event())
    data = read(api)
    assert data["metrics"]["received"] == 1
    assert data["metrics"]["delivered"] == 2
    with api["database"].connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM routing_flow_events").fetchone()[0] == 0
