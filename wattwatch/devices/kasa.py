"""`PlugDriver` implementation against the real TP-Link Kasa HS110 via python-kasa.

Connects with `kasa.iot.IotPlug`, which talks TCP 9999 directly (no UDP
discovery), works from inside a Docker bridge network, and is the fastest of
the available connection strategies (~0.14s per `update()` against the real
device). The `IotPlug` instance is constructed once and reused; callers must
call `refresh()` before reading info/live data.

CRITICAL: `Emeter` subclasses `Usage`, and the inherited `usage_this_month` /
`usage_today` properties raise `KeyError: 'time'` on this device's firmware.
Do not blanket-iterate module attributes or use `getattr` loops over the
Energy module — only the explicit accessors below are touched.
"""

from datetime import datetime

from kasa.iot import IotPlug

from wattwatch.devices.base import DeviceInfo, LiveReading


class KasaPlugDriver:
    """Talks to a single HS110 over the LAN. Not concurrency-safe on its own —
    callers (namely `DeviceService`) must serialise access with a lock."""

    def __init__(self, host: str) -> None:
        self._host = host
        self._device = IotPlug(host)

    async def refresh(self) -> None:
        await self._device.update()

    async def get_info(self) -> DeviceInfo:
        dev = self._device
        on_since: datetime | None = dev.on_since
        uptime_seconds: int | None = None
        if on_since is not None:
            now = datetime.now(on_since.tzinfo)
            uptime_seconds = max(0, int((now - on_since).total_seconds()))
        return DeviceInfo(
            alias=dev.alias,
            model=dev.model,
            mac=dev.mac,
            hw_version=dev.hw_info["hw_ver"],
            fw_version=dev.hw_info["sw_ver"],
            device_type=dev.device_type.value,
            host=self._host,
            rssi=dev.rssi,
            is_on=dev.is_on,
            led_on=dev.modules["Led"].led,
            on_since=on_since,
            uptime_seconds=uptime_seconds,
        )

    async def get_live(self) -> LiveReading:
        energy = self._device.modules["Energy"]
        return LiveReading(
            timestamp=datetime.now().astimezone(),
            power_w=energy.current_consumption,
            voltage_v=energy.voltage,
            current_a=energy.current,
            today_kwh=energy.consumption_today,
            month_kwh=energy.consumption_this_month,
            total_kwh=energy.consumption_total,
        )

    async def set_power(self, on: bool) -> None:
        if on:
            await self._device.turn_on()
        else:
            await self._device.turn_off()

    async def set_led(self, on: bool) -> None:
        await self._device.modules["Led"].set_led(on)

    async def set_alias(self, alias: str) -> None:
        await self._device.set_alias(alias)

    async def reboot(self) -> None:
        await self._device.reboot()

    async def daily_stats(self, year: int, month: int) -> dict[int, float]:
        energy = self._device.modules["Energy"]
        return await energy.get_daily_stats(year=year, month=month, kwh=True)

    async def monthly_stats(self, year: int) -> dict[int, float]:
        energy = self._device.modules["Energy"]
        return await energy.get_monthly_stats(year=year, kwh=True)

    async def erase_stats(self) -> None:
        energy = self._device.modules["Energy"]
        await energy.erase_stats()
