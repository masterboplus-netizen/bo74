-- 010: Аренда и продажа недвижимости

-- Листинги аренды/продажи
CREATE TABLE IF NOT EXISTS property_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER,
    listing_type TEXT NOT NULL,
    price INTEGER,
    currency TEXT DEFAULT 'RUB',
    price_per_sqm INTEGER,
    area_total REAL,
    rooms_count INTEGER,
    floor INTEGER,
    floors_total INTEGER,
    description TEXT,
    photos TEXT,
    is_active INTEGER DEFAULT 1,
    published_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_by INTEGER,
    closed_at DATETIME,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_plist_type ON property_listings(listing_type);
CREATE INDEX IF NOT EXISTS idx_plist_object ON property_listings(object_id);
CREATE INDEX IF NOT EXISTS idx_plist_active ON property_listings(is_active);

-- Показы (встречи с клиентами)
CREATE TABLE IF NOT EXISTS property_shows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    client_id INTEGER,
    agent_id INTEGER,
    show_date DATETIME,
    feedback TEXT,
    interest_level TEXT,
    next_step TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_shows_listing ON property_shows(listing_id);
CREATE INDEX IF NOT EXISTS idx_shows_client ON property_shows(client_id);

-- Аренда (активные договоры)
CREATE TABLE IF NOT EXISTS property_rentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER,
    object_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    renter_id INTEGER,
    contract_id INTEGER,
    monthly_payment INTEGER,
    deposit INTEGER,
    start_date DATE,
    end_date DATE,
    utilities_included INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rentals_object ON property_rentals(object_id);
CREATE INDEX IF NOT EXISTS idx_rentals_status ON property_rentals(status);

-- Продажи (закрытые сделки)
CREATE TABLE IF NOT EXISTS property_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER,
    object_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    buyer_id INTEGER,
    seller_id INTEGER,
    agent_id INTEGER,
    sale_price INTEGER,
    commission INTEGER,
    contract_id INTEGER,
    deal_date DATE,
    status TEXT DEFAULT 'in_progress',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sales_object ON property_sales(object_id);
CREATE INDEX IF NOT EXISTS idx_sales_status ON property_sales(status);

-- Воронка клиентов (интерес → показ → сделка)
CREATE TABLE IF NOT EXISTS property_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    client_id INTEGER,
    listing_id INTEGER,
    stage TEXT DEFAULT 'new',
    source TEXT,
    budget_min INTEGER,
    budget_max INTEGER,
    requirements TEXT,
    last_contact DATE,
    next_action TEXT,
    next_action_date DATE,
    assigned_to INTEGER,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON property_leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_client ON property_leads(client_id);
CREATE INDEX IF NOT EXISTS idx_leads_assigned ON property_leads(assigned_to);
