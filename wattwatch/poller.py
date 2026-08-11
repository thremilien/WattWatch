"""Background polling task: refreshes the device cache and persists history.

Runs as an asyncio task started in the app lifespan. Every
`POLL_INTERVAL_SECONDS` it refreshes `DeviceService`'s cache; every
`HISTORY_INTERVAL_SECONDS` (only while reachable) it also persists a row to
the `readings` table; roughly once an hour it prunes rows older than
`HISTORY_RETENTION_DAYS` (0 disables pruning).

On device error: log a warning on the *first* failure only, then stay quiet
until the state changes (avoids log spam from a plug that's down for hours).
The last-known-good cache is kept, `reachable` is set to False, and the poll
interval backs off progressively up to ~60s. Polling never blocks app
startup and never raises out of the task loop.
"""

import asyncio
import contextlib
import logging
import sqlite3
import time

from wattwatch import db
from wattwatch.config import settings
from wattwatch.devices.service import DeviceService, DeviceState

logger = logging.getLogger("wattwatch.poller")

_MAX_BACKOFF_SECONDS = 60
_PRUNE_INTERVAL_SECONDS = 3600


def _insert_reading(
    conn: sqlite3.Connection,
    ts: int,
    power_w: float | None,
    voltage_v: float | None,
    current_a: float | None,
) -> None:
    conn.execute(
        "INSERT INTO readings (ts, power_w, voltage_v, current_a) VALUES (?, ?, ?, ?)",
        (ts, power_w, voltage_v, current_a),
    )
    conn.commit()


def _prune_readings(conn: sqlite3.Connection, cutoff_ts: int) -> None:
    conn.execute("DELETE FROM readings WHERE ts < ?", (cutoff_ts,))
    conn.commit()


class Poller:
    """Owns the background polling loop and its lifecycle."""

    def __init__(self, service: DeviceService) -> None:
        self._service = service
        self._task: asyncio.Task | None = None
        self._last_history_write = 0.0
        self._last_prune = 0.0
        self._was_reachable: bool | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="wattwatch-poller")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        backoff = settings.poll_interval_seconds
        while True:
            state = None
            try:
                state = await self._service.refresh_cache()
            except Exception as exc:
                self._on_failure(exc)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
            else:
                self._on_success()
                backoff = settings.poll_interval_seconds
                await self._maybe_persist(state)

            await self._maybe_prune()
            await asyncio.sleep(backoff)

    def _on_failure(self, exc: Exception) -> None:
        if self._was_reachable is not False:
            logger.warning("Device unreachable: %s", exc)
        self._was_reachable = False

    def _on_success(self) -> None:
        if self._was_reachable is False:
            logger.info("Device reachable again")
        self._was_reachable = True

    async def _maybe_persist(self, state: DeviceState) -> None:
        if not state.reachable or state.live is None:
            return
        now = time.monotonic()
        if now - self._last_history_write < settings.history_interval_seconds:
            return
        self._last_history_write = now
        live = state.live
        ts = int(live.timestamp.timestamp())
        await db.run(_insert_reading, ts, live.power_w, live.voltage_v, live.current_a)

    async def _maybe_prune(self) -> None:
        if settings.history_retention_days <= 0:
            return
        now = time.monotonic()
        if self._last_prune and now - self._last_prune < _PRUNE_INTERVAL_SECONDS:
            return
        self._last_prune = now
        cutoff_ts = int(time.time()) - settings.history_retention_days * 86400
        await db.run(_prune_readings, cutoff_ts)
