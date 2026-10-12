# HANDOFF — как войти в проект «Бо 8.1»

> Для нового чата с AI. Прочитай ПЕРВЫМ.
> Дата: 2026-10-12 22:20. Сессия: 15.

---

## 1. ЧТО ЭТО

«Бо 8.1» — цифровая экосистема для строительной компании. Telegram-бот + SQLite + Python 3.13.
Стек: python-telegram-bot[job-queue], APScheduler, reportlab, openpyxl, rapidfuzz.
Andrey — автор, работает с мобилы через Replit Shell + VPN, скрин = 40 строк.
AI — ведёт патчи, следит за архитектурой, разбивает God Objects.

---

## 2. ПРАВИЛА (ЖЁСТКО)

- Один патч → один py_compile → один скрин → один коммит.
- НЕ давать 2+ команд в одном сообщении, если могут упасть.
- Номера строк УСТАРЕВАЮТ после каждого патча. Перед патчем — ВСЕГДА свежий grep -n.
- Перед рискованным патчем — cp file file.bak_name_$(date +%s)
- Если OLD_NOT_FOUND — не гадать, прислать sed -n + cat -A.
- 30 минут без движения → СТОП, откат, читаем STATE.md.
- git checkout — наш бэкап.
- Максимум 3 вопроса за раз.

---

## 3. ГДЕ МЫ (сессия 15)

Сделано: handlers/commands.py (4736 строк) → пакет handlers/commands/ с 13 модулями.

Модули (все живые, реэкспорт через __init__.py):
- start.py — start, help_command, _help_text
- personal.py — personal_command, format_personal_summary, personal_keyboard
- receipt.py — 5 receipt-хендлеров
- photos.py — 8 photos-хендлеров
- crm.py — 4 crm-функции
- finance.py — 6 finance-функций
- objects.py — 7 objects-функций
- tasks.py — 15 tasks-функций
- choose_expense.py — 4 функции выбора объекта
- document.py — handle_document (CSV/XLSX)
- keyboards.py — main_menu_keyboard
- add_menu.py — handle_add_menu
- _legacy.py — ЧТО ОСТАЛОСЬ: handle_callback (2055), handle_text (975), parse_date (156)

Стратегия разреза (проверена):
1. Вырезать блок строк из _legacy.py → новый файл модуля
2. В _legacy.py — импорт: from handlers.commands.X import Y
3. __init__.py — дописать реэкспорт
4. py_compile → перезапуск → тест → коммит

---

## 4. ТЕХДОЛГ

A. parse_date (156 строк) — циклический импорт (_legacy.py:2538 импортирует сам себя). Вынести в utils.py.

B. handle_callback (2055) и handle_text (975) — монстры. Резать по доменам отдельной сессией. НЕ в спешке.

C. rooms.py (7638 строк) — следующий God Object. Домены: walls, openings, comms, elec, plumbing, reports, core.

D. Универсальный приёмник файлов — handle_document сейчас только CSV/XLSX-прайсы. Нужно: определять тип (прайс / счёт комплектации / счёт оплаты / накладная / чек) → роутить.

E. modules/ → core/ — 176 импортов. Стратегия: шим.

---

## 5. ГЛАВНЫЕ ГРАБЛИ

UnboundLocalError из-за локальных импортов:
- Внутри функции есть from modules.X import Y
- Вызов Y() ВЫШЕ этого импорта → UnboundLocalError
- Фикс: удалить локальные импорты, глобальный покрывает
- Уже пофикшено: 18+5+1 (коммиты 0eec77b, 6949b1b, 69c8070)

Номера строк меняются после каждого патча — grep -n перед патчем.

Бэкапы — перед рискованным патчем. git checkout — откат.

---

## 6. КАК РАБОТАТЬ С ANDREY

- Мобила, Replit Shell, VPN моргает — процесс может упасть, это норма.
- Восстановить: ./start_all.sh
- Максимум 3 вопроса.
- Не давать 2+ команд разом.
- Если патч не сработал — sed -n X,Yp file | cat -A.
- «Бо 7.7» / «Бо 8.1» — версии. Сейчас 8.1.

