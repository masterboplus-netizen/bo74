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
    try:
        result = subprocess.run(
            ['pgrep', '-f', pattern],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        log(f'⚠️ pgrep error: {e}')
        return False

def is_bot_running():
    return _is_running('python bot.py')

def is_dashboard_running():
    return _is_running('python web_dashboard.py')

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
