"""`/api/auth/*` — login, logout, current user.

Login and health are the only unauthenticated endpoints in the app; every
other router is protected by `require_user` at the router level.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from wattwatch.auth.dependencies import require_user
from wattwatch.auth.models import User
from wattwatch.auth.password import PasswordAuthProvider
from wattwatch.auth.provider import AuthProvider
from wattwatch.auth.sessions import COOKIE_NAME, SessionStore
from wattwatch.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str


def _get_auth_provider(request: Request) -> AuthProvider:
    return request.app.state.auth_provider


def _get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.session_lifetime_hours * 3600,
        path="/",
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )


@router.post("/login", response_model=UserResponse)
async def login(payload: LoginRequest, request: Request, response: Response) -> UserResponse:
    auth_provider: PasswordAuthProvider = _get_auth_provider(request)
    user = await auth_provider.authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    session_store = _get_session_store(request)
    session = await session_store.create(user.username)
    _set_session_cookie(response, request, session.token)
    return UserResponse(username=user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    """Delete the session server-side and clear the cookie.

    Returns `None` rather than a fresh `Response`: FastAPI only merges the
    injected response's headers when the handler doesn't return a `Response`
    itself, so returning one here would silently drop the Set-Cookie deletion.
    The delete attributes must also match how the cookie was set, or browsers
    keep the original.
    """
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session_store = _get_session_store(request)
        await session_store.delete(token)
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(require_user)) -> UserResponse:
    return UserResponse(username=user.username)
