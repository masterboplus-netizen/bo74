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


def calc_object_labor(object_id, rate_per_hour=None, prefix=None):
    """Расчёт работ по норматив-часам.
    Возвращает часы × ставка, отдельно от цен по прайсу."""
    if rate_per_hour is None:
        rate_per_hour = 800.0
        try:
            r = fetchone("SELECT value FROM system_settings WHERE key = 'labor_rate_hour'")
            if r and r['value']:
                rate_per_hour = float(r['value'])
        except Exception:
            pass

    works = get_works_by_object(object_id)
    total_hours = 0.0
    total_by_price = 0.0
    by_type = {}
    for w in works:
        wt = w.get('work_type') or 'other'
        if prefix and not wt.startswith(prefix):
            continue
        qty = float(w.get('qty') or 0)
        h_per_unit = spec.get_work_hours(wt)
        h = round(qty * h_per_unit, 3)
        total_hours += h
        total_by_price += float(w.get('total') or 0)
        if wt not in by_type:
            by_type[wt] = {
                'label': spec.get_work_label(wt),
                'qty': 0.0, 'unit': w.get('unit') or '',
                'hours': 0.0,
                'cost_by_hours': 0.0,
                'cost_by_price': 0.0,
            }
        by_type[wt]['qty'] = round(by_type[wt]['qty'] + qty, 3)
        by_type[wt]['hours'] = round(by_type[wt]['hours'] + h, 3)
        by_type[wt]['cost_by_hours'] = round(by_type[wt]['hours'] * rate_per_hour, 2)
        by_type[wt]['cost_by_price'] = round(by_type[wt]['cost_by_price'] + float(w.get('total') or 0), 2)

    return {
        'works_count': len(works),
        'total_hours': round(total_hours, 2),
        'rate_per_hour': rate_per_hour,
        'total_by_hours': round(total_hours * rate_per_hour, 2),
        'total_by_price': round(total_by_price, 2),
        'by_type': by_type,
    }


def format_object_labor(object_id, prefix=None):
    """Текстовая смета работ по норматив-часам (отдельно от материалов)."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else ('Объект #' + str(object_id))
    d = calc_object_labor(object_id, prefix=prefix)

    lines = ["👷 Работы (норматив-часы) «" + str(obj_name) + "»", ""]
    if not d['works_count']:
        lines.append("Работ пока нет.")
        return chr(10).join(lines)

    for wt, info in d['by_type'].items():
        lines.append(
            str(info['label']) + ": " +
            str(info['qty']) + " " + str(info['unit']) + " × " +
            str(round(info['hours'] / info['qty'], 3) if info['qty'] else 0) + " ч = " +
            str(info['hours']) + " ч"
        )
        lines.append(
            "  · по нормативам: " + str(info['cost_by_hours']) + " ₽" +
            "  | по прайсу: " + str(info['cost_by_price']) + " ₽"
        )

    lines.append("")
    lines.append("Ставка часа: " + str(d['rate_per_hour']) + " ₽")
    lines.append("Всего часов: " + str(d['total_hours']) + " ч")
    lines.append("💰 Работы по нормативам: " + str(d['total_by_hours']) + " ₽")
    lines.append("💵 Работы по прайсу: " + str(d['total_by_price']) + " ₽")
    return chr(10).join(lines)


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
