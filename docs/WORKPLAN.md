# WORKPLAN — план и техдолг

> Обновлён: 2026-10-15 (сессия 17).

## ТЕХДОЛГ

### P1. _legacy.py (~200 строк)
- Fallback → text/fallback.py
- parse_message → text/parser.py
- Уборка

### P2. rooms.py (7638 строк) — ПЛАН (сессия 20: аудит)
God Object. Разбить на пакеты:
- `rooms/walls.py` — обход стен (~2000 строк). **СТАРТ: сессия 21.**
- `rooms/comm.py` — коммуникации (~300).
- `rooms/floors.py` — помещения (~300).
- `rooms/elec.py` — щиты, группы, кабели (~500).
- `rooms/openings.py` — проёмы (~300).
- `rooms/reports.py` — отчёты, экспорт (~300).
- `rooms/measure.py` — замеры (~300).

**Мёртвые функции (удалить в сессии 21):**
- `_after_niches` (1697)
- `_show_niche_top_width_from_update` (2181)

**Живые (не трогать):**
- `handle_measure_input` (5126) — вызывается из `_legacy.py:301`.

**Оценка:** 25–35 часов (10–15 сессий). Высокий риск.

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
