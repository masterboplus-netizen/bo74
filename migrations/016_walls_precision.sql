-- 016: Кривизна стен, ниши, примыкания

-- Отклонения стен (кривизна)
ALTER TABLE room_measures ADD COLUMN deviation_plus REAL;
ALTER TABLE room_measures ADD COLUMN deviation_minus REAL;
ALTER TABLE room_measures ADD COLUMN is_wavy INTEGER DEFAULT 0;
ALTER TABLE room_measures ADD COLUMN wavy_note TEXT;
ALTER TABLE room_measures ADD COLUMN measured_top REAL;
ALTER TABLE room_measures ADD COLUMN measured_middle REAL;
ALTER TABLE room_measures ADD COLUMN measured_bottom REAL;

-- Ниши
CREATE TABLE IF NOT EXISTS niches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    room_id INTEGER NOT NULL,
    wall TEXT,
    label TEXT,
    width REAL,
    height REAL,
    depth REAL,
    angle_left REAL DEFAULT 90,
    angle_right REAL DEFAULT 90,
    angle_top REAL DEFAULT 90,
    offset_x REAL,
    offset_y REAL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_niches_room ON niches(room_id);

-- Примыкания (углы между стенами)
CREATE TABLE IF NOT EXISTS wall_junctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    room_id INTEGER NOT NULL,
    wall_a TEXT,
    wall_b TEXT,
    angle REAL DEFAULT 90,
    gap_top REAL,
    gap_bottom REAL,
    is_straight INTEGER DEFAULT 1,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_junctions_room ON wall_junctions(room_id);
