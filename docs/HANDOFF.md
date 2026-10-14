# HANDOFF — как войти в проект «Бо 8.1»

> Для нового чата с AI. Прочитай ПЕРВЫМ.
> Дата: 2026-10-14. Сессия: 16.

---

## 1. ЧТО ЭТО

«Бо 8.1» — цифровая экосистема для строительной компании. Telegram-бот + SQLite + Python 3.13.
Стек: python-telegram-bot[job-queue], APScheduler, reportlab, openpyxl, rapidfuzz.
Andrey — автор, работает с мобилы через Replit Shell + VPN, скрин = 40 строк.
AI — ведёт патчи, следит за архитектурой, разбивает God Objects.

---

## 2. ПРАВИЛА (ЖЁСТКО)

- Один патч → один py_compile → один скрин → один тест → один коммит.
- НЕ давать 2+ команд в одном сообщении, если могут упасть.
- Номера строк УСТАРЕВАЮТ после каждого патча. Перед патчем — ВСЕГДА свежий grep -n.
- Перед рискованным патчем — cp file file.bak_1791973544
- Если OLD_NOT_FOUND — не гадать, прислать sed -n + cat -A.
- 30 минут без движения → СТОП, откат, читаем STATE.md.
- git checkout — наш бэкап.
- Максимум 3 вопроса за раз.
- **Перед патчем с отступами — python3 tools/show_structure.py <file> <from> <to>** (НЕ cat -A).

---

## 3. ГДЕ МЫ (сессия 16)

handle_callback разрезан на домены. Создан пакет handlers/commands/callbacks/:

- tasks.py — my_tasks, by_assignee, byassigned_ (+ меню задач byobj, archive, menu_back)
- estimates.py — 30+ поддоменов смет (est_csv, est_pdf, est_export, est_kpi, est_prices, est_sched, est_where, est_buy, est_status, est_allwork, est_allmat, est_object_floors, est_object_rooms, est_room_per, est_room_sess, est_room_mat, est_room_work, est_compare, menu_estimates)
- kpi.py — menu_kpi, kpi_masters, kpi_objects, kpi_red
- finance.py — menu_finance, finobj_

_legacy.py: 3102 -> 1625 строк (-48%).

---

## 4. ТЕХДОЛГ

A. handle_callback — осталось ~600 строк (personal, reports, obj*, menu_objects, menu_dashboard, menu_help).
B. handle_text (975) — монстр, резать по доменам.
C. rooms.py (7638) — следующий God Object.
D. menu_tasks — дубликат tasks_command (работает).
E. Универсальный приёмник файлов (handle_document).
F. modules/ -> core/ (176 импортов) через шим.

---

## 5. ГЛАВНЫЕ ГРАБЛИ

UnboundLocalError из-за локальных импортов.

## 6. КАК РАБОТАТЬ С ANDREY

- Мобила, Replit Shell, VPN моргает.
- Максимум 3 вопроса.
- Если патч не сработал — show_structure.py.

## 7. ЕСЛИ СЛОМАЛОСЬ

1. tail -40 bot_start.log
2. git checkout path/to/file.py
3. ./start_all.sh

## 8. КОММИТЫ

Формат: feat(модуль): ..., fix(модуль): ..., refactor(модуль): ..., docs(state): ...

## 9. ЧТО ЧИТАТЬ

1. docs/STATE.md
2. docs/BO_MANIFEST.md
3. docs/HANDOFF.md (этот)
4. docs/WORKPLAN.md
5. docs/UX_PRINCIPLES.md

---

## 10. КАРТА КОДА — ЧТО ГДЕ ЛЕЖИТ

Точки входа: bot.py, start_all.sh, config.py, db.py.

handlers/commands/ — пакет:
- __init__.py (реэкспорт)
- _legacy.py — handle_callback (1625 строк), handle_text (975)
- start.py, personal.py, receipt.py, photos.py, crm.py, finance.py,
  objects.py, tasks.py, choose_expense.py, document.py, keyboards.py, add_menu.py, utils.py
- callbacks/ — НОВЫЙ пакет (сессия 16):
  - tasks.py, estimates.py, kpi.py, finance.py

