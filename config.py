"""Конфигурация БО 7.2 — без dotenv"""
import os

# === TELEGRAM ===
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# === БАЗА ДАННЫХ ===
DB_PATH = os.getenv("DB_PATH", "bo72.db")

# === СИСТЕМНЫЕ ===
DEFAULT_LANGUAGE = "ru"
DEFAULT_MODE = "brief"
TIMEZONE = "Europe/Moscow"
VERSION = "7.2"


def validate_config() -> bool:
    errors = []
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        errors.append("❌ BOT_TOKEN не задан")
    if not ADMIN_IDS:
        errors.append("⚠️ ADMIN_IDS пуст")
    if errors:
        for e in errors:
            print(e)
        return False
    print(f"✅ Конфиг БО {VERSION} валиден")
    return True


if __name__ == "__main__":
    validate_config()