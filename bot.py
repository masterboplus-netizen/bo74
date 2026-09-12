"""Application entry point."""

from config import settings
from core.constants import APP_NAME


def run() -> None:
    """Start the application."""
    print(f"{APP_NAME} is ready in {settings.environment} mode.")