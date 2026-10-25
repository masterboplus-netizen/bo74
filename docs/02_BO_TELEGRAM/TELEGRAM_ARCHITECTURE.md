# TELEGRAM_ARCHITECTURE — Правила роутинга бота

> **Дата:** 2026-10-25
> **Проект:** Бо 8.1 (Интерфейс Telegram)

## 1. ТРИ УРОВНЯ ОБРАБОТКИ CALLBACK-ОВ

Callback-и в Бо обрабатываются в ТРЁХ местах (от самого специфичного к общему):

### Уровень 1: bot.py — прямые CallbackQueryHandler
app.add_handler(CallbackQueryHandler(handler, pattern="^prefix"))
Здесь живут: recognize_receipt, receipt_*, photofilt_*, cat_*, task_*, photo_*, menu_add, add_*, choose_obj_*, confirmdate_*.
*(Парсится сканером map_scan.py).*

### Уровень 2: _legacy.py -> callbacks/*.py
handle_callback -> _try_<domain>_cb(data, query, context).
Роутеры: tasks, estimates, kpi, finance, objects, reports, misc, personal.

### Уровень 3: _legacy.py -> text/*.py
handle_text -> try_handle(update, context, text).
Домены: fallback, crm, finances, misc, objects, personal, rooms, tasks.

## 2. ПРАВИЛО ПОИСКА РОУТЕРА

- Прежде чем искать роутер — обнови карту: python3 tools/map_scan.py > docs/CODE_MAP_AUTO.md
- Если префикса нет в карте — возможно, он в bot.py.
- НЕ патчить роутеры вслепую — сначала grep по всем трём уровням.

## 3. ПРАВИЛА РАБОТЫ С ФАЙЛАМИ БОТА

- bot.py — паттерн роутера (НЕ трогать без нужды).
- interfaces/telegram/rooms.py — UI комнат (God Object, в процессе разбиения).
- handlers/commands.py — команды.
- _safe_edit — универсальный edit (photo -> caption, text -> text, fallback -> delete+send).

**Конец TELEGRAM_ARCHITECTURE.md**