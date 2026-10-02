-- 033: Фасад + Крыша
-- Для домов, коттеджей, многоэтажек

-- ФАСАД
CREATE TABLE IF NOT EXISTS facade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER NOT NULL,
    side TEXT,                -- north / south / east / west / front / back
    label TEXT,
    area_sqm REAL,
    height REAL,
    length REAL,
    material TEXT,
    has_insulation INTEGER DEFAULT 0,
    insulation_thickness REAL,
    has_lighting INTEGER DEFAULT 0,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES objects(id)
);

CREATE INDEX IF NOT EXISTS idx_facade_object ON facade(object_id);
CREATE INDEX IF NOT EXISTS idx_facade_side ON facade(side);

-- КРЫША
CREATE TABLE IF NOT EXISTS roof (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER NOT NULL,
    roof_type TEXT,           -- flat / gable / hip / mansard / ...
    covering TEXT,            -- metal_tile / flexible_tile / ...
    area_sqm REAL,
    height REAL,
    angle_deg REAL,
    has_mansard INTEGER DEFAULT 0,
    has_drainage INTEGER DEFAULT 0,
    has_lighting INTEGER DEFAULT 0,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES objects(id)
);

CREATE INDEX IF NOT EXISTS idx_roof_object ON roof(object_id);
CREATE INDEX IF NOT EXISTS idx_roof_type ON roof(roof_type);

-- БАЛКОНЫ И ВЕРАНДЫ (дополнительные параметры комнат)
ALTER TABLE rooms ADD COLUMN balcony_type TEXT;       -- open / closed / glazed
ALTER TABLE rooms ADD COLUMN balcony_railing TEXT;    -- metal / concrete / glass / wood
ALTER TABLE rooms ADD COLUMN balcony_railing_height REAL;
ALTER TABLE rooms ADD COLUMN is_heated INTEGER DEFAULT 0;  -- для веранд/террас

-- ЭКСПОРТЫ
CREATE TABLE IF NOT EXISTS room_exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER,
    object_id INTEGER,
    format TEXT,
    file_path TEXT,
    file_size INTEGER,
    session_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (room_id) REFERENCES rooms(id),
    FOREIGN KEY (object_id) REFERENCES objects(id)
);

CREATE INDEX IF NOT EXISTS idx_exports_room ON room_exports(room_id);
CREATE INDEX IF NOT EXISTS idx_exports_object ON room_exports(object_id);

-- ТЕСТОВЫЕ ДАННЫЕ
ALTER TABLE objects ADD COLUMN is_test INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN is_test INTEGER DEFAULT 0;
ALTER TABLE finance ADD COLUMN is_test INTEGER DEFAULT 0;
ALTER TABLE photos ADD COLUMN is_test INTEGER DEFAULT 0;
ALTER TABLE clients ADD COLUMN is_test INTEGER DEFAULT 0;
