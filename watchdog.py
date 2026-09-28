"""Watchdog — следит за ботом и перезапускает, если упал."""
import subprocess
import time
import os
from datetime import datetime

CHECK_INTERVAL = 60  # секунд
BOT_CMD = ['python', 'bot.py']
DASHBOARD_CMD = ['python', 'web_dashboard.py']
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(WORKSPACE, 'watchdog.log')

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

def _is_running(pattern: str) -> bool:
    """Точная проверка процесса через pgrep с regex."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', pattern],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        log(f'⚠️ pgrep error: {e}')
        return False


def _is_log_fresh(log_path: str, max_age_sec: int = 900) -> bool:
    """Проверяет, менялся ли файл лога за последние max_age_sec."""
    import time
    try:
        if not os.path.exists(log_path):
            return False
        return (time.time() - os.path.getmtime(log_path)) < max_age_sec
    except Exception:
        return True  # при ошибке не мешаем watchdog-у


def is_bot_running():
    """Проверяет: процесс жив И лог свежий."""
    if not _is_running(r'^python bot\.py$'):
        return False
    log_path = os.path.join(WORKSPACE, 'bot_start.log')
    if not _is_log_fresh(log_path, max_age_sec=900):
        log('⚠️ bot.py жив, но лог не менялся >15 мин — считаем залипшим')
        return False
    return True


def is_dashboard_running():
    """Проверяет: процесс жив И лог свежий."""
    if not _is_running(r'^python web_dashboard\.py$'):
        return False
    log_path = os.path.join(WORKSPACE, 'dashboard.log')
    if not _is_log_fresh(log_path, max_age_sec=1800):
        return False
    return True
def start_bot():
    try:
        log('🚀 Запускаю bot.py...')
        with open(os.path.join(WORKSPACE, 'bot_start.log'), 'a') as f:
            subprocess.Popen(BOT_CMD, cwd=WORKSPACE, stdout=f, stderr=f, start_new_session=True)
        log('✅ bot.py запущен')
    except Exception as e:
        log(f'❌ Не смог запустить bot.py: {e}')

def start_dashboard():
    try:
        log('🚀 Запускаю web_dashboard.py...')
        with open(os.path.join(WORKSPACE, 'dashboard.log'), 'a') as f:
            subprocess.Popen(DASHBOARD_CMD, cwd=WORKSPACE, stdout=f, stderr=f, start_new_session=True)
        log('✅ web_dashboard.py запущен')
    except Exception as e:
        log(f'❌ Не смог запустить dashboard: {e}')

def main():
    log('🐕 Watchdog запущен')
    while True:
        try:
            if not is_bot_running():
                log('⚠️ Бот не работает — перезапускаю')
                start_bot()
            else:
                log('✅ Бот работает')

            if not is_dashboard_running():
                log('⚠️ Дашборд не работает — перезапускаю')
                start_dashboard()
            else:
                log('✅ Дашборд работает')

            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            log('⏹️ Watchdog остановлен вручную')
            break
        except Exception as e:
            log(f'❌ Ошибка watchdog: {e}')
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
