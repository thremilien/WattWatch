"""`/api/device/*` — power, LED, alias, reboot.

All mutating endpoints take the `DeviceService` lock, act, then re-read the
device and return the fresh `device` object (except `/reboot`, which returns
a status marker since the device is expected to be briefly unreachable
afterwards). Device communication failures on these write paths are surfaced
as `502`, never a bare 5xx traceback.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from wattwatch.auth.dependencies import require_user
from wattwatch.devices.base import PlugDriver
from wattwatch.devices.service import DeviceService
from wattwatch.schemas import DeviceOut

router = APIRouter(prefix="/api/device", tags=["device"], dependencies=[Depends(require_user)])


class PowerRequest(BaseModel):
    on: bool


class LedRequest(BaseModel):
    on: bool


class AliasRequest(BaseModel):
    alias: str

    @field_validator("alias")
    @classmethod
    def _validate_alias(cls, value: str) -> str:
        stripped = value.strip()
        if not (1 <= len(stripped) <= 31):
            raise ValueError("alias must be 1-31 characters after stripping whitespace")
        return stripped


class SyncTimeRequest(BaseModel):
    """The caller's own local wall-clock fields — never a UTC instant.

    The device has no way to know the caller's timezone, and its own
    configured timezone may itself be wrong (that's usually why this
    endpoint gets called), so the only thing that's actually trustworthy
    here is "what time does the caller's clock read right now".
    """

    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    second: int = Field(ge=0, le=59)


def _get_service(request: Request) -> DeviceService:
    return request.app.state.device_service


async def _act_or_502(service: DeviceService, fn) -> DeviceOut:
    try:
        state = await service.act(fn)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc) or exc.__class__.__name__
        ) from exc
    if state.info is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Device unreachable after action"
        )
    return DeviceOut.from_info(state.info)


@router.post("/power", response_model=DeviceOut)
async def set_power(payload: PowerRequest, request: Request) -> DeviceOut:
    service = _get_service(request)

    async def _fn(driver: PlugDriver) -> None:
        await driver.set_power(payload.on)

    return await _act_or_502(service, _fn)


@router.post("/led", response_model=DeviceOut)
async def set_led(payload: LedRequest, request: Request) -> DeviceOut:
    service = _get_service(request)

    async def _fn(driver: PlugDriver) -> None:
        await driver.set_led(payload.on)

    return await _act_or_502(service, _fn)


@router.post("/alias", response_model=DeviceOut)
async def set_alias(payload: AliasRequest, request: Request) -> DeviceOut:
    service = _get_service(request)

    async def _fn(driver: PlugDriver) -> None:
        await driver.set_alias(payload.alias)

    return await _act_or_502(service, _fn)


@router.post("/sync-time", response_model=DeviceOut)
async def sync_time(payload: SyncTimeRequest, request: Request) -> DeviceOut:
    try:
        dt = datetime(
            payload.year, payload.month, payload.day, payload.hour, payload.minute, payload.second
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    service = _get_service(request)

    async def _fn(driver: PlugDriver) -> None:
        await driver.sync_time(dt)

    return await _act_or_502(service, _fn)


@router.post("/reboot", status_code=status.HTTP_202_ACCEPTED)
async def reboot(request: Request) -> dict:
    service = _get_service(request)
    try:
        await service.reboot()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc) or exc.__class__.__name__
        ) from exc
    return {"status": "rebooting"}
