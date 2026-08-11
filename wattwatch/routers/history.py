"""`/api/history` and `/api/history/summary` — local SQLite-backed history.

Finer-grained than the device's own daily/monthly stats. `ts` is stored as
unix epoch seconds (UTC) and converted to ISO-8601 with timezone only here,
at the API boundary.
"""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from wattwatch import history
from wattwatch.auth.dependencies import require_user

router = APIRouter(prefix="/api/history", tags=["history"], dependencies=[Depends(require_user)])


def _ts_to_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).astimezone().isoformat()


@router.get("")
async def get_history(hours: int = Query(default=6, ge=1, le=720)) -> dict:
    now = int(time.time())
    start_ts = now - hours * 3600
    points = await history.get_history(start_ts, now)
    return {
        "hours": hours,
        "count": len(points),
        "points": [
            {
                "ts": _ts_to_iso(p.ts),
                "power_w": p.power_w,
                "voltage_v": p.voltage_v,
                "current_a": p.current_a,
            }
            for p in points
        ],
    }


@router.get("/summary")
async def get_summary(hours: int = Query(default=24, ge=1, le=720)) -> dict:
    now = int(time.time())
    start_ts = now - hours * 3600
    summary = await history.get_summary(start_ts, now)
    return {
        "hours": hours,
        "avg_power_w": summary.avg_power_w,
        "min_power_w": summary.min_power_w,
        "max_power_w": summary.max_power_w,
        "energy_kwh": summary.energy_kwh,
        "count": summary.count,
    }
