"""core.materials — материалы и расчёт по нормам."""
from core.db import fetchone, fetchall, commit


CATEGORIES = [
    "Штукатурка", "Шпаклёвка", "Грунтовка", "Краска",
    "Клей", "Затирка", "Стяжка", "Плитка",
    "Ламинат", "Обои", "Кабель", "Трубы",
    "Фитинги", "Крепёж", "Прочее",
]

UNITS = ["кг", "л", "м²", "м.п.", "шт", "м³"]


def add_material(name, category, unit, norm_per_sqm,
                 price, supplier_id=None, loss_percent=10):
    return commit(
        """INSERT INTO materials
           (name, category, unit, norm_per_sqm, price, supplier_id, loss_percent)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, category, unit, norm_per_sqm, price, supplier_id, loss_percent)
    )


def get_material(material_id):
    row = fetchone("SELECT * FROM materials WHERE id = ?", (material_id,))
    return dict(row) if row else None


def get_materials(category=None):
    if category:
        rows = fetchall("SELECT * FROM materials WHERE category = ? ORDER BY name", (category,))
    else:
        rows = fetchall("SELECT * FROM materials ORDER BY category, name")
    return [dict(r) for r in rows]


def update_material(material_id, **kwargs):
    allowed = {"name", "category", "unit", "norm_per_sqm", "price", "supplier_id", "loss_percent"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(material_id)
    commit(f"UPDATE materials SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_material(material_id):
    commit("DELETE FROM materials WHERE id = ?", (material_id,))
    return True


def calc_qty(material_id, area_sqm):
    """Считает количество: area × norm × (1 + loss/100)."""
    m = get_material(material_id)
    if not m:
        return 0
    norm = m.get('norm_per_sqm') or 0
    loss = m.get('loss_percent') or 0
    return round(area_sqm * norm * (1 + loss / 100), 2)


def calc_cost(material_id, area_sqm):
    """Считает стоимость: qty × price."""
    m = get_material(material_id)
    if not m:
        return 0
    qty = calc_qty(material_id, area_sqm)
    price = m.get('price') or 0
    return round(qty * price, 2)


def calc_room_materials(room_id):
    """Материалы для комнаты — заглушка, требует work_types."""
    return []


def import_materials_from_json(path):
    """Импорт материалов из JSON."""
    import json
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for item in data:
            add_material(
                name=item.get('name'),
                category=item.get('category') or 'Прочее',
                unit=item.get('unit') or 'шт',
                norm_per_sqm=item.get('norm_per_sqm') or 0,
                price=item.get('price') or 0,
                loss_percent=item.get('loss_percent') or 10,
            )
            count += 1
        return count
    except Exception as e:
        print(f"⚠️ import_materials: {e}")
        return 0
