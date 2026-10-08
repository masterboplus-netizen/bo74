-- 048_task_progress.sql
-- Дневник работ: ежедневные записи по задачам

CREATE TABLE IF NOT EXISTS task_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER,
    work_date DATE NOT NULL DEFAULT CURRENT_DATE,
    hours REAL,
    qty REAL,
    unit TEXT,
    description TEXT,
    raw_text TEXT,
    type TEXT DEFAULT 'work',
    source TEXT DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tp_task ON task_progress(task_id);
CREATE INDEX IF NOT EXISTS idx_tp_date ON task_progress(work_date);
CREATE INDEX IF NOT EXISTS idx_tp_user ON task_progress(user_id);

ALTER TABLE tasks ADD COLUMN progress_percent INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN planned_qty REAL;
ALTER TABLE tasks ADD COLUMN planned_unit TEXT;
