"""Owned-route delivery, retry, secret, and safe-history tests."""

from __future__ import annotations

import threading
import time

import pytest

from api.security import hash_password
from models import Notification
from storage.database import Database
from storage.delivery import (
    DeliveryHistoryStore,
    DeliveryResult,
    PlatformDeliveryService,
)
from storage.destinations import DestinationStore
from storage.route_destinations import RouteDestinationStore
from storage.routes import RouteStore
from storage.secrets import SecretStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x04" * 16, iterations=1_000)


@pytest.fixture
def delivery_platform(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("owner-user", "owner secure password")
    another = users.create("another-user", "another secure password")
    secrets = SecretStore(database)
    destinations = DestinationStore(database)
    routes = RouteStore(database)
    history = DeliveryHistoryStore(database)
    return {
        "database": database,
        "users": users,
        "admin": admin,
        "owner": owner,
        "another": another,
        "secrets": secrets,
        "destinations": destinations,
        "routes": routes,
        "history": history,
    }


def configured_route(platform, *, output_type="webhook", owner_key="owner"):
    owner = platform[owner_key]
    secret = platform["secrets"].create(
        owner.actor,
        owner.id,
        f"{owner.username} delivery credential",
        "webhook",
        f"private-value-for-{owner.username}",
    )
    destination = platform["destinations"].create(
        owner.actor,
        owner.id,
        f"{owner.username} destination",
        output_type,
        secret_id=secret.id,
        settings={},
    )
    route = platform["routes"].create(
        owner.actor,
        owner.id,
        f"{owner.username} route",
        "grafana",
        destination.id,
    )
    return owner, destination, route


def configured_multi_destination_route(platform, names):
    owner = platform["owner"]
    route = platform["routes"].create(
        owner.actor,
        owner.id,
        "parallel route",
        "grafana",
    )
    relationships = RouteDestinationStore(platform["database"])
    destinations = []
    for name in names:
        destination = platform["destinations"].create(
            owner.actor,
            owner.id,
            name,
            "webhook",
            settings={},
        )
        relationships.replace_for_destination(
            owner.actor,
            destination.id,
            [route.id],
        )
        destinations.append(destination)
    return owner, route, destinations


def test_delivery_uses_matching_owner_route_and_resolves_secret_internally(
    delivery_platform,
):
    owner, destination, route = configured_route(delivery_platform)
    observed = []

    def adapter(target, secret, notification):
        observed.append((target, secret, notification))
        return DeliveryResult(True, response_status=204)

    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {"webhook": adapter},
        sleeper=lambda _delay: None,
    )
    notification = Notification(
        source="grafana",
        title="Synthetic warning",
        status="warning",
        metadata={"severity": "warning"},
    )
    summary = service.deliver(owner.actor, notification)

    assert summary.success is True
    assert (summary.matched_routes, summary.delivered, summary.failed) == (1, 1, 0)
    assert observed[0][0].id == destination.id
    assert observed[0][1] == f"private-value-for-{owner.username}".encode()
    attempt = delivery_platform["history"].list_visible(owner.actor)[0]
    assert attempt.route_id == route.id
    assert attempt.outcome == "delivered"
    assert attempt.response_status == 204
    assert "private-value" not in repr(attempt)


def test_retryable_delivery_records_each_attempt_and_bounded_delays(delivery_platform):
    owner, _destination, _route = configured_route(delivery_platform)
    responses = [
        DeliveryResult(
            False,
            retryable=True,
            response_status=503,
            error_code="upstream_unavailable",
            safe_error="Temporary upstream failure",
        ),
        DeliveryResult(False, retryable=True, response_status=429),
        DeliveryResult(True, response_status=204),
    ]
    delays = []

    def adapter(_target, _secret, _notification):
        return responses.pop(0)

    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {"webhook": adapter},
        maximum_attempts=3,
        retry_delays=(0, 1, 5),
        sleeper=delays.append,
    )
    summary = service.deliver(
        owner.actor,
        Notification(source="grafana", title="Retry test"),
    )
    attempts = sorted(
        delivery_platform["history"].list_visible(owner.actor),
        key=lambda item: item.attempt_number,
    )

    assert summary == type(summary)(1, 1, 0, 3)
    assert [item.outcome for item in attempts] == [
        "retry_scheduled",
        "retry_scheduled",
        "delivered",
    ]
    assert [item.response_status for item in attempts] == [503, 429, 204]
    assert delays == [1.0, 5.0]


def test_nonretryable_failure_is_recorded_once(delivery_platform):
    owner, _destination, _route = configured_route(delivery_platform)
    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {
            "webhook": lambda *_args: DeliveryResult(
                False,
                retryable=False,
                response_status=400,
                error_code="invalid_request",
                safe_error="Request rejected",
            )
        },
        sleeper=lambda _delay: None,
    )
    summary = service.deliver(
        owner.actor,
        Notification(source="grafana", title="Failure test"),
    )
    attempts = delivery_platform["history"].list_visible(owner.actor)

    assert (summary.delivered, summary.failed, summary.attempts) == (0, 1, 1)
    assert attempts[0].outcome == "failed"
    assert attempts[0].error_code == "invalid_request"


