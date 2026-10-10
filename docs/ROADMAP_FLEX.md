# ROADMAP_FLEX.md — Гибкость архитектуры Бо

> Создано: 2026-10-10
> Причина: сейчас в коде зашито "4 стены". Нужно убрать.

## Проблема
Строитель работает с комнатами, у которых разное количество стен:
3 (Г-образная), 4 (обычная), 5 (П-образная), 6+ (сложные), круглые, эркеры, с колоннами.
Сейчас код предполагает 4 стены. Это ограничение.

## Где зашито "4"
### interfaces/telegram/rooms.py
- 467:  walls_ok = len(walls) >= 4
- 1153: next_step = step + 1 if step < 4 else 1
- 1160: if step >= 4:
- 1283: if step >= 4:
- 1490: if progress['walls_count'] >= 4:
- 2090: next_step = step + 1 if step < 4 else 1
- 2096: if step >= 4:
- 4601: walls_ok = len(walls) >= 4
- 4720: walls_ok = len(walls) >= 4
### core/spec.py
- WALL_NAMES — ровно 4
### core/measures.py
- get_walls_progress — предполагает 4

## План
1. UI: спросить "Сколько стен в комнате?" [3][4][5][6][Другое] → context.user_data['total_walls']
2. spec.py: get_wall_name(n, total) — универсальное имя
3. rooms.py: заменить 9 мест на total_walls
4. measures.py: get_walls_progress принимает total_walls

## Приоритет
Сейчас: НЕ трогаем (сначала функции).
Сессия 11+: делаем гибкость.
