"""core.comms — коммуникации комнат (вода, свет, вентиляция)."""
from core.db import fetchone, fetchall, commit


COMM_TYPES = [
    # Вода / канализация
    ("water_cold",   "💧 ХВС (холодная вода)", "cold water"),
    ("water_hot",    "🔥 ГВС (горячая вода)", "hot water"),
    ("sewer",        "🚽 Канализация", "sewer"),
    ("drain",        "🚰 Дренаж", "drain"),
    ("heating",      "♨️ Отопление", "heating"),
    ("gas",          "🔵 Газ", "gas"),
    ("vent",         "🌬 Вентиляция", "vent"),
    # Электрика (силовая)
    ("elec_panel",   "⚡ Щит / автоматы", "electric panel"),
    ("elec_socket",  "🔌 Розетка", "socket"),
    ("elec_switch",  "💡 Выключатель", "switch"),
    ("elec_cable",   "🔌 Вывод кабеля (свет)", "cable outlet"),
    # Слаботочка
    ("net_internet", "🌐 Интернет", "internet"),
    ("net_tv",       "📺 ТВ-кабель", "tv"),
    ("net_phone",    "📞 Телефон", "phone"),
    ("net_cctv",     "🎥 Видеонаблюдение", "cctv"),
    ("net_audio",    "🔊 Аудио", "audio"),
    ("net_domofon",  "🚪 Домофон", "domofon"),
    ("net_bell",     "🔔 Звонок", "bell"),
]

WALLS = [("A", "Стена A"), ("B", "Стена B"), ("C", "Стена C"), ("D", "Стена D")]


def add_comm(room_id, comm_type, label=None, wall=None,
             offset_x=None, offset_y=None, depth=None,
             diameter=None, voltage=None, size=None, note=None,
             photo_id=None, tenant_id=1, created_by=None):
    """Добавляет коммуникацию. Возвращает comm_id."""
    return commit(
        "INSERT INTO room_comms "
        "(room_id, comm_type, label, wall, offset_x, offset_y, depth, "
        "diameter, voltage, size, note, photo_id, tenant_id, created_by, "
        "session_id, world_x, world_y, world_z) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (room_id, comm_type, label, wall, offset_x, offset_y, depth,
         diameter, voltage, size, note, photo_id, tenant_id, created_by,
         session_id, None, None, None)
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
               "diameter", "voltage", "size", "note", "photo_id", "comm_type"}
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
    """Форматирует коммуникацию в строку (человекочитаемо)."""
    label = get_comm_type_label(c.get('comm_type'))
    name = c.get('label') or label

    def fmt_num(v):
        if v is None:
            return None
        return str(int(v)) if v == int(v) else str(round(v, 1))

    parts = []
    if c.get('wall'):
        parts.append(f"стена «{c['wall']}»")
    if c.get('offset_x') is not None:
        parts.append(f"от угла {fmt_num(c['offset_x'])} см")
    if c.get('offset_y') is not None:
        parts.append(f"от пола {fmt_num(c['offset_y'])} см")
    if c.get('diameter'):
        parts.append(f"Ø {fmt_num(c['diameter'])} мм")
    if c.get('voltage'):
        parts.append(f"{fmt_num(c['voltage'])} В")
    if c.get('size'):
        parts.append(f"{c['size']} см")
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
