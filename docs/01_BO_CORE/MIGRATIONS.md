# MIGRATIONS.md — Миграции БД

> Все миграции применяются при старте бота. Идемпотентны.

---

## СПИСОК МИГРАЦИЙ

### 019_room_type.sql
Добавляет `room_type` в rooms.

### 020_room_height_points.sql
Добавляет height_bottom, height_middle, height_top в rooms.

### 021_openings.sql
Создаёт таблицу openings.

### 022_measure_method.sql
Добавляет `measure_method` в rooms.

### 023_wall_niches.sql
Создаёт таблицу wall_niches.

### 024_wall_lean.sql
Создаёт таблицу wall_lean.

### 025_wall_corners.sql
Создаёт таблицу wall_corners.

### 026_room_walls_progress.sql
Добавляет walls_started_at, walls_completed_at в rooms.

### 027_openings_extend.sql
Расширяет openings (from_room_id, to_room_id, vent_type, door_kind).

### 028_measurement_sessions.sql (НОВОЕ)
Создаёт таблицу measurement_sessions:
id, room_id, session_type, session_label, session_date, created_by, notes, is_active, created_at.
Индекс: idx_sessions_room ON (room_id).

### 029_session_id.sql (НОВОЕ)
Добавляет `session_id` в:
- room_measures
- openings
- wall_niches
- room_comms

### 030_material.sql (НОВОЕ)
Добавляет `material` в room_measures.

### 031_coords.sql (НОВОЕ)
Добавляет координаты в room_measures:
- start_x, start_y, end_x, end_y
- start_z, end_z

Добавляет в openings, wall_niches, room_comms:
- world_x, world_y, world_z

### 032_room_exports.sql (НОВОЕ)
Создаёт таблицу room_exports:
id, room_id, format, file_path, file_size, created_at, created_by.

### 033_work_stages.sql (НОВОЕ)
Создаёт таблицы:
- work_stages (id, code, name, description, order_num, typical_days)
- work_types (id, code, name, category, unit, tools, materials, norm_hours, norm_price)
- object_stages (id, object_id, stage_id, status, started_at, completed_at, note)
- object_works (id, object_id, room_id, work_type_id, stage_id, qty, unit, price, total, status, assigned_to, started_at, completed_at, note)

### 034_object_type.sql (НОВОЕ)
Добавляет `object_type` в objects.

### 035_is_test.sql (НОВОЕ)
Добавляет `is_test` в:
- objects
- tasks
- finance
- photos
- clients

---

## ПРАВИЛА

1. Каждая миграция идемпотентна (try/except).
2. Нумерация — сквозная.
3. Название — `NNN_краткое_описание.sql`.
4. Применяются в порядке номеров.
5. Бэкап БД перед миграциями.

---

## КАК ПРИМЕНИТЬ

Автоматически — при старте бота `init_db()`.

Вручную — `sqlite3 bo72.db < migrations/NNN_name.sql`.

---

*Конец MIGRATIONS.md*
