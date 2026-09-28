-- 009: Договоры и платежи

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    object_id INTEGER,
    client_id INTEGER,
    contract_type TEXT,
    contract_number TEXT,
    amount INTEGER,
    currency TEXT DEFAULT 'RUB',
    start_date DATE,
    end_date DATE,
    payment_schedule TEXT,
    status TEXT DEFAULT 'draft',
    document_path TEXT,
    signed_by INTEGER,
    signed_at DATETIME,
    note TEXT,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_contracts_object ON contracts(object_id);
CREATE INDEX IF NOT EXISTS idx_contracts_client ON contracts(client_id);
CREATE INDEX IF NOT EXISTS idx_contracts_type ON contracts(contract_type);
CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);

CREATE TABLE IF NOT EXISTS contract_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    amount INTEGER,
    due_date DATE,
    paid_date DATE,
    status TEXT DEFAULT 'pending',
    method TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_payments_contract ON contract_payments(contract_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON contract_payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_due ON contract_payments(due_date);

-- Доп.соглашения (изменения к договору)
CREATE TABLE IF NOT EXISTS contract_amendments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    tenant_id INTEGER DEFAULT 1,
    amendment_number TEXT,
    description TEXT,
    amount_delta INTEGER DEFAULT 0,
    date DATE,
    document_path TEXT,
    signed_by INTEGER,
    signed_at DATETIME,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_amend_contract ON contract_amendments(contract_id);

-- Документы (сканы договоров, актов, чеков)
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER DEFAULT 1,
    entity_type TEXT,
    entity_id INTEGER,
    doc_type TEXT,
    name TEXT,
    file_uuid TEXT,
    file_path TEXT,
    mime TEXT,
    size INTEGER,
    uploaded_by INTEGER,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Миграция: добавляем поля в старую documents
ALTER TABLE documents ADD COLUMN entity_type TEXT;
ALTER TABLE documents ADD COLUMN entity_id INTEGER;
ALTER TABLE documents ADD COLUMN doc_type TEXT;
ALTER TABLE documents ADD COLUMN file_uuid TEXT;
ALTER TABLE documents ADD COLUMN file_path TEXT;
ALTER TABLE documents ADD COLUMN mime TEXT;
ALTER TABLE documents ADD COLUMN size INTEGER;
ALTER TABLE documents ADD COLUMN uploaded_by INTEGER;
ALTER TABLE documents ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE documents ADD COLUMN note TEXT;

-- Миграция: добавляем поля в старую documents
ALTER TABLE documents ADD COLUMN entity_type TEXT;
ALTER TABLE documents ADD COLUMN entity_id INTEGER;
ALTER TABLE documents ADD COLUMN doc_type TEXT;
ALTER TABLE documents ADD COLUMN file_uuid TEXT;
ALTER TABLE documents ADD COLUMN file_path TEXT;
ALTER TABLE documents ADD COLUMN mime TEXT;
ALTER TABLE documents ADD COLUMN size INTEGER;
ALTER TABLE documents ADD COLUMN uploaded_by INTEGER;
ALTER TABLE documents ADD COLUMN tenant_id INTEGER DEFAULT 1;
ALTER TABLE documents ADD COLUMN note TEXT;

CREATE INDEX IF NOT EXISTS idx_docs_entity ON documents(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_docs_type ON documents(doc_type);
