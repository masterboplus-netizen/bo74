-- Миграция 042: Сантехника (коллекторы + трассы)
CREATE TABLE IF NOT EXISTS plumbing_panels (
    id INTEGER PRIMARY KEY,
    object_id INTEGER NOT NULL,
    floor_id INTEGER,
    room_id INTEGER,
    name TEXT NOT NULL,
    panel_type TEXT DEFAULT 'collector',
    parent_panel_id INTEGER,
    mount_type TEXT DEFAULT 'wall',
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pp_object ON plumbing_panels(object_id);
CREATE INDEX IF NOT EXISTS idx_pp_floor ON plumbing_panels(floor_id);
CREATE INDEX IF NOT EXISTS idx_pp_parent ON plumbing_panels(parent_panel_id);

CREATE TABLE IF NOT EXISTS plumbing_routes (
    id INTEGER PRIMARY KEY,
    object_id INTEGER NOT NULL,
    panel_id INTEGER,
    from_point_id INTEGER,
    to_point_id INTEGER,
    pipe_type TEXT,
    length_m REAL,
    route_type TEXT,
    waypoints TEXT,
    is_manual INTEGER DEFAULT 0,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pr_object ON plumbing_routes(object_id);
CREATE INDEX IF NOT EXISTS idx_pr_panel ON plumbing_routes(panel_id);