---

## 7. ЕСЛИ СЛОМАЛОСЬ

1. tail -40 bot_start.log — трейсбек
2. Если не запускается: py_compile → git checkout → ./start_all.sh
3. Если кнопка не работает: смотрим callback в логе → grep -n по коду → проверяем pattern в bot.py
4. Message is not modified — try/except с игнором

---

## 8. КОММИТЫ

Формат: feat(модуль): ..., fix(модуль): ..., refactor(модуль): ..., docs(state): ...
git push — через GITHUB_TOKEN в Replit Secrets, не всегда работает.

---

## 9. ЧТО ЧИТАТЬ

1. docs/STATE.md — где мы сейчас
2. docs/BO_MANIFEST.md — манифест
3. docs/HANDOFF.md — этот файл
4. docs/WORKPLAN.md — план
5. docs/UX_PRINCIPLES.md — 18 принципов

---

Всё. Ты в курсе. Погнали.


---

## 10. КАРТА КОДА — ЧТО ГДЕ ЛЕЖИТ

### 10.1. Точки входа

bot.py — точка входа. Регистрирует все хендлеры.
- main() — запуск
- add_handlers(app) — регистрация
- ПОРЯДОК хендлеров ВАЖЕН — первый матч выигрывает.
- Ключевые хендлеры:
  - CommandHandler('start', start) — handlers/commands/start.py
  - CommandHandler('tasks', tasks_command) — tasks.py
  - CommandHandler('personal', personal_command) — personal.py
  - CallbackQueryHandler(handle_rooms_callback, pattern='^(rooms_list_|room_|wall_|openings_|opening_|comm_|obj_|floor_|group_|cables_|panels_|panel_|plumb_|works_|prices_)') — ПЕРВЫЙ. Ловит много. Свалка.
  - CallbackQueryHandler(handle_callback, pattern='^(menu_crm|crm_|unknown_|deal_|client_|activity_)')
  - CallbackQueryHandler(handle_callback, pattern='^(?!room_|rooms_|wall_|...).*')
  - MessageHandler(filters.Document.ALL, handle_document)
  - MessageHandler(filters.PHOTO, handle_photo)
  - MessageHandler(filters.TEXT, handle_text)

start_all.sh — venv + python bot.py + web_dashboard + watchdog.
Перезапуск: pkill -9 -f 'python bot.py' ; sleep 2 ; ./start_all.sh ; sleep 5

config.py — токен, DB_PATH, ADMIN_IDS, MAIN_ADMIN_TG_ID.
db.py — обёртка SQLite. get_connection(), fetchone(), fetchall(), commit().

### 10.2. handlers/commands/ — структура (сессия 15)

Пакет. Каждый файл — свой домен. __init__.py — реэкспорт всего.

| Файл | Что | Зависимости |
|---|---|---|
| __init__.py | Реэкспорт | из всех модулей |
| _legacy.py | handle_callback, handle_text, parse_date | 2047 строк |
| start.py | start, help_command, _help_text | modules.users, config |
| personal.py | personal_command, format_personal_summary, personal_keyboard | modules.personal |
| receipt.py | 5 receipt-функций | modules.parser, db |
| photos.py | 8 photo-функций | modules.objects, modules.tasks, db |
| crm.py | clients_command, deals_command, handle_crm_menu, _finalize_new_client | modules.crm, db |
| finance.py | finance_command, add_expense_command, finance_keyboard, format_finance_summary, show_finance_summary, format_money | modules.finance, modules.objects, db |
| objects.py | 7 objects-функций | modules.objects |
| tasks.py | 15 functions (tasks_command, task_*, build_calendar, auto_confirm_date) | modules.tasks, modules.objects, db |
| choose_expense.py | handle_choose_object, make_choose_keyboard, expense_category_keyboard, handle_category | modules.objects, modules.finance |
| document.py | handle_document (CSV/XLSX) | openpyxl, core.marketplaces |
| keyboards.py | main_menu_keyboard | telegram |
| add_menu.py | handle_add_menu | modules.objects |

### 10.3. core/ — бизнес-логика

