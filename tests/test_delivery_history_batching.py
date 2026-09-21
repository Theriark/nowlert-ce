"""Durable batched delivery-history persistence tests."""

from __future__ import annotations

import sqlite3
import threading

from contextlib import contextmanager

from api.security import hash_password
from models import Notification
from storage.database import Database
from storage.delivery import DeliveryHistoryStore, DeliveryResult
from storage.destinations import DestinationStore
from storage.routes import RouteStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x12" * 16, iterations=1_000)


def history_state(tmp_path, *, batch_wait_seconds=0.001):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    owner = users.bootstrap_admin(
        "administrator",
        "correct horse battery staple",
    )
    destination = DestinationStore(database).create(
        owner.actor,
        owner.id,
        "History destination",
        "webhook",
        settings={},
    )
    route = RouteStore(database).create(
        owner.actor,
        owner.id,
        "History route",
        "grafana",
        destination.id,
    )
    history = DeliveryHistoryStore(
        database,
        batch_wait_seconds=batch_wait_seconds,
    )
    return database, owner, destination, route, history


def test_history_record_returns_constructed_committed_attempt_without_post_read(
    tmp_path,
):
    database, owner, destination, route, history = history_state(tmp_path)

    def unexpected_get(*_args, **_kwargs):
        raise AssertionError("record() must not re-read the inserted attempt")

    history.get = unexpected_get

    attempt = history.record(
        owner.id,
        "delivery-one",
        route,
        Notification(
            source="grafana",
            title="History write",
            status="warning",
            metadata={"severity": "warning"},
        ),
        1,
        "delivered",
        DeliveryResult(True, response_status=204),
        destination_id=destination.id,
    )

    assert attempt.delivery_id == "delivery-one"
    assert attempt.outcome == "delivered"
    assert attempt.response_status == 204

    with database.connect() as connection:
        row = connection.execute(
            "SELECT outcome, response_status FROM delivery_attempts WHERE id = ?",
            (attempt.id,),
        ).fetchone()

    assert row is not None
    assert (row["outcome"], row["response_status"]) == ("delivered", 204)


def test_concurrent_history_records_share_durable_transactions(tmp_path):
    database, owner, destination, route, history = history_state(
        tmp_path,
        batch_wait_seconds=0.05,
    )

    original_transaction = database.transaction
    transaction_count = 0
    count_lock = threading.Lock()

    @contextmanager
    def counted_transaction():
        nonlocal transaction_count
        with count_lock:
            transaction_count += 1
        with original_transaction() as connection:
            yield connection

    database.transaction = counted_transaction

    workers = 12
    barrier = threading.Barrier(workers + 1)
    errors = []

    def write(index):
        try:
            barrier.wait()
            history.record(
                owner.id,
                f"delivery-{index}",
                route,
                Notification(
                    source="grafana",
                    title=f"History {index}",
                    status="warning",
                ),
                1,
                "delivered",
                DeliveryResult(True, response_status=204),
                destination_id=destination.id,
            )
        except Exception as error:
            errors.append(error)

    threads = [
        threading.Thread(target=write, args=(index,))
        for index in range(workers)
    ]
    for thread in threads:
        thread.start()

    barrier.wait()

    for thread in threads:
        thread.join(timeout=3)
        assert not thread.is_alive()

    assert errors == []

    with database.connect() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM delivery_attempts"
        ).fetchone()[0]

    assert count == workers
    assert transaction_count < workers


def test_failed_batched_record_does_not_roll_back_valid_peer(tmp_path):
    database, owner, destination, route, history = history_state(
        tmp_path,
        batch_wait_seconds=0.05,
    )

    history.record(
        owner.id,
        "duplicate-delivery",
        route,
        Notification(source="grafana", title="Original"),
        1,
        "delivered",
        DeliveryResult(True, response_status=204),
        destination_id=destination.id,
    )

    barrier = threading.Barrier(3)
    failures = []

    def write(delivery_id, title):
        try:
            barrier.wait()
            history.record(
                owner.id,
                delivery_id,
                route,
                Notification(source="grafana", title=title),
                1,
                "delivered",
                DeliveryResult(True, response_status=204),
                destination_id=destination.id,
            )
        except Exception as error:
            failures.append((delivery_id, error))

    duplicate = threading.Thread(
        target=write,
        args=("duplicate-delivery", "Duplicate"),
    )
    valid = threading.Thread(
        target=write,
        args=("valid-delivery", "Valid"),
    )

    duplicate.start()
    valid.start()
    barrier.wait()
    duplicate.join(timeout=3)
    valid.join(timeout=3)

    assert not duplicate.is_alive()
    assert not valid.is_alive()
    assert len(failures) == 1
    assert failures[0][0] == "duplicate-delivery"
    assert isinstance(failures[0][1], sqlite3.IntegrityError)

    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT delivery_id
            FROM delivery_attempts
            ORDER BY delivery_id
            """
        ).fetchall()

    assert [row["delivery_id"] for row in rows] == [
        "duplicate-delivery",
        "valid-delivery",
    ]
