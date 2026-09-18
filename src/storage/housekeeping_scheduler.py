"""Daily scheduler for operational-history housekeeping."""

from __future__ import annotations

import threading
import time

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from storage.housekeeping import HousekeepingService
from storage.settings import DEFAULT_REGIONAL_SETTINGS


class HousekeepingScheduler:
    def __init__(self, database, configuration, *, clock=time.time, interval=60):
        self.database = database
        self.configuration = configuration
        self.clock = clock
        self.interval = max(30, int(interval))
        self.service = HousekeepingService(database, clock=clock)
        self._stop = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="nowlert-housekeeping",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None

    def run_due(self, now: float | None = None):
        reload_configuration = getattr(self.configuration, "reload", None)
        if callable(reload_configuration):
            try:
                reload_configuration()
            except Exception:
                return None
        settings = self.service.settings()
        if settings.get("enabled") is not True:
            return None
        regional, _error = self.service.settings_store.get_safe(
            "platform", "regional", DEFAULT_REGIONAL_SETTINGS
        )
        try:
            zone = ZoneInfo(str(regional.get("timezone") or "Europe/Lisbon"))
        except (ValueError, ZoneInfoNotFoundError):
            zone = ZoneInfo("UTC")
        timestamp = self.clock() if now is None else now
        current = datetime.fromtimestamp(timestamp, zone)
        hour, minute = (
            int(part) for part in str(settings.get("time") or "03:15").split(":")
        )
        if (current.hour, current.minute) < (hour, minute):
            return None
        return self.service.run(period_key=f"daily:{current:%Y-%m-%d}")

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.run_due()
            except Exception:
                # The next scheduler tick retries on a future date/manual run.
                pass