def test_adapter_exceptions_do_not_reach_safe_history(delivery_platform):
    owner, _destination, _route = configured_route(delivery_platform)

    def adapter(*_args):
        raise RuntimeError("secret internal exception value")

    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {"webhook": adapter},
    )
    service.deliver(owner.actor, Notification(source="grafana", title="Exception"))
    attempt = delivery_platform["history"].list_visible(owner.actor)[0]

    assert attempt.error_code == "delivery_exception"
    assert attempt.safe_error == ""
    assert "internal exception" not in repr(attempt)


def test_history_sanitizes_credentials_and_never_stores_secret_values(
    delivery_platform,
):
    owner, _destination, _route = configured_route(delivery_platform)
    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {
            "webhook": lambda *_args: DeliveryResult(
                False,
                safe_error="token=private-token password=hunter2",
            )
        },
    )
    service.deliver(
        owner.actor,
        Notification(
            source="grafana",
            title="authorization=Bearer private-value",
        ),
    )
    attempt = delivery_platform["history"].list_visible(owner.actor)[0]
    raw_database = delivery_platform["database"].path.read_bytes()

    assert "private-token" not in attempt.safe_error
    assert "hunter2" not in attempt.safe_error
    assert "private-value" not in attempt.title
    assert b"private-token" not in raw_database
    assert b"hunter2" not in raw_database


def test_delivery_and_history_are_owner_scoped(delivery_platform):
    owner, _destination, _route = configured_route(delivery_platform)
    another = delivery_platform["another"]
    calls = []
    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {"webhook": lambda *_args: calls.append(True) or True},
    )
    notification = Notification(source="grafana", title="Owner scoped")

    assert service.deliver(another.actor, notification).matched_routes == 0
    assert service.deliver(owner.actor, notification).delivered == 1
    assert calls == [True]
    assert delivery_platform["history"].list_visible(another.actor) == []
    assert len(delivery_platform["history"].list_visible(owner.actor)) == 1
    assert len(delivery_platform["history"].list_visible(
        delivery_platform["admin"].actor
    )) == 1


def test_shared_destination_can_deliver_without_revealing_owner_secret(
    delivery_platform,
):
    admin = delivery_platform["admin"]
    another = delivery_platform["another"]
    secret = delivery_platform["secrets"].create(
        admin.actor,
        admin.id,
        "Shared delivery secret",
        "webhook",
        "shared-private-value",
    )
    destination = delivery_platform["destinations"].create(
        admin.actor,
        admin.id,
        "Shared destination",
        "webhook",
        secret_id=secret.id,
        shared=True,
    )
    delivery_platform["routes"].create(
        another.actor,
        another.id,
        "Use shared destination",
        "grafana",
        destination.id,
    )
    observed = []
    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {"webhook": lambda _target, value, _event: observed.append(value) or True},
    )

    assert service.deliver(
        another.actor,
        Notification(source="grafana", title="Shared"),
    ).success is True
    assert observed == [b"shared-private-value"]
    with pytest.raises(PermissionError):
        delivery_platform["secrets"].resolve(another.actor, secret.id)


def test_missing_adapter_is_a_safe_terminal_failure(delivery_platform):
    owner, _destination, _route = configured_route(
        delivery_platform,
        output_type="webhook",
    )
    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {},
    )
    summary = service.deliver(owner.actor, Notification(source="grafana"))
    attempt = delivery_platform["history"].list_visible(owner.actor)[0]

    assert summary.failed == 1
    assert attempt.error_code == "adapter_unavailable"


def test_delivery_fanout_starts_fast_destination_while_slow_destination_is_blocked(
    delivery_platform,
):
    owner, _route, _destinations = configured_multi_destination_route(
        delivery_platform,
        ("A slow destination", "B fast destination"),
    )
    slow_started = threading.Event()
    fast_started = threading.Event()
    release_slow = threading.Event()

    def adapter(target, _secret, _notification):
        if target.name.startswith("A slow"):
            slow_started.set()
            release_slow.wait(2)
        else:
            fast_started.set()
        return DeliveryResult(True, response_status=204)

    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {"webhook": adapter},
    )
    summary = []

    worker = threading.Thread(
        target=lambda: summary.append(
            service.deliver(
                owner.actor,
                Notification(source="grafana", title="Parallel fanout"),
            )
        )
    )
    worker.start()
    assert slow_started.wait(1)
    try:
        assert fast_started.wait(0.25)
    finally:
        release_slow.set()
        worker.join(timeout=3)

    assert not worker.is_alive()
    assert summary[0].delivered == 2


