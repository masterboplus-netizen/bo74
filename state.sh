#!/bin/bash
# Обновление STATE.md одной командой
# Использование: ./state.sh "строка для добавления"

cd ~/workspace
FILE=docs/STATE.md
LOG=docs/DEVLOG.md

if [ -z "$1" ]; then
  echo "Использование: ./state.sh 'строка обновления'"
  exit 1
fi

NOW=$(date '+%Y-%m-%d %H:%M')
HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
UPDATE="$1"

# Обновляем дату и хэш
sed -i "s|^\*\*Обновлено:\*\*.*|**Обновлено:** $NOW|" "$FILE"
sed -i "s|^\*\*Последний коммит:\*\*.*|**Последний коммит:** $HASH|" "$FILE"

# Добавляем в DEVLOG
sed -i "s|^# DEVLOG — журнал сессий (append-only)|# DEVLOG — журнал сессий (append-only)\n\n$NOW — $UPDATE ($HASH)|" "$LOG"

echo "OK: STATE обновлён ($NOW, $HASH)"
echo "OK: DEVLOG дополнен"
echo "---"
tail -8 "$FILE"
