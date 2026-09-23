"""Модуль CRM БО 7.5 — клиенты и сделки"""
from db import get_connection

# ============================================================
# КЛИЕНТЫ
# ============================================================

def add_client(name: str, phone: str = None, email: str = None,
               address: str = None, source: str = None, tg_id: int = None) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO clients (name, phone, email, address, source, tg_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, phone, email, address, source, tg_id)
    )
    client_id = c.lastrowid
    conn.commit()
    conn.close()
    return client_id


def get_clients() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, phone, email, address, source, created_at FROM clients ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [{'id': r['id'], 'name': r['name'], 'phone': r['phone'],
             'email': r['email'], 'address': r['address'],
             'source': r['source'], 'created_at': r['created_at']} for r in rows]


def get_client(client_id: int) -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, phone, email, address, source, created_at FROM clients WHERE id = ?", (client_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return None
    return {'id': r['id'], 'name': r['name'], 'phone': r['phone'],
            'email': r['email'], 'address': r['address'],
            'source': r['source'], 'created_at': r['created_at']}


def format_clients(clients: list = None) -> str:
    if clients is None:
        clients = get_clients()
    if not clients:
        return "👥 Клиентов пока нет.\n\nДобавить: /client_add"
    text = f"👥 КЛИЕНТЫ ({len(clients)})\n\n"
    for c in clients[:30]:
        text += f"#{c['id']} {c['name']}"
        if c['phone']:
            text += f" · {c['phone']}"
        text += "\n"
    if len(clients) > 30:
        text += f"\n... (показаны первые 30 из {len(clients)})"
    return text


def format_client_card(client: dict) -> str:
    if not client:
        return "❌ Клиент не найден"
    text = f"👤 КЛИЕНТ #{client['id']}\n\n"
    text += f"Имя: {client['name']}\n"
    if client['phone']:
        text += f"📞 {client['phone']}\n"
    if client['email']:
        text += f"✉️ {client['email']}\n"
    if client['address']:
        text += f"📍 {client['address']}\n"
    if client['source']:
        text += f"🔗 Источник: {client['source']}\n"
    text += f"📅 Создан: {client['created_at'][:10] if client['created_at'] else '—'}"
    deals = get_client_deals(client['id'])
    if deals:
        text += f"\n\n💼 СДЕЛКИ ({len(deals)}):\n"
        for d in deals[:10]:
            text += f"  • #{d['id']} {d['status']} — {d['budget'] or 0} ₽"
            if d['object_name']:
                text += f" ({d['object_name']})"
            text += "\n"
    return text


# ============================================================
# СДЕЛКИ
# ============================================================

def add_deal(client_id: int, object_id: int = None, status: str = 'new',
             budget: int = 0) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO crm_deals (client_id, object_id, status, budget) VALUES (?, ?, ?, ?)",
        (client_id, object_id, status, budget)
    )
    deal_id = c.lastrowid
    conn.commit()
    conn.close()
    return deal_id


def get_deals() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT d.id, d.status, d.budget, d.created_at,
               c.name as client_name, c.id as client_id,
               o.name as object_name, o.id as object_id
        FROM crm_deals d
        LEFT JOIN clients c ON d.client_id = c.id
        LEFT JOIN objects o ON d.object_id = o.id
        ORDER BY d.id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [{'id': r['id'], 'status': r['status'], 'budget': r['budget'],
             'created_at': r['created_at'],
             'client_name': r['client_name'], 'client_id': r['client_id'],
             'object_name': r['object_name'], 'object_id': r['object_id']} for r in rows]


def get_client_deals(client_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT d.id, d.status, d.budget, d.created_at,
               o.name as object_name, o.id as object_id
        FROM crm_deals d
        LEFT JOIN objects o ON d.object_id = o.id
        WHERE d.client_id = ?
        ORDER BY d.id DESC
    """, (client_id,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r['id'], 'status': r['status'], 'budget': r['budget'],
             'created_at': r['created_at'],
             'object_name': r['object_name'], 'object_id': r['object_id']} for r in rows]


def format_deals(deals: list = None) -> str:
    if deals is None:
        deals = get_deals()
    if not deals:
        return "💼 Сделок пока нет.\n\nДобавить: /deal_add"
    text = f"💼 СДЕЛКИ ({len(deals)})\n\n"
    for d in deals[:30]:
        client = d['client_name'] or '—'
        status_icon = {'new': '🆕', 'in_progress': '🔄', 'won': '✅',
                       'lost': '❌', 'paused': '⏸'}.get(d['status'], '•')
        text += f"{status_icon} #{d['id']} {client} — {d['budget'] or 0} ₽"
        if d['object_name']:
            text += f" ({d['object_name']})"
        text += "\n"
    if len(deals) > 30:
        text += f"\n... (показаны первые 30 из {len(deals)})"
    return text


def update_deal_status(deal_id: int, status: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE crm_deals SET status = ? WHERE id = ?", (status, deal_id))
    conn.commit()
    conn.close()
