CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER UNIQUE, name TEXT, role TEXT DEFAULT 'guest',
        phone TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, onboarded INTEGER DEFAULT 0, username TEXT);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE, name TEXT NOT NULL, address TEXT,
        status TEXT DEFAULT 'active', budget INTEGER DEFAULT 0,
        execution_type TEXT DEFAULT 'self', created_by INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER, title TEXT NOT NULL, description TEXT,
        status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium',
        type TEXT DEFAULT 'direct', assigned_to INTEGER, deadline DATE,
        completed_at DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, deadline_start DATE, deadline_end DATE,
        FOREIGN KEY (object_id) REFERENCES objects(id));
CREATE TABLE finance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER, task_id INTEGER, category TEXT,
        amount INTEGER, type TEXT, date DATE, note TEXT,
        is_personal INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, reimbursable INTEGER DEFAULT 0,
        FOREIGN KEY (object_id) REFERENCES objects(id));
CREATE TABLE calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, object_id INTEGER, task_id INTEGER,
        title TEXT, event_date DATE, event_type TEXT DEFAULT 'task',
        priority TEXT DEFAULT 'medium', is_completed INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT,
        email TEXT, address TEXT, source TEXT, tg_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE crm_deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER,
        object_id INTEGER, status TEXT DEFAULT 'new', budget INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE crm_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER,
        user_id INTEGER, type TEXT, description TEXT, due_date DATE,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, completed_at DATETIME);
CREATE TABLE user_preferences (
        user_id INTEGER PRIMARY KEY,
        communication_style TEXT DEFAULT 'brief',
        thinking_style TEXT DEFAULT 'task_based',
        response_mode TEXT DEFAULT 'brief',
        target_language TEXT DEFAULT 'ru',
        emoji_usage INTEGER DEFAULT 1,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE marketplace_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        item_name TEXT, platform TEXT, price INTEGER, url TEXT,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE offline_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        command TEXT, data TEXT, status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, synced_at DATETIME);
CREATE TABLE report_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER,
        object_id INTEGER, template TEXT, frequency TEXT,
        weekday INTEGER, day_of_month INTEGER, hour INTEGER,
        minute INTEGER, last_sent DATETIME, next_send DATETIME,
        active INTEGER DEFAULT 1);
CREATE TABLE task_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER,
        old_status TEXT, new_status TEXT, changed_by INTEGER,
        changed_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE finance_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, finance_id INTEGER,
        old_amount INTEGER, new_amount INTEGER,
        changed_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        task_id INTEGER, user_id INTEGER, text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        task_id INTEGER, file_id TEXT, caption TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, stage TEXT DEFAULT 'progress', uploaded_by INTEGER, taken_at DATETIME);
CREATE TABLE documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        name TEXT, file_id TEXT, type TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        name TEXT, total INTEGER, status TEXT DEFAULT 'draft',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE estimate_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, estimate_id INTEGER,
        name TEXT, qty REAL, unit TEXT, price INTEGER, total INTEGER);
CREATE TABLE suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT,
        category TEXT, note TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE kpi (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        object_id INTEGER, quality_score INTEGER DEFAULT 0,
        speed_score INTEGER DEFAULT 0, reliability_score INTEGER DEFAULT 0,
        total_score INTEGER DEFAULT 0,
        calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE report_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, blocks TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE action_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        action TEXT, entity TEXT, entity_id INTEGER, details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        task_id INTEGER, remind_at DATETIME, text TEXT,
        is_sent INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE checklists (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        task_id INTEGER, item TEXT, is_done INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        user_id INTEGER, lat REAL, lon REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE system_settings (
        key TEXT PRIMARY KEY, value TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX idx_tasks_object ON tasks(object_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_finance_object ON finance(object_id);
CREATE INDEX idx_finance_date ON finance(date);
CREATE INDEX idx_events_date ON calendar_events(event_date);
CREATE TABLE digest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    digest_type TEXT,
    sent_at DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(digest_type, sent_at)
);
CREATE TABLE receipt_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finance_id INTEGER,
        object_id INTEGER,
        name TEXT,
        qty REAL,
        unit TEXT,
        price REAL,
        total REAL,
        is_personal INTEGER DEFAULT 0,
        receipt_date DATE,
        shop TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
