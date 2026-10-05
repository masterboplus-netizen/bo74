"""core.object_works — работы объекта (расчёт стоимости работ).

Отличается от core.works (справочник видов работ) — здесь конкретные работы,
выполненные или запланированные на объекте.
"""
from core.db import fetchone, fetchall, commit
from core import spec


def create_work(object_id, work_type, qty=1, price_unit=None,
                room_id=None, group_id=None, is_manual=0, note=None):
    """Добавляет работу. Возвращает work_id."""
    work_label = spec.get_work_label(work_type)
    unit = spec.get_work_unit(work_type)
    if price_unit is None:
        price_unit = spec.get_work_price(work_type)
    total = round((qty or 0) * (price_unit or 0), 2)

    return commit(
        """INSERT INTO object_works
           (object_id, room_id, group_id, work_type, work_label,
            qty, unit, price_unit, total, is_manual, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, room_id, group_id, work_type, work_label,
         qty, unit, price_unit, total, is_manual, note)
    )


def get_work(work_id):
    row = fetchone("SELECT * FROM object_works WHERE id = ?", (work_id,))
    return dict(row) if row else None


def get_works_by_object(object_id):
    rows = fetchall(
        "SELECT * FROM object_works WHERE object_id = ? ORDER BY id",
        (object_id,)
    )
    return [dict(r) for r in rows]


def get_works_by_room(room_id):
    rows = fetchall(
        "SELECT * FROM object_works WHERE room_id = ? ORDER BY id",
        (room_id,)
    )
    return [dict(r) for r in rows]


def get_works_by_group(group_id):
    rows = fetchall(
        "SELECT * FROM object_works WHERE group_id = ? ORDER BY id",
        (group_id,)
    )
    return [dict(r) for r in rows]


def update_work(work_id, **kwargs):
    allowed = {"qty", "price_unit", "note", "work_type", "work_label", "unit"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(k + " = ?")
            params.append(v)
    if not fields:
        return False
    if "qty" in kwargs or "price_unit" in kwargs:
        cur = get_work(work_id)
        qty = kwargs.get("qty", cur.get('qty') if cur else 0)
        pu = kwargs.get("price_unit", cur.get('price_unit') if cur else 0)
        total = round((qty or 0) * (pu or 0), 2)
        fields.append("total = ?")
        params.append(total)
    params.append(work_id)
    commit("UPDATE object_works SET " + ", ".join(fields) + " WHERE id = ?", params)
    return True


def delete_work(work_id):
    commit("DELETE FROM object_works WHERE id = ?", (work_id,))
    return True


def calc_object_works_cost(object_id):
    """Сумма работ по объекту."""
    works = get_works_by_object(object_id)
    total = 0.0
    by_type = {}
    for w in works:
        t = w.get('total') or 0
        total += t
        wt = w.get('work_type') or 'other'
        by_type[wt] = by_type.get(wt, 0) + t
    return {
        'works_count': len(works),
        'total': round(total, 2),
        'by_type': {k: round(v, 2) for k, v in by_type.items()},
    }


def format_object_works(object_id):
    """Текстовая смета работ объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else ('Объект #' + str(object_id))
    data = calc_object_works_cost(object_id)

    lines = ["🔨 Работы объекта «" + str(obj_name) + "»", ""]
    works = get_works_by_object(object_id)
    if not works:
        lines.append("Работ пока нет.")
        return chr(10).join(lines)

    for idx, w in enumerate(works, start=1):
        mark = " [ручная]" if w.get('is_manual') else ""
        lines.append(
            str(idx) + ". " + str(w.get('work_label') or '?') +
            " — " + str(w.get('qty') or 0) + " " + str(w.get('unit') or '') +
            " × " + str(w.get('price_unit') or 0) + " ₽ = " +
            str(w.get('total') or 0) + " ₽" + mark
        )
    lines.append("")
    lines.append("💰 ИТОГО работ: " + str(data['total']) + " ₽")
    return chr(10).join(lines)
