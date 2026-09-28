-- 004: Комнаты (квартира, дом, ЖК)

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    name TEXT NOT NULL,
    is_default INTEGER DEFAULT 0,
    order_num INTEGER DEFAULT 0,
    note TEXT,
    area_sqm REAL,
    height REAL,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(object_id, name)
);
CREATE INDEX IF NOT EXISTS idx_rooms_object ON rooms(object_id);
CREATE INDEX IF NOT EXISTS idx_rooms_tenant ON rooms(tenant_id);

CREATE TABLE IF NOT EXISTS room_measures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    category TEXT NOT NULL,
    label TEXT,
    length REAL, width REAL, height REAL, depth REAL, angle REAL,
    unit TEXT DEFAULT 'м',
    note TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_measures_room ON room_measures(room_id);

CREATE TABLE IF NOT EXISTS room_comms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    comm_type TEXT NOT NULL,
    label TEXT,
    wall TEXT,
    offset_x REAL, offset_y REAL, depth REAL,
    diameter REAL, voltage TEXT,
    note TEXT,
    photo_id INTEGER,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_comms_room ON room_comms(room_id);

CREATE TABLE IF NOT EXISTS room_objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    name TEXT NOT NULL,
    obj_type TEXT,
    catalog_item_id INTEGER,
    length REAL, width REAL, height REAL,
    wall TEXT, offset_x REAL, offset_y REAL,
    needs_water INTEGER DEFAULT 0,
    needs_sewer INTEGER DEFAULT 0,
    needs_power INTEGER DEFAULT 0,
    power_kw REAL,
    status TEXT DEFAULT 'planned',
    note TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_roomobj_room ON room_objects(room_id);

CREATE TABLE IF NOT EXISTS room_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    event_type TEXT NOT NULL,
    event_data TEXT,
    user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_roomhist_room ON room_history(room_id);

CREATE TABLE IF NOT EXISTS supplies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER NOT NULL,
    room_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    catalog_item_id INTEGER,
    name TEXT NOT NULL,
    qty REAL,
    unit TEXT,
    status TEXT DEFAULT 'не заказано',
    price INTEGER,
    supplier_id INTEGER,
    note TEXT,
    deadline DATE,
    created_by INTEGER,
    source TEXT DEFAULT 'manual',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_supplies_object ON supplies(object_id);
CREATE INDEX IF NOT EXISTS idx_supplies_room ON supplies(room_id);

-- Расширения существующих таблиц
ALTER TABLE tasks ADD COLUMN room_id INTEGER;
ALTER TABLE tasks ADD COLUMN source TEXT DEFAULT 'manual';
ALTER TABLE tasks ADD COLUMN is_external INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN external_price INTEGER;
ALTER TABLE tasks ADD COLUMN required_skill TEXT;
ALTER TABLE tasks ADD COLUMN complexity TEXT;
ALTER TABLE tasks ADD COLUMN estimated_hours REAL;

ALTER TABLE photos ADD COLUMN room_id INTEGER;
ALTER TABLE finance ADD COLUMN room_id INTEGER;
