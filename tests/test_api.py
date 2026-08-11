"""Focused end-to-end coverage of the WattWatch API contract."""

import time
from datetime import datetime

import httpx
import pytest

from wattwatch import db
from wattwatch.poller import _insert_reading as insert_reading

from .fakes import FakePlugDriver


async def test_state_requires_auth_but_health_does_not(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/state")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_login_logout_flow(client: httpx.AsyncClient) -> None:
    bad = await client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad.status_code == 401
    assert bad.json() == {"detail": "Invalid username or password"}

    good = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    assert good.status_code == 200
    assert good.json() == {"username": "admin"}
    assert "ww_session" in good.cookies

    state = await client.get("/api/state")
    assert state.status_code == 200

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204

    after_logout = await client.get("/api/state")
    assert after_logout.status_code == 401


async def test_state_degrades_gracefully_on_driver_error(
    app, authed_client: httpx.AsyncClient, fake_driver: FakePlugDriver
) -> None:
    # Let the poller populate a good cache first.
    good = await authed_client.get("/api/state")
    assert good.status_code == 200
    assert good.json()["reachable"] is True
    last_alias = good.json()["device"]["alias"]

    fake_driver.fail = True

    # Force a refresh through the same service the app uses.
    service = app.state.device_service
    with pytest.raises(ConnectionError):
        await service.refresh_cache()

    degraded = await authed_client.get("/api/state")
    assert degraded.status_code == 200
    body = degraded.json()
    assert body["reachable"] is False
    assert body["stale"] is True
    assert body["error"]
    assert body["device"]["alias"] == last_alias


async def test_power_control_reaches_driver(
    authed_client: httpx.AsyncClient, fake_driver: FakePlugDriver
) -> None:
    response = await authed_client.post("/api/device/power", json={"on": False})
    assert response.status_code == 200
    assert fake_driver.set_power_calls == [False]
    assert response.json()["is_on"] is False


async def test_sync_time_sends_naive_local_datetime_to_driver(
    authed_client: httpx.AsyncClient, fake_driver: FakePlugDriver
) -> None:
    payload = {"year": 2026, "month": 8, "day": 12, "hour": 0, "minute": 18, "second": 30}
    response = await authed_client.post("/api/device/sync-time", json=payload)
    assert response.status_code == 200
    assert fake_driver.sync_time_calls == [datetime(2026, 8, 12, 0, 18, 30)]


async def test_sync_time_rejects_an_impossible_date(authed_client: httpx.AsyncClient) -> None:
    payload = {"year": 2026, "month": 2, "day": 30, "hour": 0, "minute": 0, "second": 0}
    response = await authed_client.post("/api/device/sync-time", json=payload)
    assert response.status_code == 422


async def test_energy_monthly_sorted_ascending(authed_client: httpx.AsyncClient) -> None:
    response = await authed_client.get("/api/energy/monthly", params={"year": 2026})
    assert response.status_code == 200
    body = response.json()
    months = [entry["month"] for entry in body["entries"]]
    assert months == sorted(months)
    assert months == [1, 2, 3]


async def test_history_downsamples_to_at_most_720_points(
    authed_client: httpx.AsyncClient,
) -> None:
    now = int(time.time())
    conn = db.get_connection()
    for i in range(1000):
        insert_reading(conn, now - i * 5, 100.0 + i, 230.0, 0.43)

    response = await authed_client.get("/api/history", params={"hours": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] <= 720
    timestamps = [p["ts"] for p in body["points"]]
    assert timestamps == sorted(timestamps)


async def test_unknown_api_path_is_json_404(authed_client: httpx.AsyncClient) -> None:
    response = await authed_client.get("/api/nope")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not found"}
