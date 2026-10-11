-- Отдельные (внеплановые) работы
CREATE TABLE IF NOT EXISTS extra_works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    qty REAL DEFAULT 1,
    unit TEXT DEFAULT 'шт',
    price REAL DEFAULT 0,
    total REAL DEFAULT 0,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (object_id) REFERENCES objects(id)
);
CREATE INDEX IF NOT EXISTS idx_extra_works_object ON extra_works(object_id);
