"""`/api/energy/*` — device-reported daily/monthly stats and stats reset.

The device returns monthly stats **out of order**; this layer sorts
ascending before responding. Day/month default to the current device-local
date when omitted.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from wattwatch.auth.dependencies import require_user
from wattwatch.devices.service import DeviceService

router = APIRouter(prefix="/api/energy", tags=["energy"], dependencies=[Depends(require_user)])


class DailyEntry(BaseModel):
    day: int
    kwh: float


class DailyOut(BaseModel):
    year: int
    month: int
    unit: str = "kWh"
    entries: list[DailyEntry]


class MonthlyEntry(BaseModel):
    month: int
    kwh: float


class MonthlyOut(BaseModel):
    year: int
    unit: str = "kWh"
    entries: list[MonthlyEntry]


def _get_service(request: Request) -> DeviceService:
    return request.app.state.device_service


async def _fetch_or_502(coro):
    try:
        return await coro
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc) or exc.__class__.__name__
        ) from exc


@router.get("/daily", response_model=DailyOut)
async def get_daily(
    request: Request, year: int | None = None, month: int | None = None
) -> DailyOut:
    now = datetime.now().astimezone()
    year = year if year is not None else now.year
    month = month if month is not None else now.month

    service = _get_service(request)
    stats = await _fetch_or_502(service.daily_stats(year, month))
    entries = [DailyEntry(day=day, kwh=kwh) for day, kwh in sorted(stats.items())]
    return DailyOut(year=year, month=month, entries=entries)


@router.get("/monthly", response_model=MonthlyOut)
async def get_monthly(request: Request, year: int | None = None) -> MonthlyOut:
    now = datetime.now().astimezone()
    year = year if year is not None else now.year

    service = _get_service(request)
    stats = await _fetch_or_502(service.monthly_stats(year))
    entries = [MonthlyEntry(month=month, kwh=kwh) for month, kwh in sorted(stats.items())]
    return MonthlyOut(year=year, entries=entries)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_stats(request: Request) -> None:
    service = _get_service(request)
    await _fetch_or_502(service.erase_stats())
