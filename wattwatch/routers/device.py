"""`/api/device/*` — power, LED, alias, reboot.

All mutating endpoints take the `DeviceService` lock, act, then re-read the
device and return the fresh `device` object (except `/reboot`, which returns
a status marker since the device is expected to be briefly unreachable
afterwards). Device communication failures on these write paths are surfaced
as `502`, never a bare 5xx traceback.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

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
