"""core.floors — Помещения (этажи / зоны объекта).

Помещение = этаж квартиры / дома / зона кафе (зал, цех, склад).
Комнаты привязываются к помещению через rooms.floor_id.
"""
from core.db import fetchone, fetchall, commit


# ============================================================
# ТИПЫ ПОМЕЩЕНИЙ
# ============================================================

FLOOR_TYPES = {
    'land':      '🌳 Участок',
    'building':  '🏢 Здание',
    'house':     '🏠 Дом',
    'floor':     '🏠 Этаж',
    'apartment': '🚪 Квартира',
    'basement':  '🏚 Подвал',
    'common':    '🚶 МОП',
    'roof':      '🏔 Кровля',
    'technical': '⚙️ Тех.помещение',
    'parking':   '🅿️ Парковка',
    'landscape': '🌿 Ландшафт',
    'bathhouse': '🧖 Баня',
    'garage':    '🚗 Гараж',
    'warehouse': '📦 Склад',
    'utility':   '🔧 Сетевой',
    'span':      '🌉 Пролёт',
    'monument':  '🏛 Памятник',
    'green':     '🌳 Зелёные',
    'zone':      '📍 Зона',
}


def get_type_icon(t):
    return FLOOR_TYPES.get(t or 'floor', '🏠')


# ============================================================
# CRUD
# ============================================================

def create_floor(object_id, floor_number=1, floor_name=None,
                 area_sqm=None, height_avg=None, note=None,
                 parent_id=None, type="floor", sort_order=0):
    """Создаёт помещение. Возвращает floor_id.

    parent_id — родитель (None = корень)
    type — house/floor/apartment/basement/common/roof/land/zone
    """
    if not floor_name:
        floor_name = f"Этаж {floor_number}"
    return commit(
        """INSERT INTO floors
        (object_id, floor_number, floor_name, area_sqm, height_avg, note,
         parent_id, type, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, floor_number, floor_name, area_sqm, height_avg, note,
         parent_id, type, sort_order)
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


def get_children(floor_id):
    """Дочерние помещения."""
    rows = fetchall(
        "SELECT * FROM floors WHERE parent_id = ? ORDER BY sort_order, id",
        (floor_id,)
    )
    return [dict(r) for r in rows]


def get_root_floors(object_id):
    """Корневые помещения (без родителя)."""
    rows = fetchall(
        "SELECT * FROM floors WHERE object_id = ? AND parent_id IS NULL ORDER BY sort_order, floor_number, id",
        (object_id,)
    )
    return [dict(r) for r in rows]


def get_full_path(floor_id):
    """Путь до помещения: Дом / Этаж 1 / Квартира 1."""
    parts = []
    cur = get_floor(floor_id)
    seen = set()
    while cur and cur["id"] not in seen:
        seen.add(cur["id"])
        parts.append(str(cur.get("floor_name") or "?"))
        pid = cur.get("parent_id")
        cur = get_floor(pid) if pid else None
    return " / ".join(reversed(parts))


def ensure_default_root(object_id, root_type='building'):
    """Гарантирует корневое помещение.

    root_type: land (усадьба) / building (многоэтажка, офис) / apartment (квартира) / zone
    """
    roots = get_root_floors(object_id)
    for r in roots:
        if r.get("type") in (root_type, 'land', 'building', 'house'):
            return r["id"]
    labels = {"land": "Участок", "building": "Здание", "apartment": "Квартира", "zone": "Зона"}
    name = labels.get(root_type, "Здание")
    return create_floor(object_id, floor_name=name, type=root_type, parent_id=None)


# Обратная совместимость
def ensure_default_house(object_id):
    return ensure_default_root(object_id, 'building')


def delete_floor_cascade(floor_id):
    """Удаляет помещение + всех детей рекурсивно."""
    children = get_children(floor_id)
    for c in children:
        delete_floor_cascade(c["id"])
    delete_floor(floor_id)
    return True


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
    parts = [f"{get_type_icon(f.get("type"))} *{name}*"]
    if area:
        parts.append(f"{area} м²")
    parts.append(f"комнат: {rooms}")
    return " · ".join(parts)


def list_floors_text(object_id):
    """Текстовый список помещений объекта — дерево."""
    roots = get_root_floors(object_id)
    if not roots:
        return "_Пока помещений нет._"
    lines = []
    def walk(fl, depth, is_last):
        indent = "    " * depth
        if depth == 0:
            prefix = ""
        else:
            prefix = "└─ " if is_last else "├─ "
        lines.append(indent + prefix + format_floor(fl))
        children = get_children(fl["id"])
        for idx, c in enumerate(children):
            walk(c, depth + 1, idx == len(children) - 1)
    for idx, r in enumerate(roots):
        walk(r, 0, idx == len(roots) - 1)
    return chr(10).join(lines)

