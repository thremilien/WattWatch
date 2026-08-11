"""Authentication seam, deliberately kept swappable for OIDC later.

Today, WattWatch has a single local admin account authenticated with a
username/password checked against a bcrypt hash (`PasswordAuthProvider`) and
server-side sessions stored in SQLite (`SessionStore`), handed to the browser
as an opaque `ww_session` cookie.

## What an OIDC swap would touch

1. Write a new class implementing `AuthProvider` (see `auth/provider.py`),
   e.g. `OidcAuthProvider`, that performs the authorization-code exchange and
   returns a `User` on success. `authenticate()`'s `username`/`password`
   signature doesn't fit an OIDC redirect flow, so in practice this means:
   - Adding provider-specific routes (`/api/auth/oidc/login`,
     `/api/auth/oidc/callback`) to `auth/router.py`, alongside or instead of
     the password form endpoint.
   - Having the callback handler validate the ID token / call userinfo, then
     construct/lookup a `User` and issue a session exactly like
     `PasswordAuthProvider`'s callers do today via `SessionStore`.
2. `SessionStore` (`auth/sessions.py`) and `require_user`
   (`auth/dependencies.py`) do not change at all — sessions and the cookie
   mechanism are orthogonal to how the user was authenticated.
3. `users` table semantics loosen: today it's exactly one bcrypt-backed admin
   row seeded from env vars at startup (see `main.py`'s lifespan). For OIDC
   you would likely stop writing `password_hash` and instead upsert a user
   row keyed by the IdP's subject claim on first login.
4. Wire the new provider into the app (dependency injection point in
   `main.py`) in place of / alongside `PasswordAuthProvider`.

Everything under `routers/` only depends on `require_user`, never on how the
session was created, so no other part of the app changes.
"""
