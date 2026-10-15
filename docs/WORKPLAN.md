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

## СДЕЛАНО (сессия 17)

- callbacks/objects, reports, misc, personal
- text/objects, tasks, finances, personal, crm, misc, rooms
- restore menu_reports
- _legacy.py: 1625 → 656 (−60%)
- AST/grep инструменты в правилах
