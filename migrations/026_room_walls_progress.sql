-- 026_room_walls_progress.sql
-- Прогресс обхода стен + новые поля room_measures.

-- Прогресс в rooms
ALTER TABLE rooms ADD COLUMN walls_started_at DATETIME;
ALTER TABLE rooms ADD COLUMN walls_completed_at DATETIME;
ALTER TABLE rooms ADD COLUMN contour_check_passed INTEGER DEFAULT 0;

-- Новые поля в room_measures
ALTER TABLE room_measures ADD COLUMN order_num INTEGER;
ALTER TABLE room_measures ADD COLUMN has_hidden INTEGER DEFAULT 0;
ALTER TABLE room_measures ADD COLUMN hidden_note TEXT;
ALTER TABLE room_measures ADD COLUMN lean_angle REAL;
ALTER TABLE room_measures ADD COLUMN lean_direction REAL;
