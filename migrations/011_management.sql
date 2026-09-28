-- 011: Управление зданиями и обслуживание

-- Заявки от жильцов/арендаторов
CREATE TABLE IF NOT EXISTS service_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    building_id INTEGER,
    unit_id INTEGER,
    object_id INTEGER,
    request_type TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'new',
    assigned_to INTEGER,
    created_by INTEGER,
    photos TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    closed_at DATETIME,
    resolution TEXT,
    cost INTEGER
);
CREATE INDEX IF NOT EXISTS idx_sreq_building ON service_requests(building_id);
CREATE INDEX IF NOT EXISTS idx_sreq_status ON service_requests(status);
CREATE INDEX IF NOT EXISTS idx_sreq_assigned ON service_requests(assigned_to);

-- Регулярное обслуживание (графики)
CREATE TABLE IF NOT EXISTS maintenance_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    building_id INTEGER,
    object_id INTEGER,
    service_type TEXT NOT NULL,
    description TEXT,
    frequency TEXT,
    last_done DATE,
    next_due DATE,
    responsible_id INTEGER,
    cost INTEGER,
    is_active INTEGER DEFAULT 1,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_msch_building ON maintenance_schedules(building_id);
CREATE INDEX IF NOT EXISTS idx_msch_next ON maintenance_schedules(next_due);

-- Счётчики (вода, свет, газ)
CREATE TABLE IF NOT EXISTS meters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    unit_id INTEGER,
    object_id INTEGER,
    meter_type TEXT NOT NULL,
    serial_number TEXT,
    unit TEXT,
    installed_at DATE,
    last_verified DATE,
    is_active INTEGER DEFAULT 1,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_meters_unit ON meters(unit_id);
CREATE INDEX IF NOT EXISTS idx_meters_type ON meters(meter_type);

-- Показания счётчиков
CREATE TABLE IF NOT EXISTS meter_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meter_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    reading_value REAL,
    reading_date DATE,
    taken_by INTEGER,
    photo_id INTEGER,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_readings_meter ON meter_readings(meter_id);
CREATE INDEX IF NOT EXISTS idx_readings_date ON meter_readings(reading_date);

-- Квитанции (коммуналка, обслуживание)
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    unit_id INTEGER,
    object_id INTEGER,
    client_id INTEGER,
    invoice_type TEXT,
    period TEXT,
    amount INTEGER,
    status TEXT DEFAULT 'draft',
    due_date DATE,
    paid_date DATE,
    pdf_path TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_inv_unit ON invoices(unit_id);
CREATE INDEX IF NOT EXISTS idx_inv_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_inv_due ON invoices(due_date);
