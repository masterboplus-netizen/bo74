# WORKPLAN — план и техдолг

> Обновлён: 2026-10-15 (сессия 17).

## ТЕХДОЛГ

### P1. _legacy.py (~200 строк)
- Fallback → text/fallback.py
- parse_message → text/parser.py
- Уборка

### P2. rooms.py (7638 строк)
God Object. Разбить: rooms/, elec/, plumbing/, measure/. Высокий риск.

### P3. modules/ → core/
176 импортов через шим.

### P4. Универсальный приёмник файлов
handle_document: любые файлы.

### P5. Хераборина редизайн
Графики, аналитика, фильтры.

### P6. Единицы измерения (м vs см) — check_object_vs_comms
**Проблема:** `length/height/offset_y` в `room_objects` / `comms` — REAL, без указания единиц. В `core/comms.py:122-125` — отображается в «см», но `room_objects` может хранить в метрах или см (разные источники: каталог, ручной ввод, импорт).
**Симптом:** `check_object_vs_comms` (core/conflicts.py:25) сравнивает `comm_y` (см?) с `obj_y1` (м?) — ложные конфликты.
**Решение (сессия 21+):** 1) Определить стандарт (см). 2) Миграция: `unit TEXT DEFAULT 'cm'` в room_objects/comms. 3) Нормализация при записи. 4) `_to_cm()` при чтении.
**Отложено:** сессия 20, требует архитектурного решения.

## СДЕЛАНО (сессия 17)

- callbacks/objects, reports, misc, personal
- text/objects, tasks, finances, personal, crm, misc, rooms
- restore menu_reports
- _legacy.py: 1625 → 656 (−60%)
- AST/grep инструменты в правилах
