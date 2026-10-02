-- 032: Архитектурная подсветка + конструкции
-- Для фасадов, ландшафта, интерьера

-- АРХИТЕКТУРНАЯ ПОДСВЕТКА
CREATE TABLE IF NOT EXISTS lighting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER,
    room_id INTEGER,
    zone_type TEXT,          -- facade / land / interior
    light_type TEXT,         -- facade_spot / facade_linear / land_path / ...
    label TEXT,
    wall TEXT,
    offset_x REAL,
    offset_y REAL,
    height REAL,
    count INTEGER DEFAULT 1,
    power_w REAL,
    temperature TEXT,        -- warm / neutral / cold / rgb / tunable
    protection TEXT,         -- ip20 / ip44 / ip65 / ip67 / ip68
    control TEXT,            -- switch / dimmer / smart / dmx / sensor / timer
    voltage INTEGER,         -- 12 / 24 / 220
    beam_angle REAL,         -- угол свечения
    note TEXT,
    world_x REAL,
    world_y REAL,
    world_z REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES objects(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

CREATE INDEX IF NOT EXISTS idx_lighting_object ON lighting(object_id);
CREATE INDEX IF NOT EXISTS idx_lighting_room ON lighting(room_id);
CREATE INDEX IF NOT EXISTS idx_lighting_zone ON lighting(zone_type);

-- КОНСТРУКЦИИ (несущие и декоративные)
CREATE TABLE IF NOT EXISTS constructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER,
    room_id INTEGER,
    construction_type TEXT,   -- load_bearing_wall / column / beam / slab / arch / ...
    material TEXT,            -- concrete / brick / metal / wood / ...
    label TEXT,
    length REAL,
    width REAL,
    height REAL,
    diameter REAL,
    depth REAL,
    is_load_bearing INTEGER DEFAULT 0,
    load_capacity REAL,
    offset_x REAL,
    offset_y REAL,
    note TEXT,
    world_x REAL,
    world_y REAL,
    world_z REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES objects(id),
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

CREATE INDEX IF NOT EXISTS idx_constructions_object ON constructions(object_id);
CREATE INDEX IF NOT EXISTS idx_constructions_room ON constructions(room_id);
CREATE INDEX IF NOT EXISTS idx_constructions_type ON constructions(construction_type);
