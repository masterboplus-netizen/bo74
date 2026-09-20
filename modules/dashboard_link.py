"""Получение ссылки на дашборд Бо 7.4"""
import os


def get_dashboard_url() -> str:
    """Возвращает URL дашборда Replit"""
    domain = os.getenv("REPLIT_DEV_DOMAIN", "")
    if not domain:
        # Fallback для локальной разработки
        return "http://localhost:8080/"
    return f"https://{domain}/"
