-- 024_wall_lean.sql
-- Наклоны стен: стена может быть не вертикальна.

CREATE TABLE IF NOT EXISTS wall_lean (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    measure_id INTEGER NOT NULL UNIQUE,
    room_id INTEGER NOT NULL,

    -- Наклон от вертикали
    lean_angle REAL,          -- угол (°)
    lean_direction REAL,      -- направление (0=вправо, 90=вверх, 180=влево, 270=вниз)
    offset_top_x REAL,        -- смещение верха по X (СМ)
    offset_top_y REAL,        -- смещение верха по Y (СМ)

    -- Скручивание (если стена изогнута по вертикали)
    twist_angle REAL,

    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (measure_id) REFERENCES room_measures(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wall_lean_measure ON wall_lean(measure_id);
CREATE INDEX IF NOT EXISTS idx_wall_lean_room ON wall_lean(room_id);
