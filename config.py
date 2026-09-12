"""Application configuration."""

from pathlib import Path

from core.settings import Settings


BASE_DIR = Path(__file__).resolve().parent
settings = Settings.from_environment(BASE_DIR)