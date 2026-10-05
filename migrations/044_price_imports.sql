-- Миграция 044: Импорт цен (маркетплейсы, CSV)
CREATE TABLE IF NOT EXISTS price_imports (
    id INTEGER PRIMARY KEY,
    object_id INTEGER,
    source TEXT,
    rows_count INTEGER,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_pi_object ON price_imports(object_id);
CREATE INDEX IF NOT EXISTS idx_pi_source ON price_imports(source);
