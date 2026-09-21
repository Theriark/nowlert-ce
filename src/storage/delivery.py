"""Owned-route delivery orchestration with retries and safe history."""

from __future__ import annotations

import threading
import time
import uuid

from collections import deque

from dataclasses import dataclass
from typing import Callable

from models import Notification
from storage.database import Database
from storage.delivery_concurrency import (
    DeliveryConcurrencyController,
    default_delivery_concurrency,
)
from storage.destinations import DeliveryDestination, DestinationStore
from storage.ownership import Actor, OwnershipPolicy
from storage.route_destinations import (
    RouteDestinationCandidate,
    RouteDestinationStore,
)
from storage.routes import Route, RouteStore
from storage.sanitize import sanitize_text
from storage.secrets import SecretStore


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    retryable: bool = False
    response_status: int | None = None
    error_code: str = ""
    safe_error: str = ""


@dataclass(frozen=True)
class DeliveryAttempt:
    id: str
    delivery_id: str
    owner_user_id: str
    route_id: str | None
    destination_id: str | None
    source: str
    title: str
    severity: str
    outcome: str
    attempt_number: int
    retryable: bool
    response_status: int | None
    error_code: str
    safe_error: str
    created_at: int
    completed_at: int
    input_type: str = ""
    device_name: str = ""
    event_name: str = ""
    event_description: str = ""
    event_status: str = ""


@dataclass(frozen=True)
class DeliverySummary:
    matched_routes: int
    delivered: int
    failed: int
    attempts: int

    @property
    def success(self) -> bool:
        return self.delivered > 0 and self.failed == 0


DEFAULT_HISTORY_BATCH_SIZE = 32
DEFAULT_HISTORY_BATCH_WAIT_SECONDS = 0.001

_HISTORY_BATCHER_ATTRIBUTE = "_nowlert_delivery_history_batcher"
_HISTORY_BATCHER_CREATION_LOCK = threading.Lock()


@dataclass
class _PendingHistoryWrite:
    values: tuple[object, ...]
    completed: bool = False
    writer: bool = False
    error: Exception | None = None


