-- 025_wall_corners.sql
-- Углы между стенами: 4 угла в комнате (между стенами 1-2, 2-3, 3-4, 4-1).

CREATE TABLE IF NOT EXISTS wall_corners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    corner_number INTEGER NOT NULL,     -- 1/2/3/4

    -- Тип угла
    corner_type TEXT DEFAULT 'straight', -- straight / rounded / angled / irregular
    angle_value REAL,                    -- угол (°)

    -- Радиус (если закруглён)
    radius REAL,                         -- радиус в СМ
    radius_note TEXT,

    -- Отклонения низа/верха
    deviation_bottom REAL,
    deviation_top REAL,

    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_wall_corners_room ON wall_corners(room_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_wall_corners_unique ON wall_corners(room_id, corner_number);
