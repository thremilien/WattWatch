"""`/api/state` (protected, polled every 2s by the UI) and `/api/health`
(unauthenticated, used as the container healthcheck).

`/api/state` always serves the `DeviceService` cache — it never calls the
device inline, so a slow/dead plug can never hang this request.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from wattwatch.auth.dependencies import require_user
from wattwatch.config import settings
from wattwatch.devices.service import DeviceService
from wattwatch.schemas import StateOut

state_router = APIRouter(prefix="/api", tags=["state"], dependencies=[Depends(require_user)])
health_router = APIRouter(prefix="/api", tags=["health"])

_STALE_MULTIPLIER = 3


def _is_stale(captured_at: datetime | None) -> bool:
    if captured_at is None:
        return True
    age = (datetime.now(UTC) - captured_at.astimezone(UTC)).total_seconds()
    return age > _STALE_MULTIPLIER * settings.poll_interval_seconds


@state_router.get("/state", response_model=StateOut)
async def get_state(request: Request) -> StateOut:
    service: DeviceService = request.app.state.device_service
    state = service.state
    stale = not state.reachable or _is_stale(state.captured_at)
    return StateOut.from_state(state, stale=stale)


@health_router.get("/health")
async def health(request: Request) -> dict:
    service: DeviceService = request.app.state.device_service
    return {"status": "ok", "device_reachable": service.state.reachable}
