-- 005: Каталог товаров + производство

CREATE TABLE IF NOT EXISTS catalog_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    category TEXT NOT NULL,
    subcategory TEXT,
    name TEXT NOT NULL,
    sku TEXT,
    description TEXT,
    price INTEGER,
    cost INTEGER,
    currency TEXT DEFAULT 'RUB',
    length REAL, width REAL, height REAL, depth REAL,
    weight REAL,
    fits_rooms TEXT,
    fits_styles TEXT,
    is_manufactured INTEGER DEFAULT 0,
    production_time_days INTEGER,
    photos TEXT,
    url TEXT,
    stock_qty INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_catalog_cat ON catalog_items(category);
CREATE INDEX IF NOT EXISTS idx_catalog_tenant ON catalog_items(tenant_id);
CREATE INDEX IF NOT EXISTS idx_catalog_sku ON catalog_items(sku);

-- Производство (свой цех)
CREATE TABLE IF NOT EXISTS production_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    catalog_item_id INTEGER,
    task_id INTEGER,
    object_id INTEGER,
    room_id INTEGER,
    qty INTEGER DEFAULT 1,
    start_date DATE,
    planned_end_date DATE,
    actual_end_date DATE,
    status TEXT DEFAULT 'planned',
    materials TEXT,
    cost INTEGER,
    price INTEGER,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_prod_tenant ON production_orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_prod_catalog ON production_orders(catalog_item_id);
CREATE INDEX IF NOT EXISTS idx_prod_object ON production_orders(object_id);

-- Подбор каталога к задаче
CREATE TABLE IF NOT EXISTS task_catalog_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    catalog_item_id INTEGER NOT NULL,
    match_type TEXT DEFAULT 'recommended',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, catalog_item_id)
);
CREATE INDEX IF NOT EXISTS idx_tcm_task ON task_catalog_matches(task_id);

-- Поставщики
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    category TEXT,
    city TEXT,
    address TEXT,
    delivery_days INTEGER,
    payment_terms TEXT,
    rating REAL DEFAULT 0,
    note TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Миграция: добавляем недостающие колонки в старую suppliers
ALTER TABLE suppliers ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE suppliers ADD COLUMN email TEXT;
ALTER TABLE suppliers ADD COLUMN city TEXT;
ALTER TABLE suppliers ADD COLUMN address TEXT;
ALTER TABLE suppliers ADD COLUMN delivery_days INTEGER;
ALTER TABLE suppliers ADD COLUMN payment_terms TEXT;
ALTER TABLE suppliers ADD COLUMN rating REAL DEFAULT 0;
ALTER TABLE suppliers ADD COLUMN is_active INTEGER DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_suppliers_tenant ON suppliers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_suppliers_cat ON suppliers(category);

-- Категории (дерево)
CREATE TABLE IF NOT EXISTS catalog_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    parent_id INTEGER,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    icon TEXT,
    order_num INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_cat_parent ON catalog_categories(parent_id);

-- Связь supplies с catalog
ALTER TABLE supplies ADD COLUMN catalog_item_id INTEGER;
ALTER TABLE supplies ADD COLUMN supplier_id INTEGER;
