"""`FakePlugDriver`: an in-memory `PlugDriver` implementation for tests.

Lets tests exercise device control and degradation paths (including
destructive ones like power-off/reboot/erase-stats) without ever touching
real hardware.
"""

from datetime import datetime

from wattwatch.devices.base import DeviceInfo, LiveReading


class FakePlugDriver:
    """In-memory stand-in for `KasaPlugDriver`, matching the `PlugDriver` protocol."""

    def __init__(
        self,
        *,
        alias: str = "Fake Plug",
        is_on: bool = True,
        fail: bool = False,
    ) -> None:
        self.alias = alias
        self.is_on = is_on
        self.led_on = True
        self.fail = fail
        self.power_w = 100.0
        self.voltage_v = 230.0
        self.current_a = 0.43
        self.today_kwh = 1.5
        self.month_kwh = 20.0
        self.total_kwh = 500.0
        self.daily = {1: 4.5, 2: 4.6}
        self.monthly = {3: 30.0, 1: 10.0, 2: 20.0}  # deliberately unordered
        self.erase_stats_called = False
        self.reboot_called = False
        self.set_power_calls: list[bool] = []

    async def refresh(self) -> None:
        if self.fail:
            raise ConnectionError("simulated device unreachable")

    async def get_info(self) -> DeviceInfo:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        return DeviceInfo(
            alias=self.alias,
            model="HS110",
            mac="74:DA:88:D4:C3:22",
            hw_version="2.0",
            fw_version="1.5.5 Build 191125 Rel.114303",
            device_type="plug",
            host="192.168.10.8",
            rssi=-42,
            is_on=self.is_on,
            led_on=self.led_on,
            on_since=datetime.now().astimezone(),
            uptime_seconds=12345,
        )

    async def get_live(self) -> LiveReading:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        return LiveReading(
            timestamp=datetime.now().astimezone(),
            power_w=self.power_w,
            voltage_v=self.voltage_v,
            current_a=self.current_a,
            today_kwh=self.today_kwh,
            month_kwh=self.month_kwh,
            total_kwh=self.total_kwh,
        )

    async def set_power(self, on: bool) -> None:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        self.is_on = on
        self.set_power_calls.append(on)

    async def set_led(self, on: bool) -> None:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        self.led_on = on

    async def set_alias(self, alias: str) -> None:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        self.alias = alias

    async def reboot(self) -> None:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        self.reboot_called = True

    async def daily_stats(self, year: int, month: int) -> dict[int, float]:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        return dict(self.daily)

    async def monthly_stats(self, year: int) -> dict[int, float]:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        return dict(self.monthly)

    async def erase_stats(self) -> None:
        if self.fail:
            raise ConnectionError("simulated device unreachable")
        self.erase_stats_called = True
