"""Bounded, fair process-wide delivery concurrency scheduling."""

from __future__ import annotations

import threading

from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable


DEFAULT_GLOBAL_DELIVERY_LIMIT = 40
DEFAULT_PER_DESTINATION_LIMIT = 8
DEFAULT_MAXIMUM_PENDING = 4096


@dataclass(frozen=True)
class DeliveryConcurrencySnapshot:
    active: int
    pending: int
    max_active: int
    max_active_per_destination: int
    active_by_destination: dict[str, int]
    pending_by_destination: dict[str, int]


@dataclass
class _DeliveryJob:
    future: Future
    function: Callable
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class DeliveryConcurrencyController:
    """Schedule delivery jobs fairly without letting one destination starve peers."""

    def __init__(
        self,
        *,
        global_limit: int = DEFAULT_GLOBAL_DELIVERY_LIMIT,
        per_destination_limit: int = DEFAULT_PER_DESTINATION_LIMIT,
        maximum_pending: int = DEFAULT_MAXIMUM_PENDING,
    ):
        self.global_limit = max(1, int(global_limit))
        self.per_destination_limit = max(1, int(per_destination_limit))
        self.maximum_pending = max(self.global_limit, int(maximum_pending))
        self._executor = ThreadPoolExecutor(
            max_workers=self.global_limit,
            thread_name_prefix="nowlert-delivery",
        )
        self._condition = threading.Condition(threading.RLock())
        self._queues: dict[str, deque[_DeliveryJob]] = {}
        self._ready: deque[str] = deque()
        self._ready_set: set[str] = set()
        self._active_by_destination: dict[str, int] = {}
        self._active_total = 0
        self._pending_total = 0
        self._max_active = 0
        self._max_active_per_destination = 0
        self._closed = False

    def submit(
        self,
        destination_id: str,
        function: Callable,
        *args,
        **kwargs,
    ) -> Future:
        destination_id = str(destination_id or "").strip()
        if not destination_id:
            raise ValueError("delivery destination id is required")
        future = Future()
        job = _DeliveryJob(future, function, tuple(args), dict(kwargs))
        with self._condition:
            while not self._closed and self._pending_total >= self.maximum_pending:
                self._condition.wait()
            if self._closed:
                raise RuntimeError("delivery concurrency controller is closed")
            queue = self._queues.setdefault(destination_id, deque())
            queue.append(job)
            self._pending_total += 1
            self._mark_ready_locked(destination_id)
            self._schedule_locked()
        return future

    def snapshot(self) -> DeliveryConcurrencySnapshot:
        with self._condition:
            return DeliveryConcurrencySnapshot(
                active=self._active_total,
                pending=self._pending_total,
                max_active=self._max_active,
                max_active_per_destination=self._max_active_per_destination,
                active_by_destination=dict(self._active_by_destination),
                pending_by_destination={
                    destination_id: len(queue)
                    for destination_id, queue in self._queues.items()
                    if queue
                },
            )

    def shutdown(self, wait: bool = True) -> None:
        with self._condition:
            self._closed = True
            if wait:
                while self._pending_total or self._active_total:
                    self._condition.wait()
            else:
                error = RuntimeError("delivery concurrency controller is closed")
                for queue in self._queues.values():
                    while queue:
                        job = queue.popleft()
                        self._pending_total -= 1
                        if not job.future.done():
                            job.future.set_exception(error)
                self._queues.clear()
                self._ready.clear()
                self._ready_set.clear()
                self._condition.notify_all()
        self._executor.shutdown(wait=wait, cancel_futures=not wait)

    def _mark_ready_locked(self, destination_id: str) -> None:
        queue = self._queues.get(destination_id)
        active = self._active_by_destination.get(destination_id, 0)
        if (
            queue
            and active < self.per_destination_limit
            and destination_id not in self._ready_set
        ):
            self._ready.append(destination_id)
            self._ready_set.add(destination_id)

    def _schedule_locked(self) -> None:
        while self._active_total < self.global_limit and self._ready:
            scheduled = False
            scans = len(self._ready)
            for _ in range(scans):
                destination_id = self._ready.popleft()
                self._ready_set.discard(destination_id)
                queue = self._queues.get(destination_id)
                if not queue:
                    self._queues.pop(destination_id, None)
                    continue
                active = self._active_by_destination.get(destination_id, 0)
                if active >= self.per_destination_limit:
                    continue

                job = queue.popleft()
                self._pending_total -= 1
                if not queue:
                    self._queues.pop(destination_id, None)

                active += 1
                self._active_by_destination[destination_id] = active
                self._active_total += 1
                self._max_active = max(self._max_active, self._active_total)
                self._max_active_per_destination = max(
                    self._max_active_per_destination,
                    active,
                )

                if self._queues.get(destination_id):
                    self._mark_ready_locked(destination_id)

                try:
                    self._executor.submit(
                        self._run_job,
                        destination_id,
                        job,
                    )
                except RuntimeError as error:
                    self._active_total -= 1
                    next_active = self._active_by_destination[destination_id] - 1
                    if next_active:
                        self._active_by_destination[destination_id] = next_active
                    else:
                        self._active_by_destination.pop(destination_id, None)
                    if not job.future.done():
                        job.future.set_exception(error)
                self._condition.notify_all()
                scheduled = True
                break
            if not scheduled:
                break

    def _run_job(
        self,
        destination_id: str,
        job: _DeliveryJob,
    ) -> None:
        if not job.future.set_running_or_notify_cancel():
            self._finish_job(destination_id)
            return
        result = None
        error = None
        try:
            result = job.function(*job.args, **job.kwargs)
        except BaseException as caught:
            error = caught
        finally:
            self._finish_job(destination_id)

        if error is None:
            job.future.set_result(result)
        else:
            job.future.set_exception(error)

    def _finish_job(self, destination_id: str) -> None:
        with self._condition:
            self._active_total = max(0, self._active_total - 1)
            active = self._active_by_destination.get(destination_id, 0) - 1
            if active > 0:
                self._active_by_destination[destination_id] = active
            else:
                self._active_by_destination.pop(destination_id, None)
            self._mark_ready_locked(destination_id)
            self._schedule_locked()
            self._condition.notify_all()


_DEFAULT_CONTROLLER: DeliveryConcurrencyController | None = None
_DEFAULT_CONTROLLER_LOCK = threading.Lock()


def default_delivery_concurrency() -> DeliveryConcurrencyController:
    global _DEFAULT_CONTROLLER
    with _DEFAULT_CONTROLLER_LOCK:
        if _DEFAULT_CONTROLLER is None or _DEFAULT_CONTROLLER._closed:
            _DEFAULT_CONTROLLER = DeliveryConcurrencyController()
        return _DEFAULT_CONTROLLER


__all__ = [
    "DEFAULT_GLOBAL_DELIVERY_LIMIT",
    "DEFAULT_MAXIMUM_PENDING",
    "DEFAULT_PER_DESTINATION_LIMIT",
    "DeliveryConcurrencyController",
    "DeliveryConcurrencySnapshot",
    "default_delivery_concurrency",
]
