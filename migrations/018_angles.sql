-- 018: Углы и закругления

ALTER TABLE room_measures ADD COLUMN has_rounded INTEGER DEFAULT 0;
ALTER TABLE room_measures ADD COLUMN radius REAL;
ALTER TABLE room_measures ADD COLUMN rounded_corner TEXT;

ALTER TABLE room_measures ADD COLUMN angle_value REAL;
ALTER TABLE room_measures ADD COLUMN angle_method TEXT;
ALTER TABLE room_measures ADD COLUMN angle_diagonal_cm REAL;

ALTER TABLE room_measures ADD COLUMN wall_pos TEXT;
