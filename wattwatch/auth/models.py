"""Auth domain model."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class User:
    username: str
