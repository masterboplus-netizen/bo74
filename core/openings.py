"""core.openings — проёмы (окна, двери, вентиляция)."""
from core.db import fetchone, fetchall, commit

from core import spec as _spec
OPENING_TYPES = _spec.OPENING_TYPES


def add_opening(room_id, opening_type, wall_pos, offset_x=None,
                width=None, height=None, depth=None, sill_height=None,
                from_room_id=None, to_room_id=None, to_outside=0,
                is_main=0, vent_type=None, door_kind=None, note=None,
                session_id=None, tenant_id=1, created_by=None):
    """Добавляет проём. Возвращает opening_id."""
    return commit(
        """INSERT INTO openings
           (room_id, session_id, opening_type, wall_pos, offset_x,
            width, height, depth, sill_height,
            from_room_id, to_room_id, to_outside, is_main,
            vent_type, door_kind, note, tenant_id, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (room_id, session_id, opening_type, wall_pos, offset_x,
         width, height, depth, sill_height,
         from_room_id, to_room_id, to_outside, is_main,
         vent_type, door_kind, note, tenant_id, created_by)
    )


def get_opening(opening_id):
    row = fetchone("SELECT * FROM openings WHERE id = ?", (opening_id,))
    return dict(row) if row else None


def get_openings(room_id, session_id=None):
    if session_id:
        rows = fetchall(
            "SELECT * FROM openings WHERE room_id = ? AND session_id = ? ORDER BY id",
            (room_id, session_id)
        )
    else:
        rows = fetchall("SELECT * FROM openings WHERE room_id = ? ORDER BY id", (room_id,))
    return [dict(r) for r in rows]


def get_openings_by_wall(room_id, wall_pos, session_id=None):
    if session_id:
        rows = fetchall(
            "SELECT * FROM openings WHERE room_id = ? AND wall_pos = ? AND session_id = ? ORDER BY id",
            (room_id, wall_pos, session_id)
        )
    else:
        rows = fetchall(
            "SELECT * FROM openings WHERE room_id = ? AND wall_pos = ? ORDER BY id",
            (room_id, wall_pos)
        )
    return [dict(r) for r in rows]


def update_opening(opening_id, **kwargs):
    allowed = {"opening_type", "wall_pos", "offset_x", "width", "height",
               "depth", "sill_height", "from_room_id", "to_room_id",
               "to_outside", "is_main", "vent_type", "door_kind", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(opening_id)
    commit(f"UPDATE openings SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_opening(opening_id):
    commit("DELETE FROM openings WHERE id = ?", (opening_id,))
    return True


def get_opening_type_label(code):
    return OPENING_TYPES.get(code, code)


def format_opening(o):
    label = OPENING_TYPES.get(o.get('opening_type'), o.get('opening_type') or '?')
    parts = []
    if o.get('width'): parts.append(f"{int(o['width'])}")
    if o.get('height'): parts.append(f"{int(o['height'])}")
    dims = '×'.join(parts) if parts else '—'
    return f"{label} {dims} см"
