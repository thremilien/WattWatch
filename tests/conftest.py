"""Shared pytest fixtures: an isolated app/client wired to a `FakePlugDriver`
and a temp-file SQLite DB, plus dependency overrides for auth.
"""

import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

# Settings are validated at import time (module-level `settings = Settings()`),
# so ADMIN_PASSWORD must be present in the environment before wattwatch.config
# (or anything importing it) is ever imported.
os.environ.setdefault("ADMIN_PASSWORD", "correct-horse-battery-staple")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("KASA_HOST", "192.0.2.1")

import httpx
import pytest
from fastapi import FastAPI

from wattwatch import db
from wattwatch.auth.password import PasswordAuthProvider, seed_admin_user
from wattwatch.auth.sessions import SessionStore
from wattwatch.config import settings
from wattwatch.devices.service import DeviceService
from wattwatch.main import create_app
from wattwatch.poller import Poller

from .fakes import FakePlugDriver


@pytest.fixture
def fake_driver() -> FakePlugDriver:
    return FakePlugDriver()


@pytest.fixture
async def app(tmp_path, fake_driver: FakePlugDriver) -> AsyncIterator[FastAPI]:
    settings.database_path = tmp_path / f"wattwatch-test-{uuid.uuid4().hex}.db"
    settings.admin_username = "admin"
    settings.admin_password = "correct-horse-battery-staple"

    application = create_app()

    @asynccontextmanager
    async def test_lifespan(app: FastAPI) -> AsyncIterator[None]:
        await db.init_db()
        await seed_admin_user()

        app.state.auth_provider = PasswordAuthProvider()
        app.state.session_store = SessionStore()

        device_service = DeviceService(fake_driver)
        app.state.device_service = device_service

        poller = Poller(device_service)
        poller.start()
        app.state.poller = poller

        try:
            yield
        finally:
            await poller.stop()
            await db.close_db()

    application.router.lifespan_context = test_lifespan

    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def authed_client(client: httpx.AsyncClient) -> httpx.AsyncClient:
    response = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return client
