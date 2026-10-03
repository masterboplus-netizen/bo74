"""core.niches — ниши в стенах."""
from core.db import fetchone, fetchall, commit


def add_niche(measure_id, room_id, name=None,
              offset_x=None, offset_y=None,
              width_bottom=None, width_top=None, height=None,
              depth_bottom=None, depth_top=None,
              niche_type='rect', note=None, session_id=None):
    """Добавляет нишу на стену. Возвращает niche_id."""
    return commit(
        """INSERT INTO wall_niches
           (measure_id, room_id, session_id, name,
            offset_x, offset_y,
            width_bottom, width_top, height,
            depth_bottom, depth_top,
            niche_type, note,
            world_x, world_y, world_z)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (measure_id, room_id, session_id, name,
         offset_x, offset_y,
         width_bottom, width_top, height,
         depth_bottom, depth_top,
         niche_type, note,
         None, None, None)
    )


def get_niche(niche_id):
    row = fetchone("SELECT * FROM wall_niches WHERE id = ?", (niche_id,))
    return dict(row) if row else None


def get_niches(measure_id):
    rows = fetchall(
        "SELECT * FROM wall_niches WHERE measure_id = ? ORDER BY id",
        (measure_id,)
    )
    return [dict(r) for r in rows]


def get_niches_by_room(room_id, session_id=None):
    if session_id:
        rows = fetchall(
            "SELECT * FROM wall_niches WHERE room_id = ? AND session_id = ? ORDER BY measure_id, id",
            (room_id, session_id)
        )
    else:
        rows = fetchall(
            "SELECT * FROM wall_niches WHERE room_id = ? ORDER BY measure_id, id",
            (room_id,)
        )
    return [dict(r) for r in rows]


def update_niche(niche_id, **kwargs):
    allowed = {"name", "offset_x", "offset_y", "width_bottom", "width_top",
               "height", "depth_bottom", "depth_top", "niche_type", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(niche_id)
    commit(f"UPDATE wall_niches SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_niche(niche_id):
    commit("DELETE FROM wall_niches WHERE id = ?", (niche_id,))
    return True


def format_niche(n):
    name = n.get('name') or 'Ниша'
    wb = n.get('width_bottom') or 0
    wt = n.get('width_top') or 0
    h = n.get('height') or 0
    db_ = n.get('depth_bottom') or 0
    dt = n.get('depth_top') or 0
    if abs(wb - wt) < 0.1 and abs(db_ - dt) < 0.1:
        return f"🕳 {name}: {int(wb)}×{int(h)}×{int(db_)} см"
    else:
        return (f"🕳 {name}: низ {int(wb)}×{int(db_)} см, "
                f"верх {int(wt)}×{int(dt)} см, высота {int(h)} см")
