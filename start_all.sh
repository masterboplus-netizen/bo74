#!/bin/bash
# Запуск всего: бот + дашборд + watchdog
cd "$(dirname "$0")"

echo "⏹️ Убиваю старые процессы..."
pkill -9 -f "python bot.py" 2>/dev/null
pkill -9 -f "python web_dashboard.py" 2>/dev/null
pkill -9 -f "python watchdog.py" 2>/dev/null
sleep 3

echo "🚀 Запускаю бота..."
nohup python bot.py > bot_start.log 2>&1 &
sleep 3

echo "🚀 Запускаю дашборд..."
nohup python web_dashboard.py > dashboard.log 2>&1 &
sleep 2

echo "🐕 Запускаю watchdog..."
nohup python watchdog.py > watchdog.log 2>&1 &
sleep 3

echo ""
echo "=== ПРОЦЕССЫ ==="
ps aux | grep -v grep | grep -E "python (bot|web_dashboard|watchdog)" | awk "{print \$2, \$11, \$12}"
echo ""
