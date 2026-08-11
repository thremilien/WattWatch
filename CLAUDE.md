# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Self-hosted control and energy monitoring for a single TP-Link Kasa HS110 smart plug. FastAPI backend talks to the plug directly over LAN (no cloud, no UDP discovery), polls it, stores history in SQLite, and serves a Svelte 5 dashboard — all as one container. Built for exactly one HS110; multi-device support is not implemented anywhere in the data model.

## Commands

Backend (from repo root, requires `uv`):
```bash
uv sync
uv run uvicorn wattwatch.main:app --reload --port 8420
uv run ruff check .      # lint
uv run ruff format .     # format
uv run pytest            # all tests
uv run pytest tests/test_api.py::test_login_logout_flow -v   # single test
```

Frontend (from `frontend/`, requires Node 20+, dev server proxies `/api` to `:8420`):
```bash
npm install
npm run dev       # vite dev server, hot reload
npm run build     # writes to frontend/dist, which the backend serves directly
```

The backend starts and serves the API even when the plug is unreachable, so backend work doesn't require the physical device — but device-dependent behavior (control, live readings, on-device stats) must be exercised through the `FakePlugDriver` seam in tests rather than by hand against hardware you may not have.

`ADMIN_PASSWORD` is required and validated at import time (`wattwatch/config.py`), so it must be set in the environment or `.env` before importing anything from `wattwatch` — `tests/conftest.py` sets sane defaults via `os.environ.setdefault(...)` before its own imports for this reason.

## Architecture

### The `PlugDriver` seam

Everything the app needs from the physical device is defined as a `Protocol` in `wattwatch/devices/base.py`. `KasaPlugDriver` (`devices/kasa.py`) implements it against python-kasa/real hardware; `FakePlugDriver` (`tests/fakes.py`) implements the identical protocol in memory. This is what lets tests exercise device control and degradation paths — including destructive ones like power-off, reboot, and erase-stats — without touching real hardware. When adding a device capability, add it to the protocol first, then both implementations.

python-kasa gotcha baked into `KasaPlugDriver`: `Emeter` subclasses `Usage`, and the inherited `usage_this_month`/`usage_today` properties raise `KeyError: 'time'` on this device's firmware — only the explicit accessors in `get_live()` are used, never a blanket attribute iteration over the Energy module.

### `DeviceService` owns the cache; nothing else talks to the driver directly

`DeviceService` (`devices/service.py`) holds the one `PlugDriver` instance, an `asyncio.Lock` serializing all device I/O, and the last-known-good `DeviceState` (info + live reading + reachability). `/api/state` (`routers/state.py`) always reads `service.state` — a plain property, no I/O — and never calls the device inline, so a slow or dead plug can never hang that request. Only the background `Poller` and the mutating `/api/device/*` endpoints (which explicitly want a fresh read-after-write via `service.act(...)`) talk to the driver.

### Two independent energy data sources — do not conflate them

- **On-device stats** (`/api/energy/*`, via `service.daily_stats`/`monthly_stats`/`erase_stats`): the plug's own emeter counters, including `consumption_total`. These are read straight from the device and are not always internally consistent with each other — e.g. `consumption_total` can be smaller than the current month's bucketed total after an `erase_stats()` call, since they're separate on-device registers. Treat this data as informational, not authoritative.
- **Local history** (`/api/history/*`, backed by the `readings` SQLite table, written by `Poller` every `HISTORY_INTERVAL_SECONDS`): finer-grained and the trustworthy source for anything beyond what the device itself retains (~a month of daily / a year of monthly on-device). `history.py` downsamples to at most `MAX_HISTORY_POINTS` (720) via SQL bucket averaging and computes energy by trapezoidal integration of power over time — it never loads full ranges into Python.

### `Poller` — the only writer of history, and the only thing that calls `refresh_cache`

Background `asyncio.Task` started in the app lifespan (`main.py`). Each cycle: refresh `DeviceService`'s cache, optionally persist a `readings` row (throttled to `HISTORY_INTERVAL_SECONDS`), and roughly hourly prune rows older than `HISTORY_RETENTION_DAYS` (0 disables pruning). On device failure it logs once (not every cycle), keeps serving the last-known-good cache with `reachable=False`, and backs off the poll interval up to 60s; it never raises out of the loop or blocks startup.

### Database: one shared `sqlite3` connection, not aiosqlite

`db.py` opens a single process-wide `sqlite3.Connection` (`check_same_thread=False`, WAL mode) and routes every call through `asyncio.to_thread`, serialized by a `threading.Lock` since a shared connection isn't safe for concurrent use even with `threadsafety == 3`. `row_factory` is set exactly once at connection time and **must never be reassigned per-query** — doing so previously raced across the `to_thread` pool and intermittently logged users out by returning session rows of the wrong shape. All query functions take `conn` as their first argument and are dispatched via `db.run(fn, *args)`.

### Auth: deliberately swappable, single admin account today

`wattwatch/auth/__init__.py` documents the full seam (read it before touching auth). Today: one bcrypt-hashed admin account seeded from `ADMIN_USERNAME`/`ADMIN_PASSWORD` at every startup (`seed_admin_user`, re-hashes on password change), `PasswordAuthProvider` implementing the `AuthProvider` protocol (`auth/provider.py`), and `SessionStore` issuing opaque tokens in an `ww_session` HttpOnly cookie, persisted in the `sessions` table. Every protected `APIRouter` is constructed with `dependencies=[Depends(require_user)]` at the router level (`auth/dependencies.py`) — no individual handler performs its own auth check. A future OIDC provider would only touch `auth/provider.py` + new routes in `auth/router.py`; `SessionStore`/`require_user`/every other router stay untouched.

### Frontend: Svelte 5 runes, no store library, no router

`frontend/src/lib/state.svelte.js` holds plain exported singleton class instances (`auth`, `deviceState`, `toasts`, `priceState`) using `$state`/`$derived` runes directly — there is no Svelte store or state-management library. `deviceState` polls `/api/state` every 2s while the tab is visible and keeps a rolling sparkline buffer. `api.js` is a thin `fetch` wrapper (JSON in/out, same-origin credentials) with a single `onUnauthorized` hook that flips the app back to the login screen on any 401. It's a single-page dashboard (`App.svelte` conditionally renders `LoginScreen` vs. the dashboard grid) — no client-side router.

### One container, two runtimes

`Dockerfile` is a two-stage build: Node builds the Svelte frontend to static files, then the Python/uv runtime image copies those into `frontend/dist` and serves them directly from FastAPI (`main.py`'s `_mount_frontend` — SPA catch-all with an `/api` passthrough to 404). There's no separate frontend server in production. Runs behind Traefik; uvicorn is started with `--proxy-headers --forwarded-allow-ips=*` since the session cookie's `Secure` flag is derived from `request.url.scheme`, which depends on those headers being trusted.

### Testing

`tests/conftest.py` builds a fully isolated app per test: a temp-file SQLite DB, a fresh `FakePlugDriver`, and its own lifespan (mirroring `main.py`'s real one) rather than reusing the module-level `app`. `authed_client` is a fixture that logs in and returns an authenticated `httpx.AsyncClient`. `tests/test_regressions.py` exists specifically for previously-shipped live bugs — read the docstrings there before touching sessions, cookies, or the shared DB connection, since they explain failure modes that are easy to reintroduce.
