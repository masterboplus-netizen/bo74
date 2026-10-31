# 📚 КАРТА ДОКУМЕНТАЦИИ «БО»

## 🚨 ГЛАВНОЕ ПРАВИЛО ДЛЯ ИИ (ЧИТАТЬ ПЕРВЫМ)

1. **Формат ссылок:** Всегда давай ссылки в виде блока кода.
2. **Получение кода:** Пользователь сам присылает Raw-ссылки (raw.githubusercontent.com). Не нужно просить его копировать текст в чат.
3. **Группировка:** Если нужно несколько ссылок, они должны быть в ОДНОМ блоке кода (каждая на новой строке). Не разбивай их на отдельные блоки.
4. **Алгоритм начала работы:** 
   - Сначала спроси пользователя: «Над каким проектом работаем?» (Ядро, Telegram, Веб, Хераборина).
   - Дождись ответа.
   - Затем пришли все Raw-ссылки на документы **и код** ЭТОГО проекта **одним блоком кода**.
5. **⏱ ФИКСАЦИЯ СЕССИИ (ОБЯЗАТЕЛЬНО):** Как только ты получил документы и определился с проектом, ты обязан зафиксировать время начала сессии. В процессе работы ты считаешь количество отправленных сообщений, просмотренных экранов (скринов) и закрытых задач. В конце сессии (или по команде пользователя «Сохрани сессию») ты используешь скрипт из раздела «Скрипт для записи сессии» ниже.

**Пример правильной ссылки (одна):**
    https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/main.py

**Пример правильной группировки (несколько ссылок в ОДНОМ блоке):**
    https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/main.py
    https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/config.py

> **Дата:** 2026-11-01
> **Главное правило:** Старые документы лежат в папке /docs (архив). Мы работаем только с этой новой структурой.

## 📌 ТОЧНЫЕ RAW-ССЫЛКИ ДЛЯ КАЖДОГО ПРОЕКТА

**01_BO_CORE (Ядро) — Документация:**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/01_BO_CORE/MANIFEST.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/01_BO_CORE/STATE.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/01_BO_CORE/RULES.md

**01_BO_CORE (Ядро) — Код (репозиторий bo74):**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/main.py
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/config.py

**02_BO_TELEGRAM (Бот) — Документация:**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/02_BO_TELEGRAM/UI_MAP.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/02_BO_TELEGRAM/STATE_BOT.md

**02_BO_TELEGRAM (Бот) — Код (репозиторий bo74):**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/bot.py
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/db.py
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/web_dashboard.py
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/main_render.py
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/keep_alive.py

**03_BO_WEB (Веб) — Документация (в bo74):**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/03_BO_WEB/WEB_STATE.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/03_BO_WEB/API.md

**03_BO_WEB (Веб) — Код (репозиторий bo-web):**
https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main/index.html
https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main/js/main.js
https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main/js/api/supabase.js
https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main/js/api/objects.js
https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main/js/screens/objects.js
https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main/js/screens/objectDetail.js
https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main/js/screens/objectEdit.js
https://raw.githubusercontent.com/masterboplus-netizen/bo-web/main/js/modals/add_menu.js

**05_KHERABORINA (Трекер) — Документация (в bo74):**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/KHERABORINA_INSTRUCTIONS.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/CODE_MAP.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/TODO.md

**05_KHERABORINA (Трекер) — Код (репозиторий worklog):**
https://raw.githubusercontent.com/masterboplus-netizen/worklog/main/index.html
https://raw.githubusercontent.com/masterboplus-netizen/worklog/main/app.js
https://raw.githubusercontent.com/masterboplus-netizen/worklog/main/style.css
https://raw.githubusercontent.com/masterboplus-netizen/worklog/main/crypto.js
https://raw.githubusercontent.com/masterboplus-netizen/worklog/main/sw.js
https://raw.githubusercontent.com/masterboplus-netizen/worklog/main/encrypt.py

## 1. ЯДРО (01_BO_CORE)
Здесь лежит вся бизнес-логика, архитектура и правила работы.
- MANIFEST.md — Философия, суть проекта и масштаб.
- ARCHITECTURE.md — Общая архитектура ядра.
- ARCHITECTURE_ELEC.md — Детальное описание ядра ЭОМ.
- ARCHITECTURE_ESTIMATE.md — Архитектура смет.
- RULES.md — Строгие правила работы (STRICT MODE).
- AI_INSTRUCTIONS.md — Инструкции для настройки ИИ-ассистента.
- STATE.md — Текущее состояние (сессия 20, баги, планы).
- WORKPLAN.md — План и техдолг (P1-P8).
- ROADMAP.md — Глобальный план развития (8 этапов).
- ROADMAP_FLEX.md — Гибкость архитектуры (3-6 стен, двойной свет).
- UX_PRINCIPLES.md — Философия юзабилити.
- HANDOFF.md — Протокол входа для нового ИИ.
- CHANGELOG.md — История версий (от 7.0 до 8.5).
- DEPS.md — Зависимости проекта.
- DEVELOPMENT.md — Правила разработки (git, БД).
- DEVLOG.md — Журнал всех сессий разработки.
- GLOSSARY.md — Словарь терминов.
- measurement_tools.md — ТЗ для замерщика.
- room_3d_model.md — ТЗ для 3D-модели.
- service_zones.md — Проверки габаритов и конфликтов.
- transitions.md — Логика обработки кривых углов.
- MIGRATIONS.md — Описание всех миграций БД.