class _DeliveryHistoryBatcher:
    """Coalesce concurrent history inserts while preserving commit durability."""

    INSERT_SQL = """
        INSERT INTO delivery_attempts(
            id, delivery_id, owner_user_id, route_id, destination_id,
            source, title, severity, outcome, attempt_number,
            retryable, response_status, error_code, safe_error,
            created_at, completed_at, input_type, device_name,
            event_name, event_description, event_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def __init__(
        self,
        database: Database,
        *,
        batch_size: int = DEFAULT_HISTORY_BATCH_SIZE,
        batch_wait_seconds: float = DEFAULT_HISTORY_BATCH_WAIT_SECONDS,
    ):
        self.database = database
        self.batch_size = max(1, int(batch_size))
        self.batch_wait_seconds = max(0.0, float(batch_wait_seconds))
        self._condition = threading.Condition()
        self._pending: deque[_PendingHistoryWrite] = deque()
        self._writer_active = False

    def write(self, values: tuple[object, ...]) -> None:
        pending = _PendingHistoryWrite(values)
        with self._condition:
            self._pending.append(pending)
            if not self._writer_active:
                self._writer_active = True
                pending.writer = True
            self._condition.notify_all()

        while True:
            with self._condition:
                if pending.completed:
                    error = pending.error
                    break
                if not pending.writer:
                    self._condition.wait()
                    continue
            self._write_next_batch()

        if error is not None:
            raise error

    def _write_next_batch(self) -> None:
        with self._condition:
            if not self._pending or not self._pending[0].writer:
                return

            deadline = time.perf_counter() + self.batch_wait_seconds
            while len(self._pending) < self.batch_size:
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)

            batch = [
                self._pending.popleft()
                for _ in range(min(self.batch_size, len(self._pending)))
            ]

        errors = self._write_batch(batch)

        with self._condition:
            for item, error in zip(batch, errors):
                item.error = error
                item.completed = True
                item.writer = False

            if self._pending:
                self._pending[0].writer = True
            else:
                self._writer_active = False

            self._condition.notify_all()

    def _write_batch(
        self,
        batch: list[_PendingHistoryWrite],
    ) -> list[Exception | None]:
        try:
            with self.database.transaction() as connection:
                connection.executemany(
                    self.INSERT_SQL,
                    [item.values for item in batch],
                )
        except Exception:
            # Preserve the old per-record failure semantics. One malformed
            # record must not roll back otherwise valid history entries that
            # happened to share its batch.
            errors: list[Exception | None] = []
            for item in batch:
                try:
                    with self.database.transaction() as connection:
                        connection.execute(self.INSERT_SQL, item.values)
                except Exception as error:
                    errors.append(error)
                else:
                    errors.append(None)
            return errors
        return [None] * len(batch)


def _shared_history_batcher(
    database: Database,
    *,
    batch_size: int,
    batch_wait_seconds: float,
) -> _DeliveryHistoryBatcher:
    with _HISTORY_BATCHER_CREATION_LOCK:
        batcher = getattr(database, _HISTORY_BATCHER_ATTRIBUTE, None)
        if batcher is None:
            batcher = _DeliveryHistoryBatcher(
                database,
                batch_size=batch_size,
                batch_wait_seconds=batch_wait_seconds,
            )
            setattr(database, _HISTORY_BATCHER_ATTRIBUTE, batcher)
        return batcher


class DeliveryHistoryStore:
    def __init__(
        self,
        database: Database,
        *,
        clock: Callable[[], float] = time.time,
        batch_size: int = DEFAULT_HISTORY_BATCH_SIZE,
        batch_wait_seconds: float = DEFAULT_HISTORY_BATCH_WAIT_SECONDS,
    ):
        self.database = database
        self.clock = clock
        self._batcher = _shared_history_batcher(
            database,
            batch_size=batch_size,
            batch_wait_seconds=batch_wait_seconds,
        )

    def record(
        self,
        owner_user_id: str,
        delivery_id: str,
        route: Route,
        notification: Notification,
        attempt_number: int,
        outcome: str,
        result: DeliveryResult,
        destination_id: str | None = None,
    ) -> DeliveryAttempt:
        if outcome not in {"delivered", "failed", "retry_scheduled"}:
            raise ValueError("unsupported delivery outcome")
        resolved_destination = destination_id or route.destination_id
        if not resolved_destination:
            raise ValueError("delivery destination is required")
        now = int(self.clock())
        attempt_id = uuid.uuid4().hex
        source = self._safe(notification.source, 64)
        title = self._safe(notification.title or notification.subject, 256)
        severity = self._safe(
            (notification.metadata or {}).get("severity") or notification.status,
            64,
        )
        error_code = self._safe(result.error_code, 64)
        safe_error = self._safe(result.safe_error, 500)
        metadata = notification.metadata or {}
        input_type = self._safe(metadata.get("_input_type") or "HTTP", 32)
        device_name = self._safe(
            metadata.get("host")
            or metadata.get("hostname")
            or metadata.get("device")
            or metadata.get("node"),
            256,
        )
        event_name = self._safe(
            metadata.get("event_name")
            or metadata.get("event")
            or metadata.get("event_type")
            or notification.title
            or notification.subject,
            256,
        )
        event_description = self._safe(
            notification.body or notification.title or notification.subject,
            1000,
        )
        event_status = self._safe(
            metadata.get("status") or metadata.get("state") or notification.status,
            64,
        )
        response_status = (
            int(result.response_status) if result.response_status is not None else None
        )
        attempt = DeliveryAttempt(
            id=attempt_id,
            delivery_id=str(delivery_id),
            owner_user_id=str(owner_user_id),
            route_id=route.id,
            destination_id=str(resolved_destination),
            source=source,
            title=title,
            severity=severity,
            outcome=outcome,
            attempt_number=int(attempt_number),
            retryable=bool(result.retryable),
            response_status=response_status,
            error_code=error_code,
            safe_error=safe_error,
            created_at=now,
            completed_at=now,
            input_type=input_type,
            device_name=device_name,
            event_name=event_name,
            event_description=event_description,
            event_status=event_status,
        )
        self._batcher.write(
            (
                attempt.id,
                attempt.delivery_id,
                attempt.owner_user_id,
                attempt.route_id,
                attempt.destination_id,
                attempt.source,
                attempt.title,
                attempt.severity,
                attempt.outcome,
                attempt.attempt_number,
                1 if attempt.retryable else 0,
                attempt.response_status,
                attempt.error_code or None,
                attempt.safe_error or None,
                attempt.created_at,
                attempt.completed_at,
                attempt.input_type,
                attempt.device_name,
                attempt.event_name,
                attempt.event_description,
                attempt.event_status,
            )
        )
        return attempt

    def get(self, actor: Actor, attempt_id: str) -> DeliveryAttempt:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM delivery_attempts WHERE id = ?",
                (str(attempt_id),),
            ).fetchone()
        if row is None:
            raise KeyError("delivery attempt not found")
        OwnershipPolicy.require_read(actor, str(row["owner_user_id"]))
        return self._attempt(row)

    def list_visible(
        self, actor: Actor, limit: int = 100, offset: int = 0
    ) -> list[DeliveryAttempt]:
        bounded = max(1, min(int(limit), 500))
        bounded_offset = max(0, int(offset))
        with self.database.connect() as connection:
            if actor.is_admin:
                rows = connection.execute(
                    "SELECT * FROM delivery_attempts ORDER BY created_at DESC, id LIMIT ? OFFSET ?",
                    (bounded, bounded_offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT attempts.* FROM delivery_attempts AS attempts
                    LEFT JOIN destinations
                      ON destinations.id = attempts.destination_id
                    WHERE attempts.owner_user_id = ? OR destinations.shared = 1
                    ORDER BY attempts.created_at DESC, attempts.id LIMIT ? OFFSET ?
                    """,
                    (actor.user_id, bounded, bounded_offset),
                ).fetchall()
        return [self._attempt(row) for row in rows]

    def count_visible(self, actor: Actor) -> int:
        with self.database.connect() as connection:
            if actor.is_admin:
                row = connection.execute(
                    "SELECT COUNT(*) FROM delivery_attempts"
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT COUNT(*) FROM delivery_attempts AS attempts
                    LEFT JOIN destinations
                      ON destinations.id = attempts.destination_id
                    WHERE attempts.owner_user_id = ? OR destinations.shared = 1
                    """,
                    (actor.user_id,),
                ).fetchone()
        return int(row[0] or 0)

    def metrics(self, actor: Actor, since: int) -> dict:
        """Return final delivery outcomes for a server-side history window."""

        where = "created_at >= ?"
        parameters: list[object] = [int(since)]
        if not actor.is_admin:
            where += " AND (owner_user_id = ? OR destination_id IN (SELECT id FROM destinations WHERE shared = 1))"
            parameters.append(actor.user_id)
        with self.database.connect() as connection:
            row = connection.execute(
                f"""
                WITH latest AS (
                    SELECT delivery_id, MAX(attempt_number) AS attempt_number
                    FROM delivery_attempts
                    WHERE {where}
                    GROUP BY delivery_id
                )
                SELECT
                    COUNT(*) AS requests,
                    SUM(CASE WHEN attempts.outcome = 'delivered' THEN 1 ELSE 0 END) AS delivered
                FROM latest
                JOIN delivery_attempts AS attempts
                  ON attempts.delivery_id = latest.delivery_id
                 AND attempts.attempt_number = latest.attempt_number
                """,
                tuple(parameters),
            ).fetchone()
            sources = connection.execute(
                f"SELECT COUNT(DISTINCT source) FROM delivery_attempts WHERE {where}",
                tuple(parameters),
            ).fetchone()[0]
        requests = int(row["requests"] or 0)
        delivered = int(row["delivered"] or 0)
        return {
            "requests": requests,
            "delivered": delivered,
            "success_percent": round(delivered * 100 / requests) if requests else None,
            "observed_sources": int(sources or 0),
        }

    def _safe(self, value, maximum: int) -> str:
        return sanitize_text(value)[:maximum]

    @staticmethod
    def _attempt(row) -> DeliveryAttempt:
        return DeliveryAttempt(
            id=str(row["id"]),
            delivery_id=str(row["delivery_id"]),
            owner_user_id=str(row["owner_user_id"]),
            route_id=str(row["route_id"]) if row["route_id"] is not None else None,
            destination_id=(
                str(row["destination_id"])
                if row["destination_id"] is not None
                else None
            ),
            source=str(row["source"]),
            title=str(row["title"]),
            severity=str(row["severity"]),
            outcome=str(row["outcome"]),
            attempt_number=int(row["attempt_number"]),
            retryable=bool(row["retryable"]),
            response_status=(
                int(row["response_status"])
                if row["response_status"] is not None
                else None
            ),
            error_code=str(row["error_code"] or ""),
            safe_error=str(row["safe_error"] or ""),
            created_at=int(row["created_at"]),
            completed_at=int(row["completed_at"]),
            input_type=str(row["input_type"] or "") if "input_type" in row.keys() else "",
            device_name=str(row["device_name"] or "") if "device_name" in row.keys() else "",
            event_name=str(row["event_name"] or "") if "event_name" in row.keys() else "",
            event_description=str(row["event_description"] or "") if "event_description" in row.keys() else "",
            event_status=str(row["event_status"] or "") if "event_status" in row.keys() else "",
        )


class PlatformDeliveryService:
    """Deliver matched reusable Routes through their bound Destinations."""

    def __init__(
        self,
        routes: RouteStore,
        destinations: DestinationStore,
        secrets: SecretStore,
        history: DeliveryHistoryStore,
        adapters: dict[str, Callable],
        *,
        relationships: RouteDestinationStore | None = None,
        maximum_attempts: int = 3,
        retry_delays: tuple[float, ...] = (0, 1, 5),
        sleeper: Callable[[float], None] = time.sleep,
        concurrency: DeliveryConcurrencyController | None = None,
    ):
        self.routes = routes
        self.destinations = destinations
        self.secrets = secrets
        self.history = history
        self.adapters = dict(adapters)
        self.relationships = relationships or RouteDestinationStore(routes.database)
        self.maximum_attempts = max(1, min(int(maximum_attempts), 5))
        self.retry_delays = tuple(max(0.0, float(value)) for value in retry_delays)
        self.sleeper = sleeper
        self.concurrency = concurrency or default_delivery_concurrency()

    def deliver(
        self,
        actor: Actor,
        notification: Notification,
    ) -> DeliverySummary:
        matching = self.routes.matching(actor, actor.user_id, notification)
        candidates = self.relationships.expand(actor, matching)
        return self._deliver_candidates(actor, notification, candidates)

    def _deliver_candidates(
        self,
        actor: Actor,
        notification: Notification,
        candidates: list[RouteDestinationCandidate],
    ) -> DeliverySummary:
        delivered = 0
        failed = 0
        attempts = 0
        jobs = []

        for candidate in candidates:
            delivery_id = uuid.uuid4().hex
            try:
                future = self.concurrency.submit(
                    candidate.destination_id,
                    self._deliver_candidate,
                    actor,
                    candidate,
                    notification,
                    delivery_id,
                )
            except Exception:
                future = None
            jobs.append((candidate, delivery_id, future))

        for candidate, delivery_id, future in jobs:
            if future is None:
                outcome, count = self._record_unexpected_delivery_failure(
                    actor,
                    candidate,
                    notification,
                    delivery_id,
                )
            else:
                try:
                    outcome, count = future.result()
                except Exception:
                    outcome, count = self._record_unexpected_delivery_failure(
                        actor,
                        candidate,
                        notification,
                        delivery_id,
                    )
            attempts += count
            if outcome:
                delivered += 1
            else:
                failed += 1

        return DeliverySummary(len(candidates), delivered, failed, attempts)

    def _record_unexpected_delivery_failure(
        self,
        actor: Actor,
        candidate: RouteDestinationCandidate,
        notification: Notification,
        delivery_id: str,
    ) -> tuple[bool, int]:
        result = DeliveryResult(
            False,
            retryable=False,
            error_code="delivery_exception",
        )
        try:
            self.history.record(
                actor.user_id,
                delivery_id,
                candidate.route,
                notification,
                1,
                "failed",
                result,
                destination_id=candidate.destination_id,
            )
        except Exception:
            pass
        return False, 1

    def _deliver_candidate(
        self,
        actor: Actor,
        candidate: RouteDestinationCandidate,
        notification: Notification,
        delivery_id: str,
    ) -> tuple[bool, int]:
        route = candidate.route
        destination_id = candidate.destination_id
        try:
            target = self.destinations.for_delivery(actor, destination_id)
        except (KeyError, PermissionError):
            result = DeliveryResult(False, error_code="destination_unavailable")
            self.history.record(
                actor.user_id,
                delivery_id,
                route,
                notification,
                1,
                "failed",
                result,
                destination_id=destination_id,
            )
            return False, 1

        secret_value = None
        if target.secret_id is not None:
            try:
                owner_actor = Actor(target.destination.owner_user_id, "user")
                secret_value = self.secrets.resolve(owner_actor, target.secret_id)
            except (KeyError, PermissionError, RuntimeError, ValueError):
                result = DeliveryResult(False, error_code="secret_unavailable")
                self.history.record(
                    actor.user_id,
                    delivery_id,
                    route,
                    notification,
                    1,
                    "failed",
                    result,
                    destination_id=destination_id,
                )
                return False, 1

        adapter = self.adapters.get(target.destination.output_type)
        if adapter is None:
            result = DeliveryResult(False, error_code="adapter_unavailable")
            self.history.record(
                actor.user_id,
                delivery_id,
                route,
                notification,
                1,
                "failed",
                result,
                destination_id=destination_id,
            )
            return False, 1

        for attempt_number in range(1, self.maximum_attempts + 1):
            if attempt_number > 1:
                delay_index = min(attempt_number - 1, len(self.retry_delays) - 1)
                delay = self.retry_delays[delay_index] if self.retry_delays else 0
                if delay:
                    self.sleeper(delay)
            result = self._invoke(adapter, target, secret_value, notification)
            retry = result.retryable and attempt_number < self.maximum_attempts
            outcome = (
                "delivered"
                if result.success
                else "retry_scheduled" if retry else "failed"
            )
            self.history.record(
                actor.user_id,
                delivery_id,
                route,
                notification,
                attempt_number,
                outcome,
                result,
                destination_id=destination_id,
            )
            if result.success:
                return True, attempt_number
            if not retry:
                return False, attempt_number
        return False, self.maximum_attempts

    @staticmethod
    def _invoke(adapter, target, secret_value, notification) -> DeliveryResult:
        try:
            result = adapter(target.destination, secret_value, notification)
        except Exception:
            return DeliveryResult(False, retryable=False, error_code="delivery_exception")
        if isinstance(result, DeliveryResult):
            return result
        if isinstance(result, bool):
            return DeliveryResult(result, retryable=False)
        return DeliveryResult(False, retryable=False, error_code="invalid_adapter_result")
