-- Миграция 041: Цены компонентов + интеграция с маркетплейсами

-- 1. Поля цены в компонентах щита
ALTER TABLE elec_panel_components ADD COLUMN price_unit REAL;
ALTER TABLE elec_panel_components ADD COLUMN price_source TEXT;
ALTER TABLE elec_panel_components ADD COLUMN price_updated_at DATETIME;
ALTER TABLE elec_panel_components ADD COLUMN market_url TEXT;
ALTER TABLE elec_panel_components ADD COLUMN market_sku TEXT;
ALTER TABLE elec_panel_components ADD COLUMN brand TEXT;

-- 2. Справочник цен (по типам)
CREATE TABLE IF NOT EXISTS component_prices (
    id INTEGER PRIMARY KEY,
    component_type TEXT NOT NULL,
    rating INTEGER,
    poles INTEGER,
    brand TEXT,
    price REAL,
    currency TEXT DEFAULT 'RUB',
    source TEXT,
    market_url TEXT,
    market_sku TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cp_type ON component_prices(component_type, rating, poles);
CREATE INDEX IF NOT EXISTS idx_cp_brand ON component_prices(brand);