| Файл | Что |
|---|---|
| spec.py | ЕДИНЫЙ СПРАВОЧНИК. WALL_NAMES, MATERIALS, типы. get_wall_name(n, total), get_total_walls(), set_total_walls() |
| rooms.py | комнаты |
| floors.py | этажи |
| geometry.py | расчёты (площади, углы) |
| room_estimate.py | смета комнаты. format_room_estimate(room_id) |
| floor_estimate.py | смета этажа |
| object_estimate.py | смета объекта |
| extra_works.py | отдельные работы |
| report_schedule.py | расписания автоотчётов |
| economics.py | экономика, маржа |
| marketplaces.py | импорт цен, format_price_comparison |
| elec_panels.py | ЭОМ: щиты, группы |
| elec_rules.py | правила ЭОМ |
| elec_routes.py | трассы ЭОМ |
| elec_prices.py | цены ЭОМ |
| plumbing_panels.py | сантехника: коллекторы |
| comms.py | коммуникации |
| export/pdf_export.py | PDF: щит, ЭОМ, сантехника, отчёт |
| db.py | обёртка (дубль корневого) |

### 10.4. interfaces/telegram/ — UI

| Файл | Что |
|---|---|
| rooms.py | 7638 строк — God Object. handle_rooms_callback + ~80 функций. Следующий для разбиения. |

### 10.5. modules/ — СТАРАЯ бизнес-логика (176 импортов)

Техдолг: перенести в core/ через шим.

| Файл | Что | Строк |
|---|---|---|
| backup_db.py | бэкап | 156 |
| calendar.py | календарь | 40 |
| crm.py | CRM | 221 |
| dashboard_link.py | ссылка | 20 |
| digest.py | дайджест | 224 |
| finance.py | add_expense, add_income, get_finance_summary, get_all_finance_summary, get_finance_by_period, get_finance_by_category | 117 |
| kpi.py | KPI | 184 |
| objects.py | create_object, get_all_objects, get_object, get_object_by_name, get_archived_objects, update_object | 136 |
| ocr.py | OCR чеков | 212 |
| parser.py | parse_message, parse_amount | 213 |
| personal.py | личные расходы | 78 |
| phone_utils.py | parse_phone, get_country_label | 84 |
| reports.py | get_summary_report, format_summary_report, get_closed_tasks_report... | 341 |
| tasks.py | create_task, close_task, get_active_tasks, get_tasks_by_object, get_archived_tasks, set_task_range | 416 |
| users.py | save_user, get_user, set_role, mark_onboarded, is_onboarded | 88 |

### 10.6. migrations/ — SQL

001-050+. Применяются при старте. ~110 таблиц:
- objects, rooms, floors, measurement_sessions, room_measures, openings, wall_niches, wall_corners, room_comms
- elec_panels, elec_panel_components, elec_groups, elec_routes
- plumbing_panels, plumbing_routes, plumbing_panel_points
- object_works, work_types, component_prices, price_imports
- users, tasks, task_history, photos, finance, receipt_items, clients, crm_deals, crm_activities
- system_settings

### 10.7. docs/

- HANDOFF.md — ЭТОТ ФАЙЛ. Читать первым.
- STATE.md — где мы сейчас.
- BO_MANIFEST.md — манифест (архитектура, БД, правила).
- WORKPLAN.md — план и техдолг.
- UX_PRINCIPLES.md — 18 принципов.
- STYLE_GUIDE.md — UI-правила.
- ARCHITECTURE_ESTIMATE.md — архитектура сметы.
- ROADMAP_FLEX.md — мультиплатформенность.

---

## 11. ЧАСТЫЕ ОПЕРАЦИИ — ШПАРГАЛКА

Перезапуск:
pkill -9 -f 'python bot.py' ; sleep 2 ; ./start_all.sh ; sleep 5 ; tail -5 bot_start.log

Трейсбек:
tail -40 bot_start.log

Поиск функции:
grep -n '^async def ИМЯ\|^def ИМЯ' <файл>

Поиск вызовов:
grep -rn 'ИМЯ' --include='*.py' . | grep -v pycache | grep -v .bak

