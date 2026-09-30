-- 023_wall_niches.sql
-- Ниши на стенах: несколько на одну стену, разные размеры низа/верха.

CREATE TABLE IF NOT EXISTS wall_niches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    measure_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    name TEXT,

    -- Положение на стене (в СМ)
    offset_x REAL,
    offset_y REAL,

    -- Размеры (низ и верх могут отличаться, в СМ)
    width_bottom REAL,
    width_top REAL,
    height REAL,
    depth_bottom REAL,
    depth_top REAL,

    -- Тип
    niche_type TEXT DEFAULT 'rect',  -- rect / arc / irregular

    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (measure_id) REFERENCES room_measures(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wall_niches_measure ON wall_niches(measure_id);
CREATE INDEX IF NOT EXISTS idx_wall_niches_room ON wall_niches(room_id);
