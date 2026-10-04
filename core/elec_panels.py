"""core.elec_panels — Щиты ЭОМ.

Щит = точка распределения питания. Один объект = N щитов:
- ВРУ (вводной) — один на объект
- Щит этажа — на каждом этаже / зоне
- Щит уличный — на улице (баня, гараж)
Связь щит <-> щит — через elec_panel_links.
"""
from core.db import fetchone, fetchall, commit


# ============================================================
# CRUD ЩИТОВ
# ============================================================

def create_panel(object_id, name, panel_type='floor',
                 floor_id=None, room_id=None, parent_panel_id=None,
                 mount_type='wall', input_breaker=None, meter_type=None,
                 lat=None, lon=None, note=None):
    """Создаёт щит. Возвращает panel_id."""
    return commit(
        """INSERT INTO elec_panels
           (object_id, floor_id, room_id, name, panel_type,
            parent_panel_id, mount_type, input_breaker, meter_type,
            lat, lon, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, floor_id, room_id, name, panel_type,
         parent_panel_id, mount_type, input_breaker, meter_type,
         lat, lon, note)
    )


def get_panel(panel_id):
    row = fetchone("SELECT * FROM elec_panels WHERE id = ?", (panel_id,))
    return dict(row) if row else None


def get_panels(object_id):
    """Все щиты объекта (сортировка по типу: сначала ВРУ)."""
    rows = fetchall(
        """SELECT * FROM elec_panels WHERE object_id = ?
           ORDER BY
             CASE panel_type
               WHEN 'vru' THEN 0
               WHEN 'floor' THEN 1
               WHEN 'apartment' THEN 2
               WHEN 'outdoor' THEN 3
               ELSE 9
             END,
             floor_id, id""",
        (object_id,)
    )
    return [dict(r) for r in rows]


def get_panels_by_floor(floor_id):
    rows = fetchall(
        "SELECT * FROM elec_panels WHERE floor_id = ? ORDER BY id",
        (floor_id,)
    )
    return [dict(r) for r in rows]


def update_panel(panel_id, **kwargs):
    allowed = {"name", "panel_type", "floor_id", "room_id",
               "parent_panel_id", "mount_type", "input_breaker",
               "meter_type", "lat", "lon", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(k + " = ?")
            params.append(v)
    if not fields:
        return False
    params.append(panel_id)
    commit("UPDATE elec_panels SET " + ", ".join(fields) + " WHERE id = ?", params)
    return True


def delete_panel(panel_id):
    """Удаляет щит. Группы отвязывает, дочерние щиты отвязывает."""
    commit("UPDATE elec_groups SET panel_id = NULL WHERE panel_id = ?", (panel_id,))
    commit("UPDATE elec_panels SET parent_panel_id = NULL WHERE parent_panel_id = ?", (panel_id,))
    commit("DELETE FROM elec_panel_links WHERE parent_panel_id = ? OR child_panel_id = ?",
           (panel_id, panel_id))
    commit("DELETE FROM elec_panels WHERE id = ?", (panel_id,))
    return True


# ============================================================
# СВЯЗИ ЩИТ <-> ЩИТ
# ============================================================

def link_panels(parent_panel_id, child_panel_id, cable_type=None,
                length_m=None, route_type=None, note=None):
    """Связывает родительский щит с дочерним (питание). Возвращает link_id."""
    return commit(
        """INSERT INTO elec_panel_links
           (parent_panel_id, child_panel_id, cable_type, length_m, route_type, note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (parent_panel_id, child_panel_id, cable_type, length_m, route_type, note)
    )


def get_parent_panel(panel_id):
    """Возвращает родительский щит или None."""
    p = get_panel(panel_id)
    if not p:
        return None
    parent_id = p.get('parent_panel_id')
    if not parent_id:
        return None
    return get_panel(parent_id)


def get_child_panels(panel_id):
    """Возвращает все дочерние щиты."""
    rows = fetchall(
        "SELECT * FROM elec_panels WHERE parent_panel_id = ? ORDER BY id",
        (panel_id,)
    )
    return [dict(r) for r in rows]


def get_panel_links(panel_id):
    """Все связи щита (входящие + исходящие)."""
    rows = fetchall(
        """SELECT * FROM elec_panel_links
           WHERE parent_panel_id = ? OR child_panel_id = ?
           ORDER BY id""",
        (panel_id, panel_id)
    )
    return [dict(r) for r in rows]


# ============================================================
# ДЕРЕВО ЩИТОВ (для визуализации)
# ============================================================

def get_panel_tree(object_id):
    """Возвращает дерево щитов объекта.

    Формат: [{'panel': {...}, 'children': [...]}, ...]
    Корни — щиты без parent_panel_id (обычно ВРУ).
    """
    panels = get_panels(object_id)
    by_id = {p['id']: p for p in panels}
    children = {}
    roots = []
    for p in panels:
        parent_id = p.get('parent_panel_id')
        if parent_id and parent_id in by_id:
            children.setdefault(parent_id, []).append(p)
        else:
            roots.append(p)

    def build(panel):
        return {
            'panel': panel,
            'children': [build(c) for c in children.get(panel['id'], [])]
        }

    return [build(r) for r in roots]


# ============================================================
# СВЯЗЬ ЩИТ <-> ГРУППА
# ============================================================

def assign_group_to_panel(group_id, panel_id):
    """Привязывает группу к щиту."""
    commit("UPDATE elec_groups SET panel_id = ? WHERE id = ?", (panel_id, group_id))
    return True


def unassign_group_from_panel(group_id):
    """Отвязывает группу от щита."""
    commit("UPDATE elec_groups SET panel_id = NULL WHERE id = ?", (group_id,))
    return True


def get_groups_by_panel(panel_id):
    """Все группы щита."""
    rows = fetchall(
        "SELECT * FROM elec_groups WHERE panel_id = ? ORDER BY id",
        (panel_id,)
    )
    return [dict(r) for r in rows]


def calc_panel_load(panel_id):
    """Суммарная нагрузка щита (Вт)."""
    groups = get_groups_by_panel(panel_id)
    return sum(int(g.get('load_watt') or 0) for g in groups)


def calc_object_total_load(object_id):
    """Суммарная нагрузка объекта по всем щитам."""
    panels = get_panels(object_id)
    return sum(calc_panel_load(p['id']) for p in panels)


# ============================================================
# ФОРМАТИРОВАНИЕ
# ============================================================

PANEL_TYPES = {
    'vru':       'ВРУ (вводно-распределительное)',
    'floor':     'Щит этажа',
    'apartment': 'Щит квартиры',
    'outdoor':   'Уличный щит',
}

MOUNT_TYPES = {
    'wall':         'На стене',
    'floor':        'На полу',
    'outdoor_pole': 'На столбе (улица)',
    'outdoor_box':  'Уличный бокс',
}


def get_panel_type_label(code):
    return PANEL_TYPES.get(code, code or '—')


def get_mount_type_label(code):
    return MOUNT_TYPES.get(code, code or '—')


def format_panel(p, show_load=True):
    """Форматирует щит в строку."""
    ptype = get_panel_type_label(p.get('panel_type'))
    name = p.get('name') or '—'
    lines = ['⚡ ' + name + ' (' + ptype + ')']

    mount = get_mount_type_label(p.get('mount_type'))
    if mount:
        lines.append('   Монтаж: ' + mount)

    if p.get('input_breaker'):
        lines.append('   Вводной: ' + str(p['input_breaker']))
    if p.get('meter_type'):
        lines.append('   Счётчик: ' + str(p['meter_type']))

    if show_load:
        try:
            load = calc_panel_load(p['id'])
            groups = get_groups_by_panel(p['id'])
            lines.append('   Групп: ' + str(len(groups)) + ' / Нагрузка: ' + str(load) + ' Вт')
        except Exception:
            pass

    if p.get('lat') and p.get('lon'):
        lines.append('   Координаты: ' + str(p['lat']) + ', ' + str(p['lon']))

    if p.get('note'):
        lines.append('   ' + str(p['note']))

    return chr(10).join(lines)


def format_panel_short(p):
    """Короткая строка для кнопки."""
    ptype = get_panel_type_label(p.get('panel_type'))
    name = p.get('name') or '—'
    return name + ' · ' + ptype


def get_panel_summary(panel_id):
    """Сводка по щиту для карточки."""
    p = get_panel(panel_id)
    if not p:
        return None
    groups = get_groups_by_panel(panel_id)
    return {
        'panel': p,
        'groups': groups,
        'groups_count': len(groups),
        'total_load_watt': calc_panel_load(panel_id),
        'parent': get_parent_panel(panel_id),
        'children': get_child_panels(panel_id),
    }
