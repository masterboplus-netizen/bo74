-- 012: Консьерж-сервис (присмотр за домами, пока хозяева в отъезде)

-- Регулярные задачи консьержа
CREATE TABLE IF NOT EXISTS concierge_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER NOT NULL,
    owner_id INTEGER,
    task_type TEXT NOT NULL,
    description TEXT,
    frequency TEXT DEFAULT 'once',
    next_date DATE,
    last_done DATE,
    assigned_to INTEGER,
    status TEXT DEFAULT 'active',
    note TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_concierge_object ON concierge_tasks(object_id);
CREATE INDEX IF NOT EXISTS idx_concierge_next ON concierge_tasks(next_date);
CREATE INDEX IF NOT EXISTS idx_concierge_assigned ON concierge_tasks(assigned_to);

-- Отчёты о выполнении (с фото)
CREATE TABLE IF NOT EXISTS concierge_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    photo_ids TEXT,
    note TEXT,
    performed_by INTEGER,
    performed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_crep_task ON concierge_reports(task_id);

-- Визиты (когда консьерж приходит в дом)
CREATE TABLE IF NOT EXISTS concierge_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER NOT NULL,
    visit_date DATETIME,
    visit_type TEXT,
    duration_min INTEGER,
    performed_by INTEGER,
    summary TEXT,
    photos TEXT,
    issues_found TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cvisits_object ON concierge_visits(object_id);
CREATE INDEX IF NOT EXISTS idx_cvisits_date ON concierge_visits(visit_date);

-- Тревоги / аварийные ситуации
CREATE TABLE IF NOT EXISTS concierge_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    description TEXT,
    source TEXT,
    photo_ids TEXT,
    status TEXT DEFAULT 'new',
    resolved_by INTEGER,
    resolved_at DATETIME,
    resolution TEXT,
    notified_owner INTEGER DEFAULT 0,
    notified_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_calert_object ON concierge_alerts(object_id);
CREATE INDEX IF NOT EXISTS idx_calert_status ON concierge_alerts(status);
CREATE INDEX IF NOT EXISTS idx_calert_severity ON concierge_alerts(severity);

-- Инструкции собственника (что делать, как делать)
CREATE TABLE IF NOT EXISTS concierge_instructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER NOT NULL,
    category TEXT,
    title TEXT,
    content TEXT,
    photo_ids TEXT,
    is_active INTEGER DEFAULT 1,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cinstr_object ON concierge_instructions(object_id);
