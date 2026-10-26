# ХЕРАБОРИНА — Инструкции для AI (Правила, данные, шифрование)

> **Хераборина (worklog-app)** — это PWA-трекер времени Andrey. 
> **Важно:** Это отдельный проект, НЕ часть Бо 8.1. 
> Читать перед началом работы с тайм-трекером.

## 1. ЧТО ЧИТАТЬ В НАЧАЛЕ СЕССИИ (по Хераборине)
1. docs/05_KHERABORINA/KHERABORINA_INSTRUCTIONS.md ← этот файл
2. docs/01_BO_CORE/HANDOFF.md — как войти в проекты

## 2. ОБЩИЕ ПРАВИЛА РАБОТЫ
- Один патч → тест в браузере → коммит.
- Одна команда — один блок.
- Перед патчем — свежий grep/sed (номера строк плавают).
- Бэкап перед риском: cp file file.bak_ИМЯ_20261025_132751.
- Откат: git checkout path/to/file.

## 3. ПРАВИЛО ПОЛУНОЧИ (КРИТИЧНО)
Сессия НЕ может пересекать полночь. Если Andrey работал с 20:24 до 00:44:
- Создать ДВЕ сессии:
  - s_YYYYMMDD_N (дата старта): 20:24 → 23:59.
  - s_YYYYMMDD+1_1 (следующий день): 00:00 → 00:44.
- Дневник = СЕССИИ (могут быть множественные в один день).
- Вкладка «Время» = ДНИ (уникальные даты, не количество сессий).
- Среднее/день = сумма реальных часов / кол-во уникальных дней.

*Пример: s_20261016_3 (20:24→23:59, 215мин) + s_20261017_1 (00:00→00:44, 44мин).*

## 4. PIN И ДАННЫЕ
- **PIN:** 201186 (НЕ в git!).
- **Данные:** worklog.json → encrypt.py → data.encrypted.json.
- encrypt.py — только .venv/bin/python (системный python3 не имеет cryptography).
- **Команда шифрования:** WORKLOG_PIN='201186' .venv/bin/python encrypt.py

## 5. ОБНОВЛЕНИЕ ДАННЫХ (4 шага)
1) Добавить/правка сессии в worklog.json.
2) Проверка: python3 -m json.tool worklog.json > /dev/null && echo JSON OK
3) Шифрование: WORKLOG_PIN='201186' .venv/bin/python encrypt.py
4) Push: git add worklog.json data.encrypted.json && git commit -m data: ... && git push origin main

## 6. CACHE-BUST — ВАЖНО
Браузер держит старый app.js/style.css.
После правки app.js/style.css → увеличить ?v=N в index.html.
Сейчас v=3.

## 7. ГРАБЛИ
1. **Cache-bust:** забыл поднять ?v=N → пользователь видит старый UI.
2. **encrypt.py системным python3** → ModuleNotFoundError: cryptography.
3. **sed -i на Android (busybox) ломает UTF-8.** Для записи русских строк использовать python3 (Path.read_text/write_text с encoding='utf-8').

## 8. ЧЕГО AI НЕ ДЕЛАЕТ
- НЕ коммитит worklog.json без data.encrypted.json.
- НЕ даёт 2+ команд разом, если могут упасть.
- НЕ патчит вслепую — сначала grep/sed.

## 9. ССЫЛКИ
- Репо: github.com/masterboplus-netizen/worklog
- Хостинг: https://masterboplus-netizen.github.io/worklog/

**Конец инструкций.**## 5. ОБНОВЛЕНИЕ ДАННЫХ (Одной командой)

Вместо ручного внесения правок, проверки JSON, шифрования и пуша, используйте единый Python-скрипт. 
Он сам считает количество сессий за день, присвоит правильный ID (защита от перезаписи), зашифрует данные и запушит на GitHub.

Шаблон для терминала (скопируйте и поменяйте настройки в начале):

python3 - <<'PY'
import json, os, subprocess, sys
from pathlib import Path

# === НАСТРОЙКИ СЕССИИ ===
S_DATE = "2026-10-26"
S_START = "02:31"
S_END = "03:55"
S_DURATION = 84
S_PROJECT = "bo81"
S_NOTE = "Текст заметки"
S_EVENTS = 35
S_SCREENS = 12
# ==========================

p = Path('worklog.json')
data = json.loads(p.read_text(encoding='utf-8'))
day_sessions = [s for s in data['sessions'] if s.get('date') == S_DATE]
S_ID = f"s_{S_DATE.replace('-', '')}_{len(day_sessions) + 1}"

new_session = {
    "id": S_ID, "date": S_DATE, "start": S_START, "end": S_END,
    "duration_min": S_DURATION, "project": S_PROJECT, "note": S_NOTE,
    "events": S_EVENTS, "screens": S_SCREENS
}
data['sessions'].append(new_session)
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Сессия {S_ID} добавлена.')

res = subprocess.run(['.venv/bin/python', 'encrypt.py'], env={**os.environ, 'WORKLOG_PIN': '201186'}, capture_output=True, text=True)
if res.returncode != 0: sys.exit(f'ОШИБКА: {res.stderr}')
print(res.stdout.strip())

subprocess.run(['git', 'add', 'worklog.json', 'data.encrypted.json'])
subprocess.run(['git', 'commit', '-m', f'data: session {S_DATE} {S_START}-{S_END}'])
res_push = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
if res_push.returncode != 0: sys.exit(f'PUSH: {res_push.stderr}')
print('Успешно запушено!')
PY

