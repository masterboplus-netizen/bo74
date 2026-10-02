-- 031: Этажи + расширенный room_type
-- Для многоэтажных зданий

CREATE TABLE IF NOT EXISTS floors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER NOT NULL,
    floor_number INTEGER NOT NULL,
    floor_name TEXT,
    area_sqm REAL,
    height_avg REAL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES objects(id)
);

CREATE INDEX IF NOT EXISTS idx_floors_object ON floors(object_id);
CREATE INDEX IF NOT EXISTS idx_floors_number ON floors(floor_number);

-- Привязка комнат к этажам
ALTER TABLE rooms ADD COLUMN floor_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_rooms_floor ON rooms(floor_id);

-- Расширенный object_type (голые стены / готовый ремонт / косметика / частотные)
ALTER TABLE objects ADD COLUMN object_type TEXT DEFAULT 'apartment';

-- Расширенный room_type (все типы комнат)
ALTER TABLE rooms ADD COLUMN room_subtype TEXT;
