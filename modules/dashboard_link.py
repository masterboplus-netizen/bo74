"""Получение ссылки на дашборд Бо 7.7"""
import os


def get_dashboard_url() -> str:
    """Возвращает URL дашборда Replit.
    Приоритет: REPLIT_DOMAINS > REPLIT_DEV_DOMAIN > localhost."""
    # REPLIT_DOMAINS может содержать несколько доменов через запятую — берём первый
    domains = os.getenv("REPLIT_DOMAINS", "").strip()
    if domains:
        first = domains.split(",")[0].strip()
        if first:
            return f"https://{first}/"

    domain = os.getenv("REPLIT_DEV_DOMAIN", "").strip()
    if domain:
        return f"https://{domain}/"

    # Fallback для локальной разработки
    return "http://localhost:8080/"
