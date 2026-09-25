"""Watchdog — следит за ботом и перезапускает, если упал."""
import subprocess
import time
import os
import sys
from datetime import datetime

CHECK_INTERVAL = 60  # секунд
BOT_CMD = ['python', 'bot.py']
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

def is_bot_running():
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'python bot.py'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        log(f'⚠️ pgrep error: {e}')
        return False

def start_bot():
    try:
        log('🚀 Запускаю bot.py...')
        with open(os.path.join(WORKSPACE, 'bot_start.log'), 'a') as f:
            subprocess.Popen(BOT_CMD, cwd=WORKSPACE, stdout=f, stderr=f, start_new_session=True)
        log('✅ bot.py запущен')
    except Exception as e:
        log(f'❌ Не смог запустить bot.py: {e}')

def main():
    log('🐕 Watchdog запущен')
    while True:
        try:
            if not is_bot_running():
                log('⚠️ Бот не работает — перезапускаю')
                start_bot()
            else:
                log('✅ Бот работает')
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            log('⏹️ Watchdog остановлен вручную')
            break
        except Exception as e:
            log(f'❌ Ошибка watchdog: {e}')
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
