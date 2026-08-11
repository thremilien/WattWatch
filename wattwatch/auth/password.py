"""Bcrypt-backed `AuthProvider` against the `users` table.

Uses the `bcrypt` package directly (not passlib). `authenticate()` always
performs a bcrypt comparison, even when the username doesn't exist, by
falling back to a dummy hash — this keeps response timing from leaking which
usernames are valid.
"""

import sqlite3
import time

import bcrypt

from wattwatch import db
from wattwatch.auth.models import User
from wattwatch.config import settings

# A precomputed bcrypt hash of a random value. Used as the comparison target
# when the username doesn't exist, so `bcrypt.checkpw` always runs.
_DUMMY_HASH = bcrypt.hashpw(b"wattwatch-dummy-password", bcrypt.gensalt())


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _get_user_row(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    # row_factory is set once in db._connect; never reassign it here.
    return conn.execute(
        "SELECT username, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()


def _upsert_user(conn: sqlite3.Connection, username: str, password_hash: str) -> None:
    conn.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?) "
        "ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash",
        (username, password_hash, int(time.time())),
    )
    # Rotating the password must not leave old sessions usable — otherwise
    # changing ADMIN_PASSWORD to lock someone out wouldn't actually do so.
    conn.execute("DELETE FROM sessions WHERE username = ?", (username,))
    conn.commit()


class PasswordAuthProvider:
    """`AuthProvider` implementation backed by bcrypt hashes in SQLite."""

    async def authenticate(self, username: str, password: str) -> User | None:
        row = await db.run(_get_user_row, username)
        target_hash = row["password_hash"].encode("utf-8") if row is not None else _DUMMY_HASH
        ok = bcrypt.checkpw(password.encode("utf-8"), target_hash)
        if row is not None and ok:
            return User(username=row["username"])
        return None


async def seed_admin_user() -> None:
    """Insert or update the admin user from `ADMIN_USERNAME`/`ADMIN_PASSWORD`.

    Called once at startup. If the stored hash no longer matches the
    configured password, it is updated in place — so changing the env var
    and redeploying changes the password.
    """
    username = settings.admin_username
    password = settings.admin_password
    row = await db.run(_get_user_row, username)
    if row is not None and bcrypt.checkpw(
        password.encode("utf-8"), row["password_hash"].encode("utf-8")
    ):
        return
    await db.run(_upsert_user, username, _hash_password(password))
