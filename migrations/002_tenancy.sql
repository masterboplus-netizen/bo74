-- 002: Multi-tenancy
-- Добавляем tenant_id во все основные таблицы.
-- DEFAULT 1 — все существующие данные привязаны к "тенанту 1" (Andrey).

-- Таблица tenants (арендаторы/компании)
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    owner_user_id INTEGER,
    plan TEXT DEFAULT 'lite',
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Вставляем дефолтного тенанта
INSERT OR IGNORE INTO tenants (id, name, slug, plan)
VALUES (1, 'Master Bo (default)', 'master-bo', 'expert');

-- Добавляем tenant_id в основные таблицы
-- (безопасно: если колонка уже есть — SQLite выдаст ошибку, но мы её проглотим)
ALTER TABLE users ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE objects ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE tasks ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE finance ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE clients ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE crm_deals ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE crm_activities ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE photos ADD COLUMN tenant_id INTEGER DEFAULT 1;

-- Индексы для быстрого фильтра по tenant
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_objects_tenant ON objects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant_id);
