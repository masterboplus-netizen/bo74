#!/bin/bash
# Запуск watchdog в фоне
cd "$(dirname "$0")"
if pgrep -f 'python watchdog.py' > /dev/null; then
    echo '⚠️ Watchdog уже запущен'
    exit 0
fi
nohup python watchdog.py > watchdog_start.log 2>&1 &
echo "✅ Watchdog запущен (PID: $!)"
