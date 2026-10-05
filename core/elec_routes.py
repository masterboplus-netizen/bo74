"""core.elec_routes — Трассы ЭОМ (метраж от щитов к точкам).

Сейчас: метраж по прямой (waypoints = NULL).
Будущее: автотрассировка (waypoints = JSON со списком точек).
"""
from core.db import fetchone, fetchall, commit


# ============================================================
# CRUD ТРАСС
# ============================================================

def create_route(object_id, panel_id, group_id=None, from_point_id=None,
                to_point_id=None, cable_type=None, length_m=None,
                route_type=None, waypoints=None, is_manual=0, note=None):
    """Создаёт трассу. Возвращает route_id."""
    import json
    wp_json = json.dumps(waypoints, ensure_ascii=False) if waypoints else None
    return commit(
        """INSERT INTO elec_routes
           (object_id, panel_id, group_id, from_point_id, to_point_id,
            cable_type, length_m, route_type, waypoints, is_manual, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, panel_id, group_id, from_point_id, to_point_id,
         cable_type, length_m, route_type, wp_json, is_manual, note)
    )


def get_route(route_id):
    row = fetchone("SELECT * FROM elec_routes WHERE id = ?", (route_id,))
    if not row:
        return None
    d = dict(row)
    _decode_waypoints(d)
    return d


def get_routes_by_object(object_id):
    rows = fetchall(
        "SELECT * FROM elec_routes WHERE object_id = ? ORDER BY id",
        (object_id,)
    )
    return [_decode_row(dict(r)) for r in rows]


def get_routes_by_panel(panel_id):
    rows = fetchall(
        "SELECT * FROM elec_routes WHERE panel_id = ? ORDER BY id",
        (panel_id,)
    )
    return [_decode_row(dict(r)) for r in rows]


def get_routes_by_group(group_id):
    rows = fetchall(
        "SELECT * FROM elec_routes WHERE group_id = ? ORDER BY id",
        (group_id,)
    )
    return [_decode_row(dict(r)) for r in rows]


def delete_route(route_id):
    commit("DELETE FROM elec_routes WHERE id = ?", (route_id,))
    return True


def delete_routes_by_group(group_id, only_auto=True):
    """Удаляет трассы группы. only_auto=True — только автоматические."""
    if only_auto:
        commit("DELETE FROM elec_routes WHERE group_id = ? AND is_manual = 0", (group_id,))
    else:
        commit("DELETE FROM elec_routes WHERE group_id = ?", (group_id,))
    return True


def update_route(route_id, **kwargs):
    allowed = {"cable_type", "length_m", "route_type", "waypoints",
               "is_manual", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(k + " = ?")
            params.append(v)
    if not fields:
        return False
    params.append(route_id)
    commit("UPDATE elec_routes SET " + ", ".join(fields) + " WHERE id = ?", params)
    return True


# ============================================================
# РАСЧЁТ МЕТРАЖА (ПО ПРЯМОЙ)
# ============================================================

def calc_distance_m(x1, y1, z1, x2, y2, z2):
    """Расстояние между двумя точками в 3D. Вход в СМ, выход в М."""
    import math
    if x1 is None or y1 is None or x2 is None or y2 is None:
        return None
    z1 = z1 or 0
    z2 = z2 or 0
    d_cm = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
    return round(d_cm / 100.0, 2)


def calc_route_length_from_panel(panel_id, point_id):
    """Считает расстояние щит->точка по прямой.

    Использует:
    - координаты щита (если есть)
    - координаты точки (room_comms.world_x/y/z)
    - Если координат нет — возвращает None
    """
    from core.elec_panels import get_panel
    p = get_panel(panel_id)
    if not p:
        return None

    # Координаты щита (если есть)
    panel_x = p.get('lat')  # пока используем lat/lon как временные поля
    panel_y = p.get('lon')
    panel_z = 0

    # Координаты точки
    row = fetchone(
        "SELECT world_x, world_y, world_z, offset_x, offset_y, wall, room_id FROM room_comms WHERE id = ?",
        (point_id,)
    )
    if not row:
        return None

    pt_x = row['world_x']
    pt_y = row['world_y']
    pt_z = row['world_z']

    # Если world_x/y/z нет — считаем из offset_x/y + wall через geometry
    if pt_x is None or pt_y is None:
        offset_x = row['offset_x']
        offset_y = row['offset_y']
        wall = row['wall']
        room_id = row['room_id']
        if offset_x is not None and wall and room_id:
            try:
                from core.geometry import wall_offset_to_world
                from core.measures import get_walls_ordered
                walls = get_walls_ordered(room_id)
                wall_obj = next((w for w in walls if w.get('wall_pos') == wall), None)
                if wall_obj:
                    pt_x, pt_y, pt_z = wall_offset_to_world(wall_obj, offset_x, offset_y or 0)
            except Exception as e:
                print("route world calc: " + str(e), flush=True)

    if pt_x is None or pt_y is None:
        return None

    if panel_x is None:
        panel_x = 0
    if panel_y is None:
        panel_y = 0

    return calc_distance_m(panel_x, panel_y, panel_z, pt_x, pt_y, pt_z)


def auto_routes_for_group(group_id, cable_type=None, route_type=None):
    """Авто-создание трасс от щита к каждой точке группы.

    1. Читает группу
    2. Читает точки группы (room_comms.group_id)
    3. Для каждой точки — считает метраж от щита по прямой
    4. Создаёт трассу (is_manual=0)

    Возвращает dict: {'created': N, 'skipped': M, 'total_m': X}
    """
    from core.elec_panels import get_panel
    from core.elec import get_group

    g = get_group(group_id)
    if not g:
        return {'created': 0, 'skipped': 0, 'total_m': 0, 'error': 'group not found'}

    panel_id = g.get('panel_id')
    if not panel_id:
        return {'created': 0, 'skipped': 0, 'total_m': 0, 'error': 'group has no panel'}

    p = get_panel(panel_id)
    if not p:
        return {'created': 0, 'skipped': 0, 'total_m': 0, 'error': 'panel not found'}

    object_id = p.get('object_id')

    # Точки группы
    points = fetchall(
        "SELECT id, comm_type, label FROM room_comms WHERE group_id = ? ORDER BY id",
        (group_id,)
    )

    # Удаляем старые авто-трассы этой группы
    delete_routes_by_group(group_id, only_auto=True)

    # Номинал кабеля из группы
    if not cable_type:
        cable_type = g.get('cable_type')

    created = 0
    skipped = 0
    total_m = 0.0

    for pt in points:
        point_id = pt['id']
        length = calc_route_length_from_panel(panel_id, point_id)
        if length is None or length <= 0:
            skipped += 1
            continue
        create_route(
            object_id=object_id,
            panel_id=panel_id,
            group_id=group_id,
            from_point_id=None,
            to_point_id=point_id,
            cable_type=cable_type,
            length_m=length,
            route_type=route_type,
            waypoints=None,
            is_manual=0,
        )
        created += 1
        total_m += length

    return {
        'created': created,
        'skipped': skipped,
        'total_m': round(total_m, 2),
    }


def auto_routes_for_panel(panel_id, route_type=None):
    """Авто-создание трасс для всех групп щита."""
    from core.elec_panels import get_groups_by_panel

    groups = get_groups_by_panel(panel_id)
    total_created = 0
    total_m = 0.0
    for g in groups:
        res = auto_routes_for_group(g['id'], route_type=route_type)
        total_created += res.get('created', 0)
        total_m += res.get('total_m', 0)
    return {
        'groups': len(groups),
        'created': total_created,
        'total_m': round(total_m, 2),
    }


# ============================================================
# ФОРМАТИРОВАНИЕ
# ============================================================

ROUTE_TYPES_RU = {
    'shtroba': 'штроба',
    'potolok': 'потолок',
    'styazhka': 'стяжка',
    'lotok': 'лоток',
    'otkryto': 'открыто',
    None: '—',
}


def format_route(r):
    """Строка описания трассы."""
    cable = r.get('cable_type') or '—'
    length = r.get('length_m') or 0
    route = ROUTE_TYPES_RU.get(r.get('route_type'), r.get('route_type') or '—')
    manual = ' [ручная]' if r.get('is_manual') else ''
    return cable + ': ' + str(length) + ' м (' + route + ')' + manual


def summarize_routes_by_cable(panel_id=None, group_id=None):
    """Суммарная длина по типам кабеля.

    Один из panel_id / group_id должен быть задан.
    """
    if group_id:
        routes = get_routes_by_group(group_id)
    elif panel_id:
        routes = get_routes_by_panel(panel_id)
    else:
        return {}

    summary = {}
    for r in routes:
        ctype = r.get('cable_type') or 'без типа'
        summary[ctype] = summary.get(ctype, 0) + (r.get('length_m') or 0)
    return {k: round(v, 2) for k, v in summary.items()}


def format_routes_summary(panel_id=None, group_id=None):
    """Текстовая сводка по трассам."""
    if group_id:
        routes = get_routes_by_group(group_id)
        header = "Трассы группы"
    elif panel_id:
        routes = get_routes_by_panel(panel_id)
        header = "Трассы щита"
    else:
        return "Не задан ни щит, ни группа"

    if not routes:
        return header + ": нет трасс"

    lines = [header + ": " + str(len(routes)) + " шт.", ""]
    total = 0
    for idx, r in enumerate(routes[:20], start=1):
        lines.append(str(idx) + ". " + format_route(r))
        total += (r.get('length_m') or 0)
    if len(routes) > 20:
        lines.append("... ещё " + str(len(routes) - 20))
    lines.append("")
    lines.append("📊 Суммарно: " + str(round(total, 2)) + " м")
    lines.append("")
    lines.append("По типам кабеля:")
    by_cable = summarize_routes_by_cable(panel_id=panel_id, group_id=group_id)
    for ctype, length in sorted(by_cable.items(), key=lambda x: -x[1]):
        lines.append("  " + ctype + ": " + str(length) + " м")
    return chr(10).join(lines)


# ============================================================
# ВНУТРЕННИЕ
# ============================================================

def _decode_waypoints(d):
    """Декодирует JSON waypoints в dict."""
    import json
    wp = d.get('waypoints')
    if wp:
        try:
            d['waypoints'] = json.loads(wp)
        except Exception:
            pass
    return d


def _decode_row(d):
    return _decode_waypoints(d)


# ============================================================
# СМЕТА ЭЛЕКТРОМОНТАЖА (кабель + расходники)
# ============================================================

def calc_route_cost(route_id, with_consumables=True):
    """Стоимость одной трассы: кабель + (опц.) расходники.

    Возвращает dict: {length_m, cable_type, route_type,
                      cable_price_per_m, cable_cost, consumable_cost, total}
    """
    from core import spec

    r = get_route(route_id)
    if not r:
        return None

    length = r.get('length_m') or 0
    ctype = r.get('cable_type')
    rtype = r.get('route_type')

    cable_price = spec.get_cable_price(ctype)
    cable_cost = round(length * cable_price, 2)

    consumable_cost = 0.0
    if with_consumables and rtype:
        cons_price = spec.get_consumable_price(rtype)
        consumable_cost = round(length * cons_price, 2)

    return {
        'length_m': length,
        'cable_type': ctype,
        'route_type': rtype,
        'cable_price_per_m': cable_price,
        'cable_cost': cable_cost,
        'consumable_cost': consumable_cost,
        'total': round(cable_cost + consumable_cost, 2),
    }


def calc_montage_cost_by_group(group_id, with_consumables=True):
    """Смета электромонтажа по группе."""
    routes = get_routes_by_group(group_id)
    total_cable = 0.0
    total_cons = 0.0
    total_m = 0.0
    by_cable = {}
    by_route = {}
    for r in routes:
        c = calc_route_cost(r['id'], with_consumables=with_consumables)
        if not c:
            continue
        total_cable += c['cable_cost']
        total_cons += c['consumable_cost']
        total_m += c['length_m']
        ctype = c['cable_type'] or 'без типа'
        by_cable[ctype] = by_cable.get(ctype, 0) + c['cable_cost']
        rtype = c['route_type'] or 'без типа'
        by_route[rtype] = by_route.get(rtype, 0) + c['consumable_cost']
    return {
        'routes_count': len(routes),
        'total_m': round(total_m, 2),
        'total_cable_cost': round(total_cable, 2),
        'total_consumable_cost': round(total_cons, 2),
        'total': round(total_cable + total_cons, 2),
        'by_cable': {k: round(v, 2) for k, v in by_cable.items()},
        'by_route': {k: round(v, 2) for k, v in by_route.items()},
    }


def calc_montage_cost_by_panel(panel_id, with_consumables=True):
    """Смета электромонтажа по щиту (все группы щита)."""
    from core.elec_panels import get_groups_by_panel
    groups = get_groups_by_panel(panel_id)
    total_cable = 0.0
    total_cons = 0.0
    total_m = 0.0
    total_routes = 0
    by_cable = {}
    by_route = {}
    for g in groups:
        s = calc_montage_cost_by_group(g['id'], with_consumables=with_consumables)
        total_cable += s['total_cable_cost']
        total_cons += s['total_consumable_cost']
        total_m += s['total_m']
        total_routes += s.get('routes_count', 0)
        for k, v in s['by_cable'].items():
            by_cable[k] = by_cable.get(k, 0) + v
        for k, v in s['by_route'].items():
            by_route[k] = by_route.get(k, 0) + v
    return {
        'routes_count': total_routes,
        'total_m': round(total_m, 2),
        'total_cable_cost': round(total_cable, 2),
        'total_consumable_cost': round(total_cons, 2),
        'total': round(total_cable + total_cons, 2),
        'by_cable': {k: round(v, 2) for k, v in by_cable.items()},
        'by_route': {k: round(v, 2) for k, v in by_route.items()},
    }


def format_montage_cost_summary(panel_id=None, group_id=None):
    """Текстовая смета электромонтажа (кабель + расходники)."""
    if group_id:
        s = calc_montage_cost_by_group(group_id)
        header = "🔧 Смета электромонтажа (группа)"
    elif panel_id:
        s = calc_montage_cost_by_panel(panel_id)
        header = "🔧 Смета электромонтажа (щит)"
    else:
        return "Не задан ни щит, ни группа"

    lines = [header, ""]
    lines.append("Трасс: " + str(s.get('routes_count', '-')) + " · Метраж: " + str(s['total_m']) + " м")
    lines.append("")
    lines.append("По типам кабеля:")
    if s['by_cable']:
        for ctype, cost in sorted(s['by_cable'].items(), key=lambda x: -x[1]):
            lines.append("  " + str(ctype) + ": " + str(cost) + " ₽")
    else:
        lines.append("  нет")
    lines.append("")
    lines.append("По типам прокладки:")
    if s['by_route']:
        for rtype, cost in sorted(s['by_route'].items(), key=lambda x: -x[1]):
            lines.append("  " + str(rtype) + ": " + str(cost) + " ₽")
    else:
        lines.append("  нет")
    lines.append("")
    lines.append("Кабель: " + str(s['total_cable_cost']) + " ₽")
    lines.append("Расходники: " + str(s['total_consumable_cost']) + " ₽")
    lines.append("")
    lines.append("💰 ИТОГО: " + str(s['total']) + " ₽")
    return chr(10).join(lines)
