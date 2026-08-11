"""FastAPI app factory: lifespan wiring, router registration, SPA static serving."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from wattwatch import db
from wattwatch.auth.password import PasswordAuthProvider, seed_admin_user
from wattwatch.auth.router import router as auth_router
from wattwatch.auth.sessions import SessionStore
from wattwatch.config import settings
from wattwatch.devices.kasa import KasaPlugDriver
from wattwatch.devices.service import DeviceService
from wattwatch.poller import Poller
from wattwatch.routers.device import router as device_router
from wattwatch.routers.energy import router as energy_router
from wattwatch.routers.history import router as history_router
from wattwatch.routers.state import health_router, state_router

logger = logging.getLogger("wattwatch")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await db.init_db()
    await seed_admin_user()

    app.state.auth_provider = PasswordAuthProvider()
    app.state.session_store = SessionStore()

    driver = KasaPlugDriver(settings.kasa_host)
    device_service = DeviceService(driver)
    app.state.device_service = device_service

    poller = Poller(device_service)
    poller.start()
    app.state.poller = poller

    try:
        yield
    finally:
        await poller.stop()
        await db.close_db()


def create_app() -> FastAPI:
    app = FastAPI(title="WattWatch", lifespan=lifespan)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(state_router)
    app.include_router(device_router)
    app.include_router(energy_router)
    app.include_router(history_router)

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        return await _spa_fallback(request)

    _mount_frontend(app)

    return app


async def _spa_fallback(request: Request) -> FileResponse | JSONResponse:
    index_path = settings.frontend_dist / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Not found"})


def _mount_frontend(app: FastAPI) -> None:
    dist = settings.frontend_dist
    assets_dir = dist / "assets"
    if not dist.is_dir():
        logger.warning("frontend_dist %s does not exist; skipping static mount (dev mode)", dist)
        return

    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", response_model=None)
    async def spa_catch_all(full_path: str, request: Request) -> FileResponse | JSONResponse:
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse(status_code=404, content={"detail": "Not found"})

        candidate = dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)

        index_path = dist / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
        return JSONResponse(status_code=404, content={"detail": "Not found"})


app = create_app()

__all__ = ["app", "create_app"]
