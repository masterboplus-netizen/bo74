"""Typed application settings loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from .constants import DEFAULT_DATABASE_NAME, ENVIRONMENT_VARIABLE


@dataclass(frozen=True)
class Settings:
    environment: str
    database_path: Path

    @classmethod
    def from_environment(cls, base_dir: Path) -> "Settings":
        environment = os.getenv(ENVIRONMENT_VARIABLE, "development")
        database_name = os.getenv("MASTERBO_DATABASE", DEFAULT_DATABASE_NAME)
        database_path = Path(database_name)

        if not database_path.is_absolute():
            database_path = base_dir / database_path

        return cls(
            environment=environment,
            database_path=database_path,
        )