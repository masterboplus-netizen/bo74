"""keep_alive — не даём Replit заснуть.

Фоновый демон-поток пингует свой URL каждые 4 минуты.
Если есть DASHBOARD_URL — пингует и его. Если нет — берёт из REPLIT_DEV_DOMAIN.
"""
import os
import threading
import time
import urllib.request
from datetime import datetime

PING_INTERVAL = 240  # 4 минуты
FIRST_PING_DELAY = 30  # 30 сек после старта

_stop = threading.Event()
_started = False
_lock = threading.Lock()


def _get_urls():
    """Возвращает список URL для пинга."""
    urls = []
    # Свой дашборд
    domain = os.getenv("REPLIT_DEV_DOMAIN", "").strip()
    if domain:
        urls.append(f"https://{domain}/")
    # Основной домен (prod)
    domains = os.getenv("REPLIT_DOMAINS", "").strip()
    if domains:
        first = domains.split(",")[0].strip()
        if first:
            urls.append(f"https://{first}/")
    # UptimeRobot (если настроен)
    uptime_url = os.getenv("UPTIME_URL", "").strip()
    if uptime_url:
        urls.append(uptime_url)
    return urls


def _ping(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BoKeepAlive/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False


def _loop():
    urls = _get_urls()
    if not urls:
        print("⚠️ keep_alive: нет URL для пинга (нет REPLIT_DEV_DOMAIN / REPLIT_DOMAINS)", flush=True)
        return
    print(f"🐕 keep_alive: пингую {len(urls)} URL каждые {PING_INTERVAL // 60} мин", flush=True)
    for u in urls:
        print(f"   → {u}", flush=True)
    time.sleep(FIRST_PING_DELAY)
    while not _stop.is_set():
        for u in urls:
            ok = _ping(u)
            ts = datetime.now().strftime("%H:%M:%S")
            mark = "✅" if ok else "⚠️"
            print(f"{mark} [{ts}] ping {u}", flush=True)
        _stop.wait(PING_INTERVAL)


def start():
    """Запускает фоновый поток (идемпотентно)."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
    t = threading.Thread(target=_loop, name="keep_alive", daemon=True)
    t.start()
    print("✅ keep_alive запущен", flush=True)


def stop():
    _stop.set()


if __name__ == "__main__":
    start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop()
        print("⏹️ keep_alive остановлен")
