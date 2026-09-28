-- 006: Маркетплейс (биржа мастеров)

-- Расширения пользователей (мастера)
ALTER TABLE users ADD COLUMN is_contractor INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN skills TEXT;
ALTER TABLE users ADD COLUMN rating REAL DEFAULT 0;
ALTER TABLE users ADD COLUMN city TEXT;
ALTER TABLE users ADD COLUMN available INTEGER DEFAULT 1;
ALTER TABLE users ADD COLUMN hourly_rate INTEGER;
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN portfolio_url TEXT;
ALTER TABLE users ADD COLUMN shifts_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN hours_total REAL DEFAULT 0;
ALTER TABLE users ADD COLUMN earned_total INTEGER DEFAULT 0;

-- Публикации задач на бирже
CREATE TABLE IF NOT EXISTS market_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    object_id INTEGER,
    room_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    title TEXT,
    description TEXT,
    price INTEGER,
    deadline DATE,
    skills_required TEXT,
    city TEXT,
    is_active INTEGER DEFAULT 1,
    published_by INTEGER,
    published_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME
);
CREATE INDEX IF NOT EXISTS idx_listings_task ON market_listings(task_id);
CREATE INDEX IF NOT EXISTS idx_listings_active ON market_listings(is_active);
CREATE INDEX IF NOT EXISTS idx_listings_city ON market_listings(city);

-- Отклики мастеров на публикации
CREATE TABLE IF NOT EXISTS market_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    contractor_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    message TEXT,
    proposed_price INTEGER,
    proposed_deadline DATE,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    decided_at DATETIME
);
CREATE INDEX IF NOT EXISTS idx_apps_listing ON market_applications(listing_id);
CREATE INDEX IF NOT EXISTS idx_apps_contractor ON market_applications(contractor_id);
CREATE INDEX IF NOT EXISTS idx_apps_status ON market_applications(status);

-- Сделки (эскроу-логика)
CREATE TABLE IF NOT EXISTS market_deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER,
    application_id INTEGER,
    contractor_id INTEGER,
    client_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    agreed_price INTEGER,
    agreed_deadline DATE,
    status TEXT DEFAULT 'active',
    started_at DATETIME,
    completed_at DATETIME,
    paid_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_deals_contractor ON market_deals(contractor_id);
CREATE INDEX IF NOT EXISTS idx_deals_status ON market_deals(status);

-- Отзывы и рейтинг
CREATE TABLE IF NOT EXISTS market_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER NOT NULL,
    from_user_id INTEGER,
    to_user_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    rating INTEGER,
    text TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reviews_to ON market_reviews(to_user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_deal ON market_reviews(deal_id);
