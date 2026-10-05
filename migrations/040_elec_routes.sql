-- Миграция 040: Трассы ЭОМ (метраж от щита к точкам)
-- Заложена основа для будущей автотрассировки (waypoints)

CREATE TABLE IF NOT EXISTS elec_routes (
    id INTEGER PRIMARY KEY,
    object_id INTEGER NOT NULL,
    panel_id INTEGER,
    group_id INTEGER,
    from_point_id INTEGER,
    to_point_id INTEGER,
    cable_type TEXT,
    length_m REAL,
    route_type TEXT,
    waypoints TEXT,
    is_manual INTEGER DEFAULT 0,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_routes_object ON elec_routes(object_id);
CREATE INDEX IF NOT EXISTS idx_routes_panel ON elec_routes(panel_id);
CREATE INDEX IF NOT EXISTS idx_routes_group ON elec_routes(group_id);
CREATE INDEX IF NOT EXISTS idx_routes_to_point ON elec_routes(to_point_id);