def test_retry_sleep_on_one_destination_does_not_block_another(
    delivery_platform,
):
    owner, _route, _destinations = configured_multi_destination_route(
        delivery_platform,
        ("A retry destination", "B fast destination"),
    )
    retry_waiting = threading.Event()
    release_retry = threading.Event()
    fast_done = threading.Event()
    attempts = {"A retry destination": 0}

    def sleeper(_delay):
        retry_waiting.set()
        release_retry.wait(2)

    def adapter(target, _secret, _notification):
        if target.name.startswith("A retry"):
            attempts[target.name] += 1
            if attempts[target.name] == 1:
                return DeliveryResult(
                    False,
                    retryable=True,
                    response_status=503,
                )
        else:
            fast_done.set()
        return DeliveryResult(True, response_status=204)

    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {"webhook": adapter},
        retry_delays=(0, 1),
        sleeper=sleeper,
    )
    worker = threading.Thread(
        target=lambda: service.deliver(
            owner.actor,
            Notification(source="grafana", title="Retry isolation"),
        )
    )
    worker.start()
    assert retry_waiting.wait(1)
    try:
        assert fast_done.wait(0.25)
    finally:
        release_retry.set()
        worker.join(timeout=3)

    assert not worker.is_alive()


def test_delivery_concurrency_controller_is_fair_and_bounded():
    from storage.delivery_concurrency import DeliveryConcurrencyController

    controller = DeliveryConcurrencyController(
        global_limit=3,
        per_destination_limit=2,
        maximum_pending=32,
    )
    lock = threading.Lock()
    release_a = threading.Event()
    two_a_started = threading.Event()
    b_started = threading.Event()
    active_total = 0
    active_a = 0
    max_total = 0
    max_a = 0

    def slow_a():
        nonlocal active_total, active_a, max_total, max_a
        with lock:
            active_total += 1
            active_a += 1
            max_total = max(max_total, active_total)
            max_a = max(max_a, active_a)
            if active_a == 2:
                two_a_started.set()
        try:
            release_a.wait(2)
            return "a"
        finally:
            with lock:
                active_total -= 1
                active_a -= 1

    def fast_b():
        nonlocal active_total, max_total
        with lock:
            active_total += 1
            max_total = max(max_total, active_total)
        try:
            b_started.set()
            return "b"
        finally:
            with lock:
                active_total -= 1

    futures = [controller.submit("destination-a", slow_a) for _ in range(6)]
    future_b = controller.submit("destination-b", fast_b)
    assert two_a_started.wait(1)
    try:
        assert b_started.wait(0.5)
    finally:
        release_a.set()

    assert [future.result(timeout=3) for future in futures] == ["a"] * 6
    assert future_b.result(timeout=3) == "b"
    snapshot = controller.snapshot()
    controller.shutdown()

    assert max_total <= 3
    assert max_a <= 2
    assert snapshot.max_active <= 3
    assert snapshot.max_active_per_destination <= 2


def test_multiple_events_share_per_destination_limit_without_loss(
    delivery_platform,
):
    from storage.delivery_concurrency import DeliveryConcurrencyController

    owner, _route, destinations = configured_multi_destination_route(
        delivery_platform,
        ("Only destination",),
    )
    controller = DeliveryConcurrencyController(
        global_limit=8,
        per_destination_limit=2,
        maximum_pending=64,
    )
    lock = threading.Lock()
    release = threading.Event()
    two_started = threading.Event()
    active = 0
    max_active = 0
    seen = []

    def adapter(_target, _secret, notification):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
            seen.append(notification.title)
            if active == 2:
                two_started.set()
        try:
            release.wait(2)
            return DeliveryResult(True, response_status=204)
        finally:
            with lock:
                active -= 1

    service = PlatformDeliveryService(
        delivery_platform["routes"],
        delivery_platform["destinations"],
        delivery_platform["secrets"],
        delivery_platform["history"],
        {"webhook": adapter},
        concurrency=controller,
    )
    barrier = threading.Barrier(9)
    summaries = []
    failures = []

    def send(index):
        try:
            barrier.wait(timeout=2)
            summaries.append(
                service.deliver(
                    owner.actor,
                    Notification(
                        source="grafana",
                        title=f"event-{index}",
                    ),
                )
            )
        except Exception as error:
            failures.append(error)

    threads = [threading.Thread(target=send, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    barrier.wait(timeout=2)
    assert two_started.wait(1)
    time.sleep(0.05)
    try:
        assert max_active == 2
    finally:
        release.set()
    for thread in threads:
        thread.join(timeout=4)
    controller.shutdown()

    assert failures == []
    assert all(not thread.is_alive() for thread in threads)
    assert len(summaries) == 8
    assert all(summary.delivered == 1 for summary in summaries)
    assert sorted(seen) == [f"event-{index}" for index in range(8)]
    assert destinations[0].id


def test_delivery_concurrency_controller_never_exceeds_global_limit():
    from storage.delivery_concurrency import DeliveryConcurrencyController

    controller = DeliveryConcurrencyController(
        global_limit=3,
        per_destination_limit=3,
        maximum_pending=64,
    )
    lock = threading.Lock()
    release = threading.Event()
    three_started = threading.Event()
    active = 0
    max_active = 0

    def task():
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
            if active == 3:
                three_started.set()
        try:
            release.wait(2)
            return True
        finally:
            with lock:
                active -= 1

    futures = [
        controller.submit(f"destination-{index % 4}", task)
        for index in range(12)
    ]
    assert three_started.wait(1)
    time.sleep(0.05)
    try:
        assert max_active == 3
    finally:
        release.set()
    assert all(future.result(timeout=3) for future in futures)
    controller.shutdown()