core/ — бизнес-логика (spec.py, rooms.py, floors.py, geometry.py, room_estimate.py, floor_estimate.py, object_estimate.py, extra_works.py, report_schedule.py, economics.py, marketplaces.py, elec_*, plumbing_panels.py, comms.py, export/pdf_export.py).

interfaces/telegram/rooms.py — 7638 строк, следующий God Object.

modules/ — СТАРАЯ логика (176 импортов): backup_db, calendar, crm, dashboard_link, digest, finance, kpi, objects, ocr, parser, personal, phone_utils, reports, tasks, users.

migrations/ — SQL 001-050+. ~110 таблиц.

docs/ — HANDOFF.md, STATE.md, BO_MANIFEST.md, WORKPLAN.md, UX_PRINCIPLES.md, STYLE_GUIDE.md, ROADMAP_FLEX.md.

tools/ — show_structure.py.

---

## 11. ШПАРГАЛКА

Структура файла:
python3 tools/show_structure.py <file> <from> <to>

Перезапуск:
pkill -9 -f python bot.py ; sleep 2 ; ./start_all.sh ; sleep 5 ; tail -5 bot_start.log

Трейсбек: tail -40 bot_start.log

Поиск функции: grep -n '^async def ИМЯ\|^def ИМЯ' <файл>

Точные пробелы: sed -n 'X,Yp' file | cat -A

Бэкап: cp file file.bak_ИМЯ_20261014_102544

Откат: git checkout path/to/file.py

---

## 12. ПРИМЕР РАБОЧЕГО ПАТЧА

Шаг 1 — свежий grep: grep -n '^async def \|^def ' handlers/commands/_legacy.py
Шаг 2 — бэкап.
Шаг 3 — Python-патч: вырезать блок, записать в новый файл, удалить из _legacy.
Шаг 4 — py_compile обоих.
Шаг 5 — импорт в _legacy.py.
Шаг 6 — перезапуск + тест + коммит.
Шаг 7 — если NameError: проверить, что ВСЕ зависимости импортированы в шапке нового модуля.

---

## 13. КОММИТЫ сессии 16 (HEAD 4c9e053)

26 коммитов, всё на GitHub. См. docs/STATE.md.

---

## 14. ЧТО ДАЛЬШЕ

1. Оставшиеся ~600 строк _legacy.py -> callbacks/personal.py, reports.py, objects.py, misc.py
2. rooms.py (7638) -> rooms/ по доменам (высокий риск)
3. Рефакторинг menu_tasks (убрать дубликат)
4. handle_text (975) -> text/ по доменам
5. Универсальный приёмник файлов
6. modules/ -> core/ через шим

---

## 15. ТЕХНИЧЕСКИЕ ДЕТАЛИ

python-telegram-bot 20+ (async). Application, ContextTypes.DEFAULT_TYPE.
await query.answer() — ПЕРВЫМ в callback-хендлере.
await query.edit_message_text() — может падать Message is not modified. try/except.
Порядок add_handler — первый матч выигрывает.

SQLite: get_connection() из db.py. row_factory = sqlite3.Row.

---

## 16. АРХИТЕКТУРНЫЕ ПРИНЦИПЫ

- Один патч — одно изменение.
- Модуль = домен.
- Реэкспорт через __init__.py.
- Минимум правок в bot.py.
- God Objects резать постепенно.
- _legacy.py — временное.
- Тест вручную после каждого патча.
- Коммит после каждого успешного патча.

---

## 17. ПЕРВЫЙ ПАТЧ НОВОГО AI

1. Прочитай HANDOFF.md, STATE.md, BO_MANIFEST.md.
2. Спроси Andrey: какая задача?
3. Свежий grep -n или show_structure.py.
4. Бэкап.
5. Патч одной командой.
6. py_compile.
7. Перезапуск.
8. Тест.
9. Коммит.
10. Если сломалось — git checkout.

---

## 18. ЧТОБЫ ПОГРУЗИТЬСЯ (30 минут)

1. docs/HANDOFF.md (этот) — 15 мин.
2. docs/STATE.md — 3 мин.
3. docs/BO_MANIFEST.md (разделы 1, 3, 4, 5) — 10 мин.
4. docs/UX_PRINCIPLES.md — 5 мин.

Не читай пока: rooms.py, _legacy.py, migrations/.
Открывай точечно через show_structure.py.

---

Готов. Ты вооружён знанием. Погнали.