## 2. TELEGRAM (02_BO_TELEGRAM)
Здесь лежит всё, что касается интерфейса бота.
- UI_MAP.md — Карта кнопок и меню.
- STATE_BOT.md — История рефакторинга кода бота.
- TELEGRAM_ARCHITECTURE.md — 3 уровня обработки callback-ов.
- STYLE_GUIDE.md — Правила оформления UI.
- MASTER_GUIDE.md — Инструкция для мастеров.
- CLIENT_GUIDE.md — Инструкция для заказчиков.

## 3. ВЕБ (03_BO_WEB)
Здесь лежит документация по веб-версии (bo-web).
- WEB_STATE.md — История разработки и ошибки с доменом.
- WEB_ARCHITECTURE.md — Как устроен API и работа с Replit.
- API.md — Черновик REST API для внешних систем.
- PWA_POSTMORTEM.md — Разбор ошибок с PWA.

## 4. ХЕРАБОРИНА (05_KHERABORINA)
Отдельный проект тайм-трекера.
- KHERABORINA_INSTRUCTIONS.md — Правила, PIN, шифрование.
- CODE_MAP.md — Карта кода (app.js, style.css).
- TODO.md — Текущие задачи и баги.
- WORKLOG.md — Краткое описание работы трекера.

## 5. АРХИВ (_ARCHIVE)
Старые снимки кода, бэкапы и устаревшие версии.

## 6. СКРИПТ ДЛЯ ЗАПИСИ СЕССИИ (ШАБЛОН)

В конце работы (или по команде «Сохрани сессию») используйте этот скрипт:

cd ~/workspace/worklog-app && python3 - <<'PY'
import json, os, subprocess, sys
from pathlib import Path

# === НАСТРОЙКИ СЕССИИ (МЕНЯЙ ТОЛЬКО ЗДЕСЬ) ===
S_DATE = "2026-11-01"      # Дата сессии (YYYY-MM-DD)
S_START = "21:00"          # Время начала
S_END = "23:25"            # Время окончания
S_DURATION = 145           # Длительность в минутах
S_PROJECT = "bo81"         # Название проекта
S_NOTE = "Текст заметки"   # Краткое описание работы
S_EVENTS = 50              # Кол-во сообщений/событий
S_SCREENS = 20             # Кол-во просмотренных экранов
S_TASKS_DONE = 0           # Кол-во закрытых задач
# ================================================

p = Path('worklog.json')
if not p.exists():
    sys.exit('ОШИБКА: worklog.json не найден.')

data = json.loads(p.read_text(encoding='utf-8'))

existing = [s for s in data['sessions'] if s.get('date') == S_DATE and s.get('start') == S_START]
if existing:
    print(f"Сессия {S_START} уже есть. Обновляем...")
    existing[0].update({
        'end': S_END, 'duration_min': S_DURATION, 'note': S_NOTE,
        'events': S_EVENTS, 'screens': S_SCREENS, 'tasks_done': S_TASKS_DONE
    })
    print("Сессия обновлена.")
else:
    day_sessions = [s for s in data['sessions'] if s.get('date') == S_DATE]
    S_ID = f"s_{S_DATE.replace('-', '')}_{len(day_sessions) + 1}"
    new_session = {
        "id": S_ID, "date": S_DATE, "start": S_START, "end": S_END,
        "duration_min": S_DURATION, "project": S_PROJECT, "note": S_NOTE,
        "events": S_EVENTS, "screens": S_SCREENS, "tasks_done": S_TASKS_DONE
    }
    data['sessions'].append(new_session)
    print(f'Сессия {S_ID} добавлена.')

p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

print('Шифрование...')
res = subprocess.run(['.venv/bin/python', 'encrypt.py'], env={**os.environ, 'WORKLOG_PIN': '201186'}, capture_output=True, text=True)
if res.returncode != 0:
    sys.exit(f'ОШИБКА ШИФРОВАНИЯ: {res.stderr}')
print(res.stdout.strip())

print('Отправка на GitHub...')
subprocess.run(['git', 'add', 'worklog.json', 'data.encrypted.json'])
subprocess.run(['git', 'commit', '-m', f'data: session {S_DATE} {S_START}-{S_END}'])
res_push = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True)
if res_push.returncode != 0:
    sys.exit(f'ОШИБКА PUSH: {res_push.stderr}')
print('Успешно запушено!')
PY

**Конец карты документации.**
