-- Миграция 037: Щиты ЭОМ (несколько на объект)
-- Фундамент для трасс, сантехники, BIM

-- 1. Таблица щитов
CREATE TABLE IF NOT EXISTS elec_panels (
    id INTEGER PRIMARY KEY,
    object_id INTEGER NOT NULL,
    floor_id INTEGER,
    room_id INTEGER,
    name TEXT NOT NULL,
    panel_type TEXT DEFAULT 'floor',
    parent_panel_id INTEGER,
    mount_type TEXT DEFAULT 'wall',
    input_breaker TEXT,
    meter_type TEXT,
    lat REAL,
    lon REAL,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_panels_object ON elec_panels(object_id);
CREATE INDEX IF NOT EXISTS idx_panels_floor ON elec_panels(floor_id);
CREATE INDEX IF NOT EXISTS idx_panels_parent ON elec_panels(parent_panel_id);

-- 2. Связи щит <-> щит (питание)
CREATE TABLE IF NOT EXISTS elec_panel_links (
    id INTEGER PRIMARY KEY,
    parent_panel_id INTEGER NOT NULL,
    child_panel_id INTEGER NOT NULL,
    cable_type TEXT,
    length_m REAL,
    route_type TEXT,
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_panel_links_parent ON elec_panel_links(parent_panel_id);
CREATE INDEX IF NOT EXISTS idx_panel_links_child ON elec_panel_links(child_panel_id);

-- 3. Привязка групп к щиту
ALTER TABLE elec_groups ADD COLUMN panel_id INTEGER;

-- (индекс idx_groups_panel создаётся после ALTER — может упасть если уже есть,
--  поэтому пропускаем или ставим после проверки)