Точные пробелы:
sed -n 'X,Yp' file | cat -A

Бэкап:
cp file file.bak_ИМЯ_$(date +%Y%m%d_%H%M%S)

Откат:
git checkout path/to/file.py

Проверка импорта:
python3 -c 'from handlers import commands; print(commands.Z)'

Установка пакета:
pip install --break-system-packages openpyxl

---

## 12. ПРИМЕР РАБОЧЕГО ПАТЧА

Шаг 1 — свежий grep: grep -n '^async def \|^def ' handlers/commands/_legacy.py
Шаг 2 — определить границы (например, handle_add_menu: 3241-3310).
Шаг 3 — бэкап.
Шаг 4 — Python-патч: вырезать блок, записать в новый файл, удалить из _legacy.
Шаг 5 — py_compile обоих.
Шаг 6 — импорт в _legacy.py и __init__.py.
Шаг 7 — перезапуск + тест + коммит.
Шаг 8 — если NameError: проверить, что ВСЕ зависимости импортированы в шапке нового модуля.

---

## 13. КОММИТЫ сессии 15 (все на GitHub)

41284a8 docs: add HANDOFF.md
2e7724b add_menu.py
339fc1d keyboards.py
0b3be5e docs(state)
f3e356c .xlsx via openpyxl
331faae document.py
69c8070 parse_amount fix
38f90b2 choose_expense.py
5783c9b + a0392b6 fix back button
8abdbac tasks.py
9535e3c objects.py
ea45932 + 6949b1b finance fixes
3ebf99d crm.py
1b227f9 photos.py
016d6ae receipt.py
8755410 personal fix
02ff371 start.py
aa7367b convert to package
2e9f1f7 docs(state)
b62a239 room_estimate_ fix
0eec77b 18 imports fix
adf899e get_wall_name 5+

---

## 14. ЧТО ДАЛЬШЕ — ЗАДАЧИ

### Первая (низкий риск, 30 мин)
utils.py — вынести parse_date из _legacy.py (3085-3240).
Проблема: _legacy.py:2538 — циклический импорт from handlers.commands import parse_date.
Фикс: в utils.py, заменить на from handlers.commands.utils import parse_date.

### Вторая (средний риск, 3-4 часа)
Резать handle_callback (2055) по доменам:
callbacks/estimates.py, objects.py, tasks.py, crm.py, prices.py, panels.py, plumbing.py, misc.py.

### Третья (средний риск, 3-4 часа)
Резать handle_text (975):
text/crm_flows.py, activity_flows.py, task_flows.py, estimate_flows.py, personal_flows.py, room_flows.py.

### Четвёртая (большой, 5-6 часов)
Резать rooms.py (7638) — walls, openings, comms, elec, plumbing, reports, core.

### Пятая (средний, 2-3 часа)
Универсальный приёмник файлов — handle_document:
CSV/XLSX прайс, счёт комплектации, счёт оплаты, накладная, чек.

### Шестая (большой, 4-5 часов)
modules/ -> core/ — 176 импортов через шим.

---

## 15. ТЕХНИЧЕСКИЕ ДЕТАЛИ

python-telegram-bot 20+ (async). Application, ContextTypes.DEFAULT_TYPE.
await query.answer() — ПЕРВЫМ в callback-хендлере.
await query.edit_message_text() — может падать Message is not modified. try/except.
filters.Document.ALL, filters.TEXT & ~filters.COMMAND.
Порядок add_handler — первый матч выигрывает.

SQLite: get_connection() из db.py. row_factory = sqlite3.Row. НЕ забывать conn.close().

Python 3.13: f-строки, match, walrus. UnboundLocalError — классика.

Replit: (venv), pip install --break-system-packages, VPN моргает -> процесс падает.

reportlab: PDF через SimpleDocTemplate.

openpyxl: load_workbook(path, data_only=True), ws.iter_rows(values_only=True).

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
3. Свежий grep -n.
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
Открывай точечно через sed -n 'X,Yp'.

---

Готов. Ты вооружён знанием. Погнали.
