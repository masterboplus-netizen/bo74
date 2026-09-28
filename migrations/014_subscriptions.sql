-- 014: Тарифы, подписки, биллинг (SaaS-заготовка)

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price_monthly INTEGER,
    price_yearly INTEGER,
    currency TEXT DEFAULT 'RUB',
    limits TEXT,
    features TEXT,
    is_active INTEGER DEFAULT 1,
    order_num INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invoices_billing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    subscription_id INTEGER,
    amount INTEGER,
    currency TEXT DEFAULT 'RUB',
    period_start DATE,
    period_end DATE,
    status TEXT DEFAULT 'pending',
    payment_provider TEXT,
    payment_id TEXT,
    paid_at DATETIME,
    pdf_path TEXT,
    note TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_binvoices_tenant ON invoices_billing(tenant_id);
CREATE INDEX IF NOT EXISTS idx_binvoices_status ON invoices_billing(status);

CREATE TABLE IF NOT EXISTS payment_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    invoice_id INTEGER,
    provider TEXT,
    external_id TEXT,
    amount INTEGER,
    status TEXT,
    raw_response TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_paytx_tenant ON payment_transactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_paytx_external ON payment_transactions(external_id);

-- Стартовые тарифы
INSERT OR IGNORE INTO plans (code, name, price_monthly, price_yearly, limits, features, order_num)
VALUES
  ('lite',   'Lite — старт',     0,     0,     '{"objects":3,"rooms":30,"tasks":100}', '["базовые функции","1 пользователь"]', 1),
  ('prime',  'Prime — команда',  2900,  29000, '{"objects":30,"rooms":300,"tasks":2000}', '["все функции","5 пользователей","дашборд","интеграции"]', 2),
  ('expert', 'Expert — бизнес',  9900,  99000, '{"objects":-1,"rooms":-1,"tasks":-1}', '["всё без лимитов","неограниченно","API","приоритетная поддержка"]', 3);

-- Купоны и промо-коды
CREATE TABLE IF NOT EXISTS coupons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    discount_type TEXT DEFAULT 'percent',
    discount_value INTEGER,
    max_uses INTEGER,
    used_count INTEGER DEFAULT 0,
    valid_from DATE,
    valid_until DATE,
    applicable_plans TEXT,
    note TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(code);

CREATE TABLE IF NOT EXISTS coupon_redemptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coupon_id INTEGER NOT NULL,
    tenant_id INTEGER,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    discount_applied INTEGER
);
CREATE INDEX IF NOT EXISTS idx_redempt_coupon ON coupon_redemptions(coupon_id);
CREATE INDEX IF NOT EXISTS idx_redempt_tenant ON coupon_redemptions(tenant_id);

-- Рефералы (приглашения)
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_tenant_id INTEGER NOT NULL,
    referred_tenant_id INTEGER,
    code TEXT,
    status TEXT DEFAULT 'invited',
    reward_amount INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    rewarded_at DATETIME
);
CREATE INDEX IF NOT EXISTS idx_ref_referrer ON referrals(referrer_tenant_id);
CREATE INDEX IF NOT EXISTS idx_ref_code ON referrals(code);
