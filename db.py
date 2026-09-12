"""Database helpers."""

import sqlite3

from config import settings


def connect() -> sqlite3.Connection:
    """Open a SQLite connection using the configured database path."""
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    return connection