-- 017: Последовательность работ, финишные зоны, решения, кейсы

-- === ЗАВИСИМОСТИ ЗАДАЧ ===
ALTER TABLE tasks ADD COLUMN depends_on TEXT;
ALTER TABLE tasks ADD COLUMN blocks TEXT;
ALTER TABLE tasks ADD COLUMN access_difficulty INTEGER DEFAULT 1;
ALTER TABLE tasks ADD COLUMN must_be_before_finish INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_tasks_depends ON tasks(depends_on);

-- === ФИНИШНЫЕ ЗОНЫ (нельзя трогать после финиша) ===
CREATE TABLE IF NOT EXISTS final_zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    room_id INTEGER,
    zone_type TEXT,
    wall TEXT,
    offset_x REAL,
    offset_y REAL,
    length REAL,
    width REAL,
    finished_at DATE,
    is_locked INTEGER DEFAULT 0,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_finalzones_room ON final_zones(room_id);
CREATE INDEX IF NOT EXISTS idx_finalzones_locked ON final_zones(is_locked);

-- === ОТКРЫТЫЕ РЕШЕНИЯ ===
CREATE TABLE IF NOT EXISTS pending_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER,
    room_id INTEGER,
    title TEXT NOT NULL,
    options TEXT,
    decision TEXT,
    decided_by INTEGER,
    decided_at DATETIME,
    deadline DATE,
    blocks_tasks TEXT,
    status TEXT DEFAULT 'open',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_decisions_obj ON pending_decisions(object_id);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON pending_decisions(status);

-- === КЕЙСЫ (база знаний) ===
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER,
    title TEXT NOT NULL,
    problem TEXT,
    solution TEXT,
    result TEXT,
    photos TEXT,
    tags TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cases_object ON cases(object_id);
CREATE INDEX IF NOT EXISTS idx_cases_tags ON cases(tags);
