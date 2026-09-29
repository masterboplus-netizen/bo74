#!/bin/bash
cd ~/workspace
source venv/bin/activate
pkill -9 -f "python bot.py" 2>/dev/null
pkill -9 -f "python web_dashboard.py" 2>/dev/null
pkill -9 -f "python watchdog.py" 2>/dev/null
sleep 2
nohup python bot.py > bot_start.log 2>&1 &
nohup python web_dashboard.py > dashboard.log 2>&1 &
nohup python watchdog.py > watchdog.log 2>&1 &
echo "✅ Запущено (venv)"
