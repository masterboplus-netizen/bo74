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


# ============================================================
# ТРАССЫ + СМЕТА САНТЕХНИКИ
# ============================================================

PIPE_PRICES_DEFAULT = {
    'ppr20': 120,      # полипропилен 20 мм
    'ppr25': 180,      # полипропилен 25 мм
    'ppr32': 250,      # полипропилен 32 мм
    'pex16': 150,      # PEX 16 мм
    'pex20': 200,      # PEX 20 мм
    'copper15': 450,   # медь 15 мм
    'copper22': 650,   # медь 22 мм
    'sewer50': 250,    # канализация 50 мм
    'sewer110': 450,   # канализация 110 мм
}

PIPE_LABELS = {
    'ppr20': 'PPR 20 мм',
    'ppr25': 'PPR 25 мм',
    'ppr32': 'PPR 32 мм',
    'pex16': 'PEX 16 мм',
    'pex20': 'PEX 20 мм',
    'copper15': 'Медь 15 мм',
    'copper22': 'Медь 22 мм',
    'sewer50': 'Канализация 50 мм',
    'sewer110': 'Канализация 110 мм',
}

PLUMB_CONSUMABLE_PRICES = {
    'shtroba': 200,     # штробление
    'gofra': 30,        # гофра
    'klipsa': 15,       # клипсы
    'otkryto': 50,      # открыто
    'styazhka': 100,    # в стяжке
}


def get_pipe_price(pipe_type):
    return PIPE_PRICES_DEFAULT.get(pipe_type, 0)


def get_plumb_consumable_price(route_type):
    return PLUMB_CONSUMABLE_PRICES.get(route_type, 0)


def get_pipe_label(pipe_type):
    return PIPE_LABELS.get(pipe_type, pipe_type or '—')


def calc_route_cost(route_id, with_consumables=True):
    """Стоимость одной трассы сантехники (труба + расходники)."""
    import json
    row = fetchone("SELECT * FROM plumbing_routes WHERE id = ?", (route_id,))
    if not row:
        return None
    r = dict(row)
    length = r.get('length_m') or 0
    pipe = r.get('pipe_type')
    rtype = r.get('route_type')

    pipe_price = get_pipe_price(pipe)
    pipe_cost = round(length * pipe_price, 2)

    cons = 0.0
    if with_consumables and rtype:
        cons = round(length * get_plumb_consumable_price(rtype), 2)

    return {
        'length_m': length,
        'pipe_type': pipe,
        'route_type': rtype,
        'pipe_price_per_m': pipe_price,
        'pipe_cost': pipe_cost,
        'consumable_cost': cons,
        'total': round(pipe_cost + cons, 2),
    }


def calc_montage_cost_by_panel(panel_id, with_consumables=True):
    """Смета монтажа по коллектору."""
    routes = get_routes_by_panel(panel_id)
    total_pipe = 0.0
    total_cons = 0.0
    total_m = 0.0
    by_pipe = {}
    by_route = {}
    for r in routes:
        c = calc_route_cost(r['id'], with_consumables=with_consumables)
        if not c:
            continue
        total_pipe += c['pipe_cost']
        total_cons += c['consumable_cost']
        total_m += c['length_m']
        ptype = c['pipe_type'] or 'без типа'
        by_pipe[ptype] = by_pipe.get(ptype, 0) + c['pipe_cost']
        rtype = c['route_type'] or 'без типа'
        by_route[rtype] = by_route.get(rtype, 0) + c['consumable_cost']
    return {
        'routes_count': len(routes),
        'total_m': round(total_m, 2),
        'total_pipe_cost': round(total_pipe, 2),
        'total_consumable_cost': round(total_cons, 2),
        'total': round(total_pipe + total_cons, 2),
        'by_pipe': {k: round(v, 2) for k, v in by_pipe.items()},
        'by_route': {k: round(v, 2) for k, v in by_route.items()},
    }


def calc_object_cost(object_id):
    """Смета сантехники по объекту (трубы + расходники + работы)."""
    panels = get_panels(object_id)
    total_pipe = 0.0
    total_cons = 0.0
    total_m = 0.0
    total_routes = 0
    by_pipe = {}
    by_route = {}
    for p in panels:
        s = calc_montage_cost_by_panel(p['id'])
        total_pipe += s['total_pipe_cost']
        total_cons += s['total_consumable_cost']
        total_m += s['total_m']
        total_routes += s['routes_count']
        for k, v in s['by_pipe'].items():
            by_pipe[k] = by_pipe.get(k, 0) + v
        for k, v in s['by_route'].items():
            by_route[k] = by_route.get(k, 0) + v
    # Работы сантехники (по work_type префиксу plumb_)
    works_total = 0.0
    works_count = 0
    try:
        from core import object_works as _ow
        works = _ow.get_works_by_object(object_id)
        for w in works:
            if str(w.get('work_type') or '').startswith('plumb_'):
                works_total += w.get('total') or 0
                works_count += 1
    except Exception:
        pass
    return {
        'panels_count': len(panels),
        'routes_count': total_routes,
        'total_m': round(total_m, 2),
        'total_pipe_cost': round(total_pipe, 2),
        'total_consumable_cost': round(total_cons, 2),
        'works_total': round(works_total, 2),
        'works_count': works_count,
        'total': round(total_pipe + total_cons + works_total, 2),
        'by_pipe': {k: round(v, 2) for k, v in by_pipe.items()},
        'by_route': {k: round(v, 2) for k, v in by_route.items()},
    }


