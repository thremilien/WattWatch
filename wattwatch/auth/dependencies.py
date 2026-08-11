"""The single `require_user` dependency, applied at router level.

Every protected `APIRouter` is constructed with
`dependencies=[Depends(require_user)]` — individual route handlers must not
contain their own auth checks. This is the one place session cookies are
read and validated.
"""

from fastapi import HTTPException, Request, status

from wattwatch.auth.models import User
from wattwatch.auth.sessions import COOKIE_NAME, SessionStore

_NOT_AUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
)


async def require_user(request: Request) -> User:
    """Resolve the current session cookie to a `User`, or raise 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise _NOT_AUTHENTICATED

    session_store: SessionStore = request.app.state.session_store
    session = await session_store.get(token)
    if session is None:
        raise _NOT_AUTHENTICATED

    request.state.session_token = session.token
    return User(username=session.username)
