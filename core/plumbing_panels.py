"""core.plumbing_panels — Сантехнические коллекторы."""
from core.db import fetchone, fetchall, commit


PANEL_TYPES = {
    'collector': 'Коллектор',
    'riser': 'Стояк',
    'boiler': 'Котёл',
    'pump': 'Насосная группа',
    'filter': 'Фильтр',
}

MOUNT_TYPES = {
    'wall': 'На стене',
    'floor': 'На полу',
    'ceiling': 'На потолке',
    'niche': 'В нише',
}


def get_panel_type_label(code):
    return PANEL_TYPES.get(code, code or '—')


def get_mount_type_label(code):
    return MOUNT_TYPES.get(code, code or '—')


def create_panel(object_id, name, panel_type='collector', floor_id=None,
                 room_id=None, parent_panel_id=None, mount_type='wall', note=None):
    return commit(
        """INSERT INTO plumbing_panels
           (object_id, floor_id, room_id, name, panel_type, parent_panel_id, mount_type, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, floor_id, room_id, name, panel_type, parent_panel_id, mount_type, note)
    )


def get_panel(panel_id):
    row = fetchone("SELECT * FROM plumbing_panels WHERE id = ?", (panel_id,))
    return dict(row) if row else None


def get_panels(object_id):
    rows = fetchall("SELECT * FROM plumbing_panels WHERE object_id = ? ORDER BY id", (object_id,))
    return [dict(r) for r in rows]


def get_panels_by_floor(floor_id):
    rows = fetchall("SELECT * FROM plumbing_panels WHERE floor_id = ? ORDER BY id", (floor_id,))
    return [dict(r) for r in rows]


def get_child_panels(panel_id):
    rows = fetchall("SELECT * FROM plumbing_panels WHERE parent_panel_id = ? ORDER BY id", (panel_id,))
    return [dict(r) for r in rows]


def get_parent_panel(panel_id):
    p = get_panel(panel_id)
    if not p or not p.get('parent_panel_id'):
        return None
    return get_panel(p['parent_panel_id'])


def update_panel(panel_id, **kwargs):
    allowed = {"name", "panel_type", "floor_id", "room_id",
               "parent_panel_id", "mount_type", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(k + " = ?")
            params.append(v)
    if not fields:
        return False
    params.append(panel_id)
    commit("UPDATE plumbing_panels SET " + ", ".join(fields) + " WHERE id = ?", params)
    return True


def delete_panel(panel_id):
    commit("UPDATE plumbing_panels SET parent_panel_id = NULL WHERE parent_panel_id = ?", (panel_id,))
    commit("DELETE FROM plumbing_routes WHERE panel_id = ?", (panel_id,))
    commit("DELETE FROM plumbing_panels WHERE id = ?", (panel_id,))
    return True


def format_panel(p):
    lines = [(p.get('name') or '?') + ' (' + get_panel_type_label(p.get('panel_type')) + ')']
    if p.get('mount_type'):
        lines.append('   Монтаж: ' + get_mount_type_label(p.get('mount_type')))
    if p.get('note'):
        lines.append('   ' + str(p['note']))
    return chr(10).join(lines)


# --- ТРАССЫ ---

def create_route(object_id, panel_id, from_point_id=None, to_point_id=None,
                 pipe_type=None, length_m=None, route_type=None,
                 waypoints=None, is_manual=0, note=None):
    import json
    wp = json.dumps(waypoints, ensure_ascii=False) if waypoints else None
    return commit(
        """INSERT INTO plumbing_routes
           (object_id, panel_id, from_point_id, to_point_id,
            pipe_type, length_m, route_type, waypoints, is_manual, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, panel_id, from_point_id, to_point_id,
         pipe_type, length_m, route_type, wp, is_manual, note)
    )


def get_routes_by_panel(panel_id):
    rows = fetchall("SELECT * FROM plumbing_routes WHERE panel_id = ? ORDER BY id", (panel_id,))
    return [dict(r) for r in rows]


def delete_route(route_id):
    commit("DELETE FROM plumbing_routes WHERE id = ?", (route_id,))
    return True


def format_route(r):
    pipe = r.get('pipe_type') or '—'
    length = r.get('length_m') or 0
    route = r.get('route_type') or '—'
    return pipe + ': ' + str(length) + ' м (' + route + ')'


def get_summary(object_id):
    panels = get_panels(object_id)
    total_panels = len(panels)
    return {'panels_count': total_panels}
