"""core.comms — коммуникации комнат (вода, свет, вентиляция)."""
from core.db import fetchone, fetchall, commit


COMM_TYPES = [
    ("water_cold", "💧 ХВС", "cold water"),
    ("water_hot",  "🔥 ГВС", "hot water"),
    ("sewer",      "🚽 Слив", "sewer"),
    ("heating",    "♨️ Отопление", "heating"),
    ("electric",   "⚡ Электрика", "electric"),
    ("gas",        "🔵 Газ", "gas"),
    ("vent",       "🌬 Вентиляция", "vent"),
    ("weak",       "📡 Слаботочка", "weak current"),
    ("drain",      "🚰 Дренаж", "drain"),
]

WALLS = [("A", "Стена A"), ("B", "Стена B"), ("C", "Стена C"), ("D", "Стена D")]


def add_comm(room_id, comm_type, label=None, wall=None,
             offset_x=None, offset_y=None, depth=None,
             diameter=None, voltage=None, note=None,
             photo_id=None, tenant_id=1, created_by=None):
    """Добавляет коммуникацию. Возвращает comm_id."""
    return commit(
        "INSERT INTO room_comms "
        "(room_id, comm_type, label, wall, offset_x, offset_y, depth, "
        "diameter, voltage, note, photo_id, tenant_id, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (room_id, comm_type, label, wall, offset_x, offset_y, depth,
         diameter, voltage, note, photo_id, tenant_id, created_by)
    )


def get_comm(comm_id):
    row = fetchone("SELECT * FROM room_comms WHERE id = ?", (comm_id,))
    return dict(row) if row else None


def get_comms(room_id, comm_type=None):
    """Все коммуникации комнаты (опц. фильтр по типу)."""
    if comm_type:
        rows = fetchall(
            "SELECT * FROM room_comms WHERE room_id = ? AND comm_type = ? ORDER BY id",
            (room_id, comm_type)
        )
    else:
        rows = fetchall(
            "SELECT * FROM room_comms WHERE room_id = ? ORDER BY comm_type, id",
            (room_id,)
        )
    return [dict(r) for r in rows]


def update_comm(comm_id, **kwargs):
    """Обновляет поля коммуникации."""
    allowed = {"label", "wall", "offset_x", "offset_y", "depth",
               "diameter", "voltage", "note", "photo_id", "comm_type"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(comm_id)
    commit(f"UPDATE room_comms SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_comm(comm_id):
    commit("DELETE FROM room_comms WHERE id = ?", (comm_id,))
    return True


def get_comm_type_label(comm_type):
    """Человекочитаемая метка типа."""
    for code, label, _ in COMM_TYPES:
        if code == comm_type:
            return label
    return comm_type or "—"


def format_comm(c):
    """Форматирует коммуникацию в строку."""
    label = get_comm_type_label(c.get('comm_type'))
    name = c.get('label') or label
    parts = []
    if c.get('wall'):
        parts.append(f"стена {c['wall']}")
    if c.get('offset_x') is not None:
        parts.append(f"X={c['offset_x']}м")
    if c.get('offset_y') is not None:
        parts.append(f"Y={c['offset_y']}м")
    if c.get('diameter'):
        parts.append(f"Ø{c['diameter']}мм")
    if c.get('voltage'):
        parts.append(c['voltage'])
    dims = ' · '.join(parts) if parts else '—'
    return f"{label} {name}: {dims}"


def group_comms_by_type(room_id):
    """Группирует коммуникации по типу."""
    comms = get_comms(room_id)
    grouped = {}
    for c in comms:
        t = c.get('comm_type') or 'other'
        grouped.setdefault(t, []).append(c)
    return grouped


def count_comms_by_type(room_id):
    """Считает количество по типам."""
    rows = fetchall(
        "SELECT comm_type, COUNT(*) as cnt FROM room_comms "
        "WHERE room_id = ? GROUP BY comm_type",
        (room_id,)
    )
    return {r['comm_type']: r['cnt'] for r in rows}
