"""core.floors — Помещения (этажи / зоны объекта).

Помещение = этаж квартиры / дома / зона кафе (зал, цех, склад).
Комнаты привязываются к помещению через rooms.floor_id.
"""
from core.db import fetchone, fetchall, commit


# ============================================================
# CRUD
# ============================================================

def create_floor(object_id, floor_number=1, floor_name=None,
                 area_sqm=None, height_avg=None, note=None):
    """Создаёт помещение. Возвращает floor_id."""
    if not floor_name:
        floor_name = f"Этаж {floor_number}"
    return commit(
        """INSERT INTO floors
           (object_id, floor_number, floor_name, area_sqm, height_avg, note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (object_id, floor_number, floor_name, area_sqm, height_avg, note)
    )


def get_floor(floor_id):
    row = fetchone("SELECT * FROM floors WHERE id = ?", (floor_id,))
    return dict(row) if row else None


def get_floors(object_id):
    """Все помещения объекта."""
    rows = fetchall(
        "SELECT * FROM floors WHERE object_id = ? ORDER BY floor_number, id",
        (object_id,)
    )
    return [dict(r) for r in rows]


def update_floor(floor_id, **kwargs):
    allowed = {"floor_number", "floor_name", "area_sqm", "height_avg", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(floor_id)
    commit(f"UPDATE floors SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_floor(floor_id):
    """Удаляет помещение. Комнаты отвязывает (floor_id = NULL)."""
    commit("UPDATE rooms SET floor_id = NULL WHERE floor_id = ?", (floor_id,))
    commit("UPDATE elec_groups SET floor_id = NULL WHERE floor_id = ?", (floor_id,))
    commit("DELETE FROM floors WHERE id = ?", (floor_id,))
    return True


# ============================================================
# ПОМОЩНИКИ
# ============================================================

def ensure_default_floor(object_id):
    """Если у объекта нет помещений — создаёт «Этаж 1». Возвращает floor_id."""
    floors = get_floors(object_id)
    if floors:
        return floors[0]['id']
    return create_floor(object_id, floor_number=1, floor_name="Этаж 1")


def get_rooms_of_floor(floor_id):
    """Все комнаты этого помещения."""
    rows = fetchall(
        """SELECT id, name, room_type, height, is_default, order_num
           FROM rooms WHERE floor_id = ? ORDER BY order_num, id""",
        (floor_id,)
    )
    return [dict(r) for r in rows]


def count_rooms(floor_id):
    r = fetchone("SELECT COUNT(*) as cnt FROM rooms WHERE floor_id = ?", (floor_id,))
    return r['cnt'] if r else 0


def format_floor(f):
    """Строка-описание помещения."""
    name = f.get('floor_name') or f"Этаж {f.get('floor_number') or '?'}"
    rooms = count_rooms(f['id'])
    area = f.get('area_sqm')
    parts = [f"🏠 *{name}*"]
    if area:
        parts.append(f"{area} м²")
    parts.append(f"комнат: {rooms}")
    return " · ".join(parts)


def list_floors_text(object_id):
    """Текстовый список помещений объекта."""
    floors = get_floors(object_id)
    if not floors:
        return "_Пока помещений нет._"
    lines = []
    for f in floors:
        lines.append(format_floor(f))
    return "\n".join(lines)
