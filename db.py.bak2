"""База данных БО 7.5 — 27 таблиц"""
import sqlite3
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER UNIQUE, name TEXT, role TEXT DEFAULT 'guest',
        onboarded INTEGER DEFAULT 0,
        phone TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE, name TEXT NOT NULL, address TEXT,
        status TEXT DEFAULT 'active', budget INTEGER DEFAULT 0,
        execution_type TEXT DEFAULT 'self', created_by INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER, title TEXT NOT NULL, description TEXT,
        status TEXT DEFAULT 'open', priority TEXT DEFAULT 'medium',
        type TEXT DEFAULT 'direct', assigned_to INTEGER, deadline DATE,
        completed_at DATETIME, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (object_id) REFERENCES objects(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS finance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER, task_id INTEGER, category TEXT,
        amount INTEGER, type TEXT, date DATE, note TEXT,
        is_personal INTEGER DEFAULT 0,
        reimbursable INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (object_id) REFERENCES objects(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, object_id INTEGER, task_id INTEGER,
        title TEXT, event_date DATE, event_type TEXT DEFAULT 'task',
        priority TEXT DEFAULT 'medium', is_completed INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT,
        email TEXT, address TEXT, source TEXT, tg_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS crm_deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER,
        object_id INTEGER, status TEXT DEFAULT 'new', budget INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS crm_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER,
        user_id INTEGER, type TEXT, description TEXT, due_date DATE,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, completed_at DATETIME)''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER PRIMARY KEY,
        communication_style TEXT DEFAULT 'brief',
        thinking_style TEXT DEFAULT 'task_based',
        response_mode TEXT DEFAULT 'brief',
        target_language TEXT DEFAULT 'ru',
        emoji_usage INTEGER DEFAULT 1,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS marketplace_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        item_name TEXT, platform TEXT, price INTEGER, url TEXT,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS offline_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        command TEXT, data TEXT, status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP, synced_at DATETIME)''')

    c.execute('''CREATE TABLE IF NOT EXISTS report_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER,
        object_id INTEGER, template TEXT, frequency TEXT,
        weekday INTEGER, day_of_month INTEGER, hour INTEGER,
        minute INTEGER, last_sent DATETIME, next_send DATETIME,
        active INTEGER DEFAULT 1)''')

    c.execute('''CREATE TABLE IF NOT EXISTS task_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER,
        old_status TEXT, new_status TEXT, changed_by INTEGER,
        changed_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS finance_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, finance_id INTEGER,
        old_amount INTEGER, new_amount INTEGER,
        changed_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        task_id INTEGER, user_id INTEGER, text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        task_id INTEGER, file_id TEXT, caption TEXT,
        stage TEXT DEFAULT 'progress',
        uploaded_by INTEGER,
        taken_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        name TEXT, file_id TEXT, type TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        name TEXT, total INTEGER, status TEXT DEFAULT 'draft',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS estimate_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, estimate_id INTEGER,
        name TEXT, qty REAL, unit TEXT, price INTEGER, total INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT,
        category TEXT, note TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS kpi (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        object_id INTEGER, quality_score INTEGER DEFAULT 0,
        speed_score INTEGER DEFAULT 0, reliability_score INTEGER DEFAULT 0,
        total_score INTEGER DEFAULT 0,
        calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS report_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, blocks TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS action_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        action TEXT, entity TEXT, entity_id INTEGER, details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        task_id INTEGER, remind_at DATETIME, text TEXT,
        is_sent INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS checklists (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        task_id INTEGER, item TEXT, is_done INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER,
        user_id INTEGER, lat REAL, lon REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY, value TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_object ON tasks(object_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_finance_object ON finance(object_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_finance_date ON finance(date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON calendar_events(event_date)")

    # === МИГРАЦИИ для старых БД ===
    try:
        c.execute("ALTER TABLE users ADD COLUMN onboarded INTEGER DEFAULT 0")
        print("🔧 Миграция: добавлена колонка onboarded в users")
    except Exception:
        pass

    # Миграция photos: stage, uploaded_by, taken_at
    for col, sql in [
        ("stage", "ALTER TABLE photos ADD COLUMN stage TEXT DEFAULT 'progress'"),
        ("uploaded_by", "ALTER TABLE photos ADD COLUMN uploaded_by INTEGER"),
        ("taken_at", "ALTER TABLE photos ADD COLUMN taken_at DATETIME"),
    ]:
        try:
            c.execute(sql)
            print(f"🔧 Миграция photos: добавлена колонка {col}")
        except Exception:
            pass

    conn.commit()
    conn.close()
    print("✅ База БО 7.5 инициализирована (27 таблиц)")

if __name__ == '__main__':
    init_db()