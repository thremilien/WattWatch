"""`DeviceService`: the single owner of the plug driver and its cached state.

Holds one `PlugDriver` instance, an `asyncio.Lock` that serialises *all*
device I/O (python-kasa is not documented as concurrency-safe), and the
last-known-good `DeviceInfo` + `LiveReading` along with the timestamp they
were captured and whether the device is currently reachable.

Reads of `/api/state` must serve this cache directly and never call the
device inline, so a slow or dead plug can never hang an HTTP request. Only
the poller and write endpoints (which explicitly want a fresh read-after-write)
talk to the driver.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from wattwatch.devices.base import DeviceInfo, LiveReading, PlugDriver


@dataclass(slots=True)
class DeviceState:
    """The cached, last-known-good snapshot of the device plus health info."""

    reachable: bool
    error: str | None
    info: DeviceInfo | None
    live: LiveReading | None
    captured_at: datetime | None


class DeviceService:
    """Owns the driver instance and the cache. Thread-unsafe, asyncio-safe."""

    def __init__(self, driver: PlugDriver) -> None:
        self._driver = driver
        self._lock = asyncio.Lock()
        self._state = DeviceState(
            reachable=False, error=None, info=None, live=None, captured_at=None
        )

    @property
    def state(self) -> DeviceState:
        """The current cached state. Safe to call without awaiting/locking."""
        return self._state

    async def refresh_cache(self) -> DeviceState:
        """Refresh the driver and update the cache. Used by the poller."""
        async with self._lock:
            await self._refresh_locked()
        return self._state

    async def _refresh_locked(self) -> None:
        try:
            await self._driver.refresh()
            info = await self._driver.get_info()
            live = await self._driver.get_live()
        except Exception as exc:
            self._state = DeviceState(
                reachable=False,
                error=str(exc) or exc.__class__.__name__,
                info=self._state.info,
                live=self._state.live,
                captured_at=self._state.captured_at,
            )
            raise
        else:
            self._state = DeviceState(
                reachable=True,
                error=None,
                info=info,
                live=live,
                captured_at=datetime.now().astimezone(),
            )

    async def act(self, fn: Callable[[PlugDriver], Awaitable[None]]) -> DeviceState:
        """Run a mutating driver call under the lock, then refresh the cache.

        `fn` receives the driver and should call exactly one mutating method
        on it, e.g. `lambda d: d.set_power(True)`. Raises on failure (callers
        map this to a 502); the cache is refreshed on both success and
        failure so the reachability flag stays accurate.
        """
        async with self._lock:
            try:
                await fn(self._driver)
            finally:
                with contextlib.suppress(Exception):
                    await self._refresh_locked()
        return self._state

    async def reboot(self) -> None:
        """Trigger a reboot. Does not wait for the device to come back; the
        poller will observe it dropping off the network and recover."""
        async with self._lock:
            await self._driver.reboot()

    async def daily_stats(self, year: int, month: int) -> dict[int, float]:
        async with self._lock:
            return await self._driver.daily_stats(year, month)

    async def monthly_stats(self, year: int) -> dict[int, float]:
        async with self._lock:
            return await self._driver.monthly_stats(year)

    async def erase_stats(self) -> None:
        async with self._lock:
            await self._driver.erase_stats()
