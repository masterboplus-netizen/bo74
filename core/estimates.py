"""core.estimates — сметы."""
from core.db import fetchone, fetchall, commit


def create_estimate(object_id, session_id=None, name=None):
    return commit(
        """INSERT INTO estimates (object_id, session_id, name, status)
           VALUES (?, ?, ?, 'draft')""",
        (object_id, session_id, name)
    )


def get_estimate(estimate_id):
    row = fetchone("SELECT * FROM estimates WHERE id = ?", (estimate_id,))
    if not row:
        return None
    est = dict(row)
    est['items'] = get_estimate_items(estimate_id)
    return est


def get_estimates(object_id):
    rows = fetchall(
        "SELECT * FROM estimates WHERE object_id = ? ORDER BY created_at DESC",
        (object_id,)
    )
    return [dict(r) for r in rows]


def add_estimate_item(estimate_id, name, qty, unit, price):
    total = round(qty * price, 2)
    return commit(
        """INSERT INTO estimate_items
           (estimate_id, name, qty, unit, price, total)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (estimate_id, name, qty, unit, price, total)
    )


def get_estimate_items(estimate_id):
    rows = fetchall(
        "SELECT * FROM estimate_items WHERE estimate_id = ? ORDER BY id",
        (estimate_id,)
    )
    return [dict(r) for r in rows]


def recalc_estimate(estimate_id):
    """Пересчитывает итог сметы."""
    row = fetchone(
        "SELECT COALESCE(SUM(total), 0) as s FROM estimate_items WHERE estimate_id = ?",
        (estimate_id,)
    )
    total = row['s'] if row else 0
    commit("UPDATE estimates SET total = ? WHERE id = ?", (total, estimate_id))
    return total


def update_estimate_status(estimate_id, status):
    allowed = ('draft', 'approved', 'invoiced', 'paid')
    if status not in allowed:
        return False
    commit("UPDATE estimates SET status = ? WHERE id = ?", (status, estimate_id))
    return True


def delete_estimate(estimate_id):
    commit("DELETE FROM estimate_items WHERE estimate_id = ?", (estimate_id,))
    commit("DELETE FROM estimates WHERE id = ?", (estimate_id,))
    return True


def format_estimate(estimate_id):
    est = get_estimate(estimate_id)
    if not est:
        return "❌ Смета не найдена"
    lines = [f"📋 *Смета #{estimate_id}*"]
    if est.get('name'):
        lines.append(est['name'])
    lines.append("")
    for item in est['items']:
        lines.append(f"• {item['name']}: {item['qty']} {item['unit']} × {item['price']} = {item['total']} ₽")
    lines.append("")
    lines.append(f"💰 *ИТОГО: {est.get('total') or 0} ₽*")
    return "\n".join(lines)
