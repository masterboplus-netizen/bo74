-- Миграция 038: Вводной автомат щита + автокомплектация

-- 1. Поля вводного автомата
ALTER TABLE elec_panels ADD COLUMN input_breaker_type TEXT;
ALTER TABLE elec_panels ADD COLUMN input_breaker_rating INTEGER;
ALTER TABLE elec_panels ADD COLUMN input_breaker_curve TEXT;
ALTER TABLE elec_panels ADD COLUMN input_breaker_poles INTEGER;
ALTER TABLE elec_panels ADD COLUMN input_breaker_rcd_ma INTEGER;

-- 2. Поля корпуса щита
ALTER TABLE elec_panels ADD COLUMN enclosure_type TEXT;
ALTER TABLE elec_panels ADD COLUMN modules_count INTEGER;
ALTER TABLE elec_panels ADD COLUMN has_busbar INTEGER DEFAULT 0;

-- 3. Таблица комплектации щита (автоматы, УЗО, шины, клеммы)
CREATE TABLE IF NOT EXISTS elec_panel_components (
    id INTEGER PRIMARY KEY,
    panel_id INTEGER NOT NULL,
    component_type TEXT NOT NULL,
    component_model TEXT,
    rating INTEGER,
    curve TEXT,
    poles INTEGER,
    rcd_ma INTEGER,
    quantity INTEGER DEFAULT 1,
    linked_group_id INTEGER,
    order_num INTEGER,
    is_manual INTEGER DEFAULT 0,
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_components_panel ON elec_panel_components(panel_id);
CREATE INDEX IF NOT EXISTS idx_components_group ON elec_panel_components(linked_group_id);
