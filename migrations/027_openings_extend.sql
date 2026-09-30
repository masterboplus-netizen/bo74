-- 027_openings_extend.sql
-- Расширение таблицы openings: типы дверей/окон, связи, флаги.

-- Добавляем новые поля (если их нет)
ALTER TABLE openings ADD COLUMN from_room_id INTEGER;
ALTER TABLE openings ADD COLUMN to_room_id INTEGER;
ALTER TABLE openings ADD COLUMN to_outside INTEGER DEFAULT 0;
ALTER TABLE openings ADD COLUMN is_main INTEGER DEFAULT 0;
ALTER TABLE openings ADD COLUMN vent_type TEXT;
ALTER TABLE openings ADD COLUMN door_kind TEXT;
