-- Система электроснабжения объекта
CREATE TABLE IF NOT EXISTS elec_supply (
    object_id INTEGER PRIMARY KEY,
    phase_count INTEGER DEFAULT 1,
    voltage INTEGER DEFAULT 220,
    input_breaker TEXT,
    meter_type TEXT,
    total_load_watt REAL,
    note TEXT,
    updated_at DATETIME
);

-- Группы электрики
CREATE TABLE IF NOT EXISTS elec_groups (
    id INTEGER PRIMARY KEY,
    object_id INTEGER,
    room_id INTEGER,
    name TEXT NOT NULL,
    phase INTEGER DEFAULT 1,
    breaker_type TEXT,
    breaker_curve TEXT DEFAULT 'C',
    cable_type TEXT,
    load_watt REAL,
    purpose TEXT,
    is_emergency INTEGER DEFAULT 0,
    diff_protection INTEGER DEFAULT 0,
    ip_class TEXT DEFAULT 'ip20',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Привязка точек к группам
ALTER TABLE room_comms ADD COLUMN group_id INTEGER;

-- Кабельный журнал
CREATE TABLE IF NOT EXISTS elec_cables (
    id INTEGER PRIMARY KEY,
    object_id INTEGER,
    group_id INTEGER,
    from_point TEXT,
    to_point TEXT,
    cable_type TEXT,
    length_m REAL,
    route_type TEXT,
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_groups_room ON elec_groups(room_id);
CREATE INDEX IF NOT EXISTS idx_groups_object ON elec_groups(object_id);
CREATE INDEX IF NOT EXISTS idx_cables_group ON elec_cables(group_id);
