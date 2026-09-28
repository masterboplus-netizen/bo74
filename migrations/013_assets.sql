-- 013: Аренда инструмента, техники, оборудования

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    asset_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    sku TEXT,
    serial_number TEXT,
    inventory_number TEXT,
    purchase_price INTEGER,
    current_value INTEGER,
    daily_rate INTEGER,
    weekly_rate INTEGER,
    monthly_rate INTEGER,
    deposit INTEGER,
    ownership TEXT DEFAULT 'own',
    status TEXT DEFAULT 'available',
    condition TEXT DEFAULT 'good',
    photos TEXT,
    purchased_at DATE,
    warranty_until DATE,
    note TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_tenant ON assets(tenant_id);

-- Заказы аренды (сдача/получение)
CREATE TABLE IF NOT EXISTS rental_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    asset_id INTEGER,
    direction TEXT NOT NULL,
    counterparty_id INTEGER,
    start_date DATE,
    end_date DATE,
    actual_return_date DATE,
    rate INTEGER,
    total INTEGER,
    deposit INTEGER,
    status TEXT DEFAULT 'active',
    condition_out TEXT,
    condition_in TEXT,
    photos_out TEXT,
    photos_in TEXT,
    note TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rorders_asset ON rental_orders(asset_id);
CREATE INDEX IF NOT EXISTS idx_rorders_status ON rental_orders(status);
CREATE INDEX IF NOT EXISTS idx_rorders_direction ON rental_orders(direction);
CREATE INDEX IF NOT EXISTS idx_rorders_counterparty ON rental_orders(counterparty_id);

-- История использования актива
CREATE TABLE IF NOT EXISTS asset_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    order_id INTEGER,
    event TEXT,
    event_date DATE,
    user_id INTEGER,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_assetlog_asset ON asset_usage_log(asset_id);
CREATE INDEX IF NOT EXISTS idx_assetlog_event ON asset_usage_log(event);
