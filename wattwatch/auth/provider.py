"""`AuthProvider` protocol: the seam that lets auth backends be swapped."""

from typing import Protocol

from wattwatch.auth.models import User


class AuthProvider(Protocol):
    """Something that can turn credentials into a `User`."""

    async def authenticate(self, username: str, password: str) -> User | None:
        """Return a `User` on success, `None` on failure. Never raises for
        bad credentials — only for genuine infrastructure errors."""
        ...
