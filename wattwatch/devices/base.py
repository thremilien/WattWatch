"""The `PlugDriver` seam: everything the rest of the app needs from a smart plug.

`KasaPlugDriver` implements this against python-kasa and the real HS110. Tests
implement a `FakePlugDriver` against the same protocol so device control and
degradation paths (including destructive ones like power-off/reboot/erase-stats)
can be exercised without touching real hardware.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class DeviceInfo:
    """Static-ish device identity and current on/off state."""

    alias: str
    model: str
    mac: str
    hw_version: str
    fw_version: str
    device_type: str
    host: str
    rssi: int | None
    is_on: bool
    led_on: bool
    on_since: datetime | None
    uptime_seconds: int | None


@dataclass(slots=True)
class LiveReading:
    """A snapshot of instantaneous power/energy readings."""

    timestamp: datetime
    power_w: float | None
    voltage_v: float | None
    current_a: float | None
    today_kwh: float | None
    month_kwh: float | None
    total_kwh: float | None


@runtime_checkable
class PlugDriver(Protocol):
    """Async protocol for a single smart plug. Implementations must serialize
    their own I/O internally only if they are shared across callers without an
    external lock; `DeviceService` is responsible for serialising calls here."""

    async def refresh(self) -> None:
        """Refresh cached device state (calls the equivalent of `update()`)."""
        ...

    async def get_info(self) -> DeviceInfo:
        """Return device identity/on-off info as of the last `refresh()`."""
        ...

    async def get_live(self) -> LiveReading:
        """Return live power/energy readings as of the last `refresh()`."""
        ...

    async def set_power(self, on: bool) -> None:
        """Turn the plug relay on or off."""
        ...

    async def set_led(self, on: bool) -> None:
        """Turn the status LED on or off."""
        ...

    async def set_alias(self, alias: str) -> None:
        """Rename the device."""
        ...

    async def reboot(self) -> None:
        """Reboot the device. It will drop off the network briefly."""
        ...

    async def daily_stats(self, year: int, month: int) -> dict[int, float]:
        """Return day-of-month -> kWh for the given year/month."""
        ...

    async def monthly_stats(self, year: int) -> dict[int, float]:
        """Return month -> kWh for the given year. May be returned unordered."""
        ...

    async def erase_stats(self) -> None:
        """Erase the device's on-board accumulated emeter statistics."""
        ...
