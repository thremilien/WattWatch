"""Regression tests for bugs found during review.

Both of these were live defects, not hypotheticals — see the comments on each.
"""

import asyncio

import httpx


async def test_logout_clears_the_session_cookie(authed_client: httpx.AsyncClient) -> None:
    """Logout must actually send a Set-Cookie deletion to the browser.

    Regression: the handler set `delete_cookie` on the injected `Response` but
    then returned a *new* `Response`. FastAPI only merges the injected
    response's headers when the handler doesn't return a `Response` itself, so
    the deletion header was silently dropped and the browser kept the cookie.
    """
    assert authed_client.cookies.get("ww_session") is not None

    response = await authed_client.post("/api/auth/logout")

    assert response.status_code == 204
    set_cookie = response.headers.get("set-cookie", "")
    assert "ww_session=" in set_cookie, f"no session cookie deletion sent: {set_cookie!r}"
    # httpx applies the deletion to its jar, which is what a browser would do.
    assert not authed_client.cookies.get("ww_session")

    # And the session is genuinely gone server-side.
    assert (await authed_client.get("/api/state")).status_code == 401


async def test_concurrent_requests_never_drop_a_valid_session(
    authed_client: httpx.AsyncClient,
) -> None:
    """Concurrent DB access must not corrupt session lookups.

    Regression: `db.py` shared one sqlite3 connection across `asyncio.to_thread`
    pool threads while `sessions.py`/`password.py` flipped the connection-global
    `row_factory` per query. Racing queries got rows of the wrong shape, and
    valid session lookups intermittently returned no row at all — surfacing as
    a random 401 that logs the user out. The frontend polls `/api/state` every
    2s alongside history requests, so this fired in normal use.

    `/api/state` exercises the session path; `/api/history` exercises the
    positional-index query that was the other half of the race.
    """
    requests = []
    for _ in range(40):
        requests.append(authed_client.get("/api/state"))
        requests.append(authed_client.get("/api/history?hours=6"))
        requests.append(authed_client.get("/api/history/summary?hours=24"))

    responses = await asyncio.gather(*requests)

    bad = [(r.request.url.path, r.status_code) for r in responses if r.status_code != 200]
    assert not bad, f"{len(bad)} of {len(responses)} concurrent requests failed: {bad[:5]}"
