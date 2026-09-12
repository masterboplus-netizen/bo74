"""Permission definitions used by the application."""

from enum import StrEnum


class Permission(StrEnum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


DEFAULT_PERMISSIONS = frozenset({Permission.READ})