def format_object_cost(object_id):
    """Текстовая смета сантехники объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else ('Объект #' + str(object_id))
    data = calc_object_cost(object_id)

    lines = ["🔧 Смета сантехники «" + str(obj_name) + "»", ""]
    lines.append("Коллекторов: " + str(data['panels_count']))
    lines.append("Трасс: " + str(data['routes_count']))
    lines.append("Метраж: " + str(data['total_m']) + " м")
    lines.append("")
    lines.append("По типам труб:")
    if data['by_pipe']:
        for ptype, cost in sorted(data['by_pipe'].items(), key=lambda x: -x[1]):
            lines.append("  " + get_pipe_label(ptype) + ": " + str(cost) + " ₽")
    else:
        lines.append("  нет данных")
    lines.append("")
    lines.append("По типам прокладки:")
    if data['by_route']:
        for rtype, cost in sorted(data['by_route'].items(), key=lambda x: -x[1]):
            lines.append("  " + str(rtype) + ": " + str(cost) + " ₽")
    else:
        lines.append("  нет данных")
    lines.append("")
    lines.append("Трубы: " + str(data['total_pipe_cost']) + " ₽")
    lines.append("Расходники: " + str(data['total_consumable_cost']) + " ₽")
    lines.append("")
    lines.append("Работы сантехники:")
    if data.get('works_count'):
        lines.append("Всего работ: " + str(data['works_count']))
        lines.append("Итого работы: " + str(data['works_total']) + " ₽")
    else:
        lines.append("нет")
    lines.append("")
    lines.append("💰 ИТОГО: " + str(data['total']) + " ₽")
    return chr(10).join(lines)


def format_panel_cost(panel_id):
    """Смета монтажа по одному коллектору."""
    p = get_panel(panel_id)
    if not p:
        return "Коллектор не найден"
    data = calc_montage_cost_by_panel(panel_id)
    lines = ["🔧 Смета сантехники «" + str(p.get('name')) + "»", ""]
    lines.append("Трасс: " + str(data['routes_count']) + " · Метраж: " + str(data['total_m']) + " м")
    lines.append("")
    lines.append("По типам труб:")
    if data['by_pipe']:
        for ptype, cost in sorted(data['by_pipe'].items(), key=lambda x: -x[1]):
            lines.append("  " + get_pipe_label(ptype) + ": " + str(cost) + " ₽")
    else:
        lines.append("  нет данных")
    lines.append("")
    lines.append("Трубы: " + str(data['total_pipe_cost']) + " ₽")
    lines.append("Расходники: " + str(data['total_consumable_cost']) + " ₽")
    lines.append("")
    lines.append("💰 ИТОГО: " + str(data['total']) + " ₽")
    return chr(10).join(lines)


def format_panel_spec(panel_id):
    """Спецификация сантехники по коллектору (TXT-строка)."""
    from datetime import datetime
    from modules.objects import get_object
    p = get_panel(panel_id)
    if not p:
        return "Коллектор не найден"
    obj = get_object(p.get('object_id')) if p.get('object_id') else None
    obj_name = obj['name'] if obj else '—'
    routes = get_routes_by_panel(panel_id)
    data = calc_montage_cost_by_panel(panel_id)

    lines = []
    lines.append("=" * 60)
    lines.append("СПЕЦИФИКАЦИЯ САНТЕХНИКИ (коллектор)")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Объект:    " + str(obj_name))
    lines.append("Коллектор: " + str(p.get('name') or '?'))
    lines.append("Тип:       " + get_panel_type_label(p.get('panel_type')))
    lines.append("Дата:      " + datetime.now().strftime('%d.%m.%Y'))
    lines.append("")
    lines.append("-" * 60)
    lines.append("№  Труба                    Длина    Цена/м   Сумма")
    lines.append("-" * 60)

    if not routes:
        lines.append("(нет трасс)")
    else:
        for idx, r in enumerate(routes, start=1):
            pipe_label = get_pipe_label(r.get('pipe_type'))
            length = r.get('length_m') or 0
            price_m = get_pipe_price(r.get('pipe_type'))
            summa = round(length * price_m, 2)
            lines.append(
                str(idx).ljust(3) +
                pipe_label[:22].ljust(23) +
                str(length).rjust(6) +
                str(price_m).rjust(9) +
                str(summa).rjust(10)
            )

    lines.append("-" * 60)
    lines.append("Трубы:".ljust(45) + str(data['total_pipe_cost']).rjust(14) + " ₽")
    lines.append("Расходники:".ljust(45) + str(data['total_consumable_cost']).rjust(14) + " ₽")
    lines.append("ИТОГО:".ljust(45) + str(data['total']).rjust(14) + " ₽")
    lines.append("=" * 60)
    return chr(10).join(lines)
