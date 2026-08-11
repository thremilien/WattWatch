"""Stdlib sqlite3 access, wrapped in `asyncio.to_thread` for use from async code.

No aiosqlite dependency: every blocking call to sqlite3 goes through
`asyncio.to_thread`, and a single module-level connection (opened with
`check_same_thread=False`) is reused for the life of the process. WAL mode
allows concurrent readers while a writer is active, which suits the poller
writing readings while the API concurrently serves history queries.

Two rules keep that shared connection safe, because `asyncio.to_thread` runs
callables on a *pool* of threads that can touch it simultaneously:

1. `row_factory` is set once here and must never be reassigned per-query.
   It is connection-global state, so a query that flipped it to `sqlite3.Row`
   and back raced with any concurrent query, which returned rows of the wrong
   shape — and, worse, made valid session lookups intermittently return no row
   at all, logging users out at random.
2. Every callable runs while holding `_write_lock`. Statements here are
   sub-millisecond and the app has a single user, so serialising them costs
   nothing and removes the remaining "bad parameter or other API misuse"
   errors from interleaved use of one connection.
"""

import asyncio
import sqlite3
import threading
from pathlib import Path

from wattwatch.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at);

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    power_w REAL,
    voltage_v REAL,
    current_a REAL
);
CREATE INDEX IF NOT EXISTS idx_readings_ts ON readings (ts);
"""

_connection: sqlite3.Connection | None = None
_write_lock = threading.Lock()


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(database_path), check_same_thread=False)
    # Connection-global, set exactly once. See the module docstring: mutating
    # this per-query races across to_thread pool threads.
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def get_connection() -> sqlite3.Connection:
    """Return the process-wide sqlite3 connection, opening it on first use."""
    global _connection
    if _connection is None:
        _connection = _connect(settings.database_path)
    return _connection


async def init_db() -> None:
    """Ensure the database and schema exist. Safe to call multiple times."""
    await asyncio.to_thread(get_connection)


async def close_db() -> None:
    """Close the process-wide connection, if open."""
    global _connection
    if _connection is not None:
        conn = _connection
        _connection = None
        await asyncio.to_thread(conn.close)


async def run(fn, /, *args, **kwargs):
    """Run a blocking sqlite3 callable against the shared connection in a thread.

    Serialised by `_write_lock`: the connection is shared across to_thread
    pool threads, and concurrent use of a single sqlite3 connection is not
    safe at the Python level even with `threadsafety == 3`.
    """
    conn = get_connection()

    def _call():
        with _write_lock:
            return fn(conn, *args, **kwargs)

    return await asyncio.to_thread(_call)
