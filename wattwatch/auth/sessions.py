"""Server-side session storage, backed by the `sessions` SQLite table."""

import secrets
import sqlite3
import time
from dataclasses import dataclass

from wattwatch import db
from wattwatch.config import settings

COOKIE_NAME = "ww_session"


@dataclass(slots=True, frozen=True)
class Session:
    token: str
    username: str
    created_at: int
    expires_at: int


def _insert_session(
    conn: sqlite3.Connection, token: str, username: str, now: int, expires_at: int
) -> Session:
    conn.execute(
        "INSERT INTO sessions (token, username, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, username, now, expires_at),
    )
    conn.commit()
    return Session(token=token, username=username, created_at=now, expires_at=expires_at)


def _get_session(conn: sqlite3.Connection, token: str, now: int) -> sqlite3.Row | None:
    # row_factory is set once in db._connect; never reassign it here.
    return conn.execute(
        "SELECT token, username, created_at, expires_at FROM sessions "
        "WHERE token = ? AND expires_at > ?",
        (token, now),
    ).fetchone()


def _delete_session(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()


def _prune_expired(conn: sqlite3.Connection, now: int) -> None:
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
    conn.commit()


class SessionStore:
    """Create, look up, and delete sessions in the `sessions` table."""

    async def create(self, username: str) -> Session:
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        expires_at = now + settings.session_lifetime_hours * 3600
        await self.prune_expired()
        return await db.run(_insert_session, token, username, now, expires_at)

    async def get(self, token: str) -> Session | None:
        row = await db.run(_get_session, token, int(time.time()))
        if row is None:
            return None
        return Session(
            token=row["token"],
            username=row["username"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    async def delete(self, token: str) -> None:
        await db.run(_delete_session, token)

    async def prune_expired(self) -> None:
        await db.run(_prune_expired, int(time.time()))
