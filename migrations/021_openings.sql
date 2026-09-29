-- 021_openings.sql — проёмы (окна, двери, арки)
-- Хранит все проёмы в комнате: на какой стене, где, размеры

CREATE TABLE IF NOT EXISTS openings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    opening_type TEXT NOT NULL,       -- window / door / opening (арка)
    wall_pos TEXT,                    -- напротив / слева / справа / у входа
    offset_x REAL,                    -- смещение от угла (см)
    width REAL NOT NULL,              -- ширина (см)
    height REAL NOT NULL,             -- высота (см)
    sill_height REAL,                 -- высота подоконника от пола (см)
    depth REAL,                       -- глубина откоса (см)
    note TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_openings_room ON openings(room_id);
CREATE INDEX IF NOT EXISTS idx_openings_type ON openings(opening_type);
