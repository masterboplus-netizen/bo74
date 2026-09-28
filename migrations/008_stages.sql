-- 008: Этапы стройки (для домов, ЖК, ремонта)

CREATE TABLE IF NOT EXISTS stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER NOT NULL,
    stage_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    parent_id INTEGER,
    order_num INTEGER DEFAULT 0,
    status TEXT DEFAULT 'planned',
    planned_start DATE,
    planned_end DATE,
    actual_start DATE,
    actual_end DATE,
    budget INTEGER DEFAULT 0,
    spent INTEGER DEFAULT 0,
    responsible_id INTEGER,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_stages_object ON stages(object_id);
CREATE INDEX IF NOT EXISTS idx_stages_parent ON stages(parent_id);
CREATE INDEX IF NOT EXISTS idx_stages_status ON stages(status);

-- Шаблоны этапов (пресеты под типы объектов)
CREATE TABLE IF NOT EXISTS stage_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_type TEXT NOT NULL,
    stage_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    order_num INTEGER DEFAULT 0,
    default_days INTEGER,
    requires_inspection INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_stempl_type ON stage_templates(object_type);

-- Проверки этапов (инспекции)
CREATE TABLE IF NOT EXISTS stage_inspections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    inspection_type TEXT,
    inspector_id INTEGER,
    result TEXT DEFAULT 'pending',
    checklist TEXT,
    photos TEXT,
    defects TEXT,
    note TEXT,
    inspected_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_inspect_stage ON stage_inspections(stage_id);
CREATE INDEX IF NOT EXISTS idx_inspect_result ON stage_inspections(result);

-- Акты (КС-2, КС-3)
CREATE TABLE IF NOT EXISTS acts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER,
    stage_id INTEGER,
    contract_id INTEGER,
    tenant_id INTEGER DEFAULT 1,
    act_type TEXT DEFAULT 'ks2',
    act_number TEXT,
    act_date DATE,
    amount INTEGER,
    period_start DATE,
    period_end DATE,
    status TEXT DEFAULT 'draft',
    pdf_path TEXT,
    signed_by INTEGER,
    signed_at DATETIME,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_acts_object ON acts(object_id);
CREATE INDEX IF NOT EXISTS idx_acts_contract ON acts(contract_id);
