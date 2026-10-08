-- 047_objects_engineering.sql
-- Расширение модели: типы объектов, виды работ, наружные сети

-- 1. objects — тип объекта + вид работ + корень floors
ALTER TABLE objects ADD COLUMN object_kind TEXT DEFAULT 'residential';
ALTER TABLE objects ADD COLUMN work_kind TEXT DEFAULT 'construction';
ALTER TABLE objects ADD COLUMN root_floor_id INTEGER DEFAULT NULL;

-- 2. object_networks — наружные инженерные сети между строениями
CREATE TABLE IF NOT EXISTS object_networks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER NOT NULL,
    system_type TEXT NOT NULL,
    subtype TEXT,
    from_floor_id INTEGER,
    from_point_id INTEGER,
    to_floor_id INTEGER,
    to_point_id INTEGER,
    length_m REAL,
    pipe_type TEXT,
    diameter_mm INTEGER,
    voltage INTEGER,
    cable_type TEXT,
    depth_m REAL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_objnet_object ON object_networks(object_id);
CREATE INDEX IF NOT EXISTS idx_objnet_system ON object_networks(system_type);
CREATE INDEX IF NOT EXISTS idx_objnet_from ON object_networks(from_floor_id);
CREATE INDEX IF NOT EXISTS idx_objnet_to ON object_networks(to_floor_id);
