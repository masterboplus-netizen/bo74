-- Миграция 043: Работы объекта (расчёт стоимости работ)
CREATE TABLE IF NOT EXISTS object_works (
    id INTEGER PRIMARY KEY,
    object_id INTEGER NOT NULL,
    room_id INTEGER,
    group_id INTEGER,
    work_type TEXT,
    work_label TEXT,
    qty REAL,
    unit TEXT,
    price_unit REAL,
    total REAL,
    is_manual INTEGER DEFAULT 0,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ow_object ON object_works(object_id);
CREATE INDEX IF NOT EXISTS idx_ow_room ON object_works(room_id);
CREATE INDEX IF NOT EXISTS idx_ow_group ON object_works(group_id);
