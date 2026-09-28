-- 003: Auth-identity, Audit-log, Files, Notifications

-- 1. Auth-identities (один юзер — много провайдеров: tg, email, phone)
CREATE TABLE IF NOT EXISTS auth_identities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    verified INTEGER DEFAULT 0,
    tenant_id INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_id)
);
CREATE INDEX IF NOT EXISTS idx_auth_user ON auth_identities(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_provider ON auth_identities(provider, provider_id);

-- 2. Audit-log (кто что делал)
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    old_data TEXT,
    new_data TEXT,
    ip TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

-- 3. Files (единый слой для фото/документов)
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_uuid TEXT UNIQUE NOT NULL,
    tg_file_id TEXT,
    url TEXT,
    local_path TEXT,
    original_name TEXT,
    size INTEGER,
    mime TEXT,
    uploaded_by INTEGER,
    tenant_id INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_files_tg ON files(tg_file_id);
CREATE INDEX IF NOT EXISTS idx_files_uuid ON files(file_uuid);

-- 4. Notification-queue (универсальный канал)
CREATE TABLE IF NOT EXISTS notification_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    channel TEXT DEFAULT 'telegram',
    title TEXT,
    body TEXT,
    payload TEXT,
    status TEXT DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    scheduled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sent_at DATETIME,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notif_status ON notification_queue(status);
CREATE INDEX IF NOT EXISTS idx_notif_sched ON notification_queue(scheduled_at);

-- 5. Subscriptions (тарифы — заготовка)
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    plan TEXT DEFAULT 'lite',
    status TEXT DEFAULT 'active',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    payment_provider TEXT,
    payment_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_subs_tenant ON subscriptions(tenant_id);

-- 6. Usage-metrics (учёт использования — заготовка)
CREATE TABLE IF NOT EXISTS usage_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    metric TEXT NOT NULL,
    value INTEGER DEFAULT 0,
    period TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, metric, period)
);
CREATE INDEX IF NOT EXISTS idx_usage_tenant ON usage_metrics(tenant_id);
