"""Shared Pydantic response models for `/api/state` and `/api/device/*`.

Kept separate from the routers because both `routers/state.py` and
`routers/device.py` return the same `device`/`live`/state shapes.
"""

from datetime import datetime

from pydantic import BaseModel

from wattwatch.devices.base import DeviceInfo, LiveReading
from wattwatch.devices.service import DeviceState


class DeviceOut(BaseModel):
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
    device_time: datetime | None

    @classmethod
    def from_info(cls, info: DeviceInfo) -> "DeviceOut":
        return cls(
            alias=info.alias,
            model=info.model,
            mac=info.mac,
            hw_version=info.hw_version,
            fw_version=info.fw_version,
            device_type=info.device_type,
            host=info.host,
            rssi=info.rssi,
            is_on=info.is_on,
            led_on=info.led_on,
            on_since=info.on_since,
            uptime_seconds=info.uptime_seconds,
            device_time=info.device_time,
        )


class LiveOut(BaseModel):
    timestamp: datetime
    power_w: float | None
    voltage_v: float | None
    current_a: float | None
    today_kwh: float | None
    month_kwh: float | None
    total_kwh: float | None

    @classmethod
    def from_reading(cls, live: LiveReading) -> "LiveOut":
        return cls(
            timestamp=live.timestamp,
            power_w=live.power_w,
            voltage_v=live.voltage_v,
            current_a=live.current_a,
            today_kwh=live.today_kwh,
            month_kwh=live.month_kwh,
            total_kwh=live.total_kwh,
        )


class StateOut(BaseModel):
    reachable: bool
    error: str | None
    stale: bool
    device: DeviceOut | None
    live: LiveOut | None

    @classmethod
    def from_state(cls, state: DeviceState, *, stale: bool) -> "StateOut":
        return cls(
            reachable=state.reachable,
            error=state.error,
            stale=stale,
            device=DeviceOut.from_info(state.info) if state.info is not None else None,
            live=LiveOut.from_reading(state.live) if state.live is not None else None,
        )
