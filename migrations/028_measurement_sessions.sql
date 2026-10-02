-- 028: Сессии замеров
-- Один объект — много версий замеров (initial, furniture, final...)

CREATE TABLE IF NOT EXISTS measurement_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    session_type TEXT NOT NULL DEFAULT 'initial',
    session_label TEXT,
    session_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    notes TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (room_id) REFERENCES rooms(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_room ON measurement_sessions(room_id);
CREATE INDEX IF NOT EXISTS idx_sessions_type ON measurement_sessions(session_type);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON measurement_sessions(is_active);
