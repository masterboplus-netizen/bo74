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


# ============================================================
# ВВОДНОЙ АВТОМАТ
# ============================================================

def set_input_breaker(panel_id, breaker_type=None, rating=None,
                     curve=None, poles=None, rcd_ma=None):
    """Устанавливает вводной автомат щита.

    breaker_type: auto / uzo / dif / switch
    rating: номинал (А)
    curve: B / C / D
    poles: 1 / 2 / 3 / 4
    rcd_ma: 10 / 30 / 100 / 300 (для uzo/dif)
    """
    fields, params = [], []
    for k, v in [
        ("input_breaker_type", breaker_type),
        ("input_breaker_rating", rating),
        ("input_breaker_curve", curve),
        ("input_breaker_poles", poles),
        ("input_breaker_rcd_ma", rcd_ma),
    ]:
        if v is not None:
            fields.append(k + " = ?")
            params.append(v)
    if not fields:
        return False
    params.append(panel_id)
    commit("UPDATE elec_panels SET " + ", ".join(fields) + " WHERE id = ?", params)
    return True


def get_input_breaker(panel_id):
    """Возвращает dict с полями вводного автомата или None."""
    p = get_panel(panel_id)
    if not p:
        return None
    return {
        'type': p.get('input_breaker_type'),
        'rating': p.get('input_breaker_rating'),
        'curve': p.get('input_breaker_curve'),
        'poles': p.get('input_breaker_poles'),
        'rcd_ma': p.get('input_breaker_rcd_ma'),
        'raw': p.get('input_breaker'),
    }


def format_input_breaker(panel_id):
    """Текстовая строка вводного автомата."""
    b = get_input_breaker(panel_id)
    if not b or not b.get('type'):
        return "не задан"
    parts = []
    type_labels = {
        'auto': 'Автомат',
        'uzo': 'УЗО',
        'dif': 'Дифавтомат',
        'switch': 'Рубильник',
    }
    parts.append(type_labels.get(b['type'], b['type']))
    if b.get('poles'):
        parts.append(str(b['poles']) + "P")
    if b.get('rating'):
        parts.append(str(b['rating']) + "А")
    if b.get('curve'):
        parts.append(b['curve'])
    if b.get('rcd_ma'):
        parts.append(str(b['rcd_ma']) + "мА")
    return " ".join(parts)


# ============================================================
# КОМПОНЕНТЫ ЩИТА
# ============================================================

def add_component(panel_id, component_type, component_model=None,
                  rating=None, curve=None, poles=None, rcd_ma=None,
                  quantity=1, linked_group_id=None, order_num=None,
                  is_manual=0, note=None):
    """Добавляет компонент в щит. Возвращает component_id."""
    return commit(
        """INSERT INTO elec_panel_components
           (panel_id, component_type, component_model, rating, curve,
            poles, rcd_ma, quantity, linked_group_id, order_num, is_manual, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (panel_id, component_type, component_model, rating, curve,
         poles, rcd_ma, quantity, linked_group_id, order_num, is_manual, note)
    )


def get_component(component_id):
    row = fetchone("SELECT * FROM elec_panel_components WHERE id = ?", (component_id,))
    return dict(row) if row else None


def get_components(panel_id):
    """Все компоненты щита."""
    rows = fetchall(
        "SELECT * FROM elec_panel_components WHERE panel_id = ? ORDER BY order_num, id",
        (panel_id,)
    )
    return [dict(r) for r in rows]


def get_components_by_group(group_id):
    rows = fetchall(
        "SELECT * FROM elec_panel_components WHERE linked_group_id = ? ORDER BY id",
        (group_id,)
    )
    return [dict(r) for r in rows]


def delete_component(component_id):
    commit("DELETE FROM elec_panel_components WHERE id = ?", (component_id,))
    return True


def clear_auto_components(panel_id):
    """Удаляет только автоматические компоненты (is_manual=0)."""
    commit("DELETE FROM elec_panel_components WHERE panel_id = ? AND is_manual = 0", (panel_id,))
    return True


def format_component(c):
    """Строка описания компонента."""
    type_labels = {
        'auto': '🔌 Автомат',
        'uzo': '🛡 УЗО',
        'dif': '🛡 Дифавтомат',
        'switch': '⚙️ Рубильник',
        'busbar': '📏 Шина',
        'clamp': '🔗 Клемма',
        'counter': '📊 Счётчик',
    }
    label = type_labels.get(c.get('component_type'), c.get('component_type') or '?')
    parts = [label]
    model = c.get('component_model')
    if model:
        parts.append(str(model))
    if c.get('poles'):
        parts.append(str(c['poles']) + "P")
    if c.get('rating'):
        parts.append(str(c['rating']) + "А")
    if c.get('curve'):
        parts.append(c['curve'])
    if c.get('rcd_ma'):
        parts.append(str(c['rcd_ma']) + "мА")
    q = c.get('quantity') or 1
    if q > 1:
        parts.append("x" + str(q))
    return " ".join(parts)


# ============================================================
# АВТОКОМПЛЕКТАЦИЯ ЩИТА
# ============================================================

def autocomplete_panel(panel_id, rules=None):
    """Автокомплектация щита.

    1. Удаляет старые АВТО компоненты (is_manual=0)
    2. Создаёт: вводной автомат, автоматы на группы, УЗО, шины, клеммы
    3. Сохраняет РУЧНЫЕ компоненты (is_manual=1)

    Возвращает dict: {'created': N, 'skipped': M, 'manual': K}
    """
    from core import elec_rules as rules_mod
    from core import elec as elec_mod

    p = get_panel(panel_id)
    if not p:
        return None

    object_id = p.get('object_id')
    if rules is None:
        rules = rules_mod.get_rules(object_id)

    # 1. Удаляем старые авто-компоненты
    clear_auto_components(panel_id)

    # 2. Считаем нагрузку
    groups = get_groups_by_panel(panel_id)
    total_watt = 0
    for g in groups:
        total_watt += int(g.get('load_watt') or 0)

    # Применяем одновременность
    total_watt_calc = total_watt * rules.get('simultaneity_factor', 0.8)

    created = 0
    order = 1

    # 3. Вводной автомат — только если НЕ задан вручную
    input_b = get_input_breaker(panel_id)
    if not input_b or not input_b.get('type'):
        phase_count = 1
        try:
            supply = elec_mod.get_supply(object_id) or {}
            phase_count = supply.get('phase_count') or 1
        except Exception:
            pass
        voltage = 380 if phase_count == 3 else 220

        if total_watt_calc > 0:
            current = elec_mod.calc_current(total_watt_calc, phase_count, voltage)
            rating = elec_mod.pick_breaker(total_watt_calc, phase_count,
                                            rules.get('default_curve', 'C'))[0]
            poles = 3 if phase_count == 3 else 1

            # Ограничение: 1-фазный максимум 63А
            max_1p = rules.get('max_breaker_1p', 63)
            if phase_count == 1 and rating > max_1p:
                rating = max_1p

            add_component(
                panel_id, 'auto',
                component_model=rules.get('auto_model'),
                rating=rating, curve=rules.get('default_curve', 'C'),
                poles=poles, quantity=1, order_num=order
            )
            # Дублируем вводной в поля щита (для селективности)
            set_input_breaker(panel_id, breaker_type='auto', rating=rating,
                              curve=rules.get('default_curve', 'C'), poles=poles)
            created += 1
            order += 1

            # УЗО на ввод (противопожарное)
            add_component(
                panel_id, 'uzo',
                component_model=rules.get('uzo_model'),
                rating=rating,
                poles=poles,
                rcd_ma=rules.get('rcd_input_ma', 100),
                quantity=1, order_num=order
            )
            created += 1
            order += 1

    # 4. Автоматы на группы
    for g in groups:
        group_load = int(g.get('load_watt') or 0)
        if group_load <= 0:
            continue
        phase = int(g.get('phase') or 1)
        voltage = 380 if phase == 3 else 220

        try:
            rating = elec_mod.pick_breaker(group_load, phase,
                                           rules.get('default_curve', 'C'))[0]
        except Exception:
            rating = 16

        # Минимальный номинал по назначению
        min_by_purpose = rules.get('min_rating_by_purpose') or {}
        purpose_key = g.get('purpose') or 'socket'
        min_rating = min_by_purpose.get(purpose_key, 6)
        if rating < min_rating:
            rating = min_rating

        poles = 3 if phase == 3 else 1

        # Автомат группы
        add_component(
            panel_id, 'auto',
            component_model=rules.get('auto_model'),
            rating=rating, curve=rules.get('default_curve', 'C'),
            poles=poles, quantity=1, linked_group_id=g['id'],
            order_num=order
        )
        created += 1
        order += 1

        # УЗО на группу — по назначению
        purpose = g.get('purpose') or 'socket'
        need_uzo = False
        if purpose == 'socket' and rules.get('uzo_sockets'):
            need_uzo = True
        elif purpose == 'kitchen' and rules.get('uzo_kitchen'):
            need_uzo = True
        elif purpose == 'light' and rules.get('uzo_lighting'):
            need_uzo = True
        elif purpose in ('bathroom', 'wet') and rules.get('uzo_bathroom'):
            need_uzo = True
        elif purpose == 'outdoor' and rules.get('uzo_outdoor'):
            need_uzo = True

        if need_uzo:
            add_component(
                panel_id, 'uzo',
                component_model=rules.get('uzo_model'),
                rating=rating,
                poles=poles,
                rcd_ma=rules.get('rcd_sockets_ma', 30),
                quantity=1, linked_group_id=g['id'],
                order_num=order
            )
            created += 1
            order += 1

    # 5. Шина N/PE (если не задана)
    existing_busbar = [c for c in get_components(panel_id)
                       if c.get('component_type') == 'busbar']
    if not existing_busbar:
        add_component(panel_id, 'busbar', component_model='Шина N/PE',
                      quantity=2, order_num=order)
        created += 1
        order += 1

    # 6. Клеммы на ввод
    add_component(panel_id, 'clamp', component_model='Клемма вводная',
                  quantity=4, order_num=order)

    manual_count = len([c for c in get_components(panel_id) if c.get('is_manual')])

    return {
        'created': created,
        'manual': manual_count,
        'total_watt': total_watt,
        'calc_watt': round(total_watt_calc, 1),
        'groups': len(groups),
    }


def recalc_panel(panel_id, rules=None):
    """Пересчёт щита (алиас autocomplete_panel)."""
    return autocomplete_panel(panel_id, rules=rules)


def format_panel_components(panel_id):
    """Полный текст комплектации щита (с нумерацией)."""
    p = get_panel(panel_id)
    if not p:
        return "Щит не найден"
    comps = get_components(panel_id)
    lines = ["🔧 Комплектация щита «" + str(p.get('name')) + "»", ""]

    # Группировка по типу
    by_type = {}
    for c in comps:
        t = c.get('component_type') or 'other'
        by_type.setdefault(t, []).append(c)

    # Сквозной счётчик по всем компонентам
    global_idx = 0
    type_order = ['auto', 'uzo', 'dif', 'switch', 'counter', 'busbar', 'clamp']
    for t in type_order:
        items = by_type.get(t)
        if not items:
            continue
        lines.append("── " + t.upper() + " ──")
        for c in items:
            global_idx += 1
            mark = " [ручной]" if c.get('is_manual') else ""
            lines.append("  " + str(global_idx) + ". " + format_component(c) + mark)
        lines.append("")

    # Прочие типы (если есть)
    for t, items in by_type.items():
        if t in type_order:
            continue
        lines.append("── " + t.upper() + " ──")
        for c in items:
            global_idx += 1
            mark = " [ручной]" if c.get('is_manual') else ""
            lines.append("  " + str(global_idx) + ". " + format_component(c) + mark)
        lines.append("")

    return chr(10).join(lines)


def get_panel_stats(panel_id):
    """Статистика щита: модули, компоненты, нагрузка."""
    comps = get_components(panel_id)
    modules = 0
    for c in comps:
        t = c.get('component_type')
        if t in ('auto', 'uzo', 'dif', 'switch'):
            poles = c.get('poles') or 1
            q = c.get('quantity') or 1
            modules += poles * q

    load = calc_panel_load(panel_id)
    groups = get_groups_by_panel(panel_id)

    return {
        'components_total': len(comps),
        'modules_used': modules,
        'groups_count': len(groups),
        'total_load_watt': load,
    }


# ============================================================
# СЕЛЕКТИВНОСТЬ
# ============================================================

def check_selectivity(panel_id, rules=None):
    """Проверяет селективность щита.

    Сравнивает вводной автомат с групповыми:
    вводной >= групповой * selectivity_factor.

    Возвращает dict:
    {
      'ok': bool,
      'issues': [{'group_id': N, 'group_rating': X, 'input_rating': Y, 'msg': '...'}],
      'input_rating': X,
      'min_input_required': Y
    }
    """
    from core import elec_rules as rules_mod

    p = get_panel(panel_id)
    if not p:
        return None

    if rules is None:
        rules = rules_mod.get_rules(p.get('object_id'))

    factor = rules.get('selectivity_factor', 1.6)

    input_b = get_input_breaker(panel_id)
    input_rating = (input_b.get('rating') if input_b else None) or 0

    # Групповые автоматы
    comps = get_components(panel_id)
    group_autos = [c for c in comps
                   if c.get('component_type') == 'auto' and c.get('linked_group_id')]

    issues = []
    max_group_rating = 0
    for c in group_autos:
        r = c.get('rating') or 0
        if r > max_group_rating:
            max_group_rating = r
        required = round(r * factor)
        if input_rating < required:
            issues.append({
                'group_id': c.get('linked_group_id'),
                'group_rating': r,
                'input_rating': input_rating,
                'required': required,
                'msg': 'Групповой ' + str(r) + 'А требует вводной >= ' + str(required) + 'А',
            })

    return {
        'ok': len(issues) == 0,
        'issues': issues,
        'input_rating': input_rating,
        'min_input_required': round(max_group_rating * factor),
    }


def format_selectivity(panel_id, rules=None):
    """Текстовая строка о селективности."""
    s = check_selectivity(panel_id, rules=rules)
    if not s:
        return "Селективность: неизвестно"
    if s['ok']:
        return "✅ Селективность OK (вводной " + str(s['input_rating']) + "А)"
    lines = ["⚠️ Селективность нарушена:"]
    for i in s['issues'][:5]:
        lines.append("   • " + i['msg'])
    lines.append("   Требуется вводной >= " + str(s['min_input_required']) + "А")
    return chr(10).join(lines)


# ============================================================
# ИЕРАРХИЯ ЩИТОВ (parent -> child)
# ============================================================

def add_child_panel(parent_panel_id, name, panel_type='floor',
                   mount_type='wall', breaker_rating=None,
                   breaker_poles=None, breaker_curve='C',
                   floor_id=None, room_id=None, note=None):
    """Создаёт дочерний щит + связывает с родителем.

    1. Создаёт новый щит
    2. Устанавливает parent_panel_id
    3. Создаёт в родителе компонент 'auto' (питание дочернего)
    4. Создаёт в дочернем компонент 'input' (вводной)
    5. Создаёт запись в elec_panel_links

    Возвращает child_panel_id или None.
    """
    parent = get_panel(parent_panel_id)
    if not parent:
        return None

    object_id = parent.get('object_id')
    if not object_id:
        return None

    # 1. Создаём дочерний щит
    child_id = create_panel(
        object_id=object_id,
        name=name,
        panel_type=panel_type,
        floor_id=floor_id,
        room_id=room_id,
        parent_panel_id=parent_panel_id,
        mount_type=mount_type,
        note=note,
    )
    if not child_id:
        return None

    # 2. Компоненты создаются после назначения номинала (шаг 3)
    if breaker_rating:
        _create_panel_link_with_components(
            parent_panel_id, child_id,
            breaker_rating=breaker_rating,
            breaker_poles=breaker_poles,
            breaker_curve=breaker_curve or 'C',
        )

    return child_id


def _create_panel_link_with_components(parent_panel_id, child_id,
                                      breaker_rating, breaker_poles=None,
                                      breaker_curve='C', cable_type=None,
                                      length_m=None, route_type=None):
    """Создаёт связь и оба компонента (в родителе и дочернем)."""
    poles = breaker_poles or 1

    # Компонент в родителе — групповой на дочерний щит
    add_component(
        parent_panel_id, 'auto',
        rating=breaker_rating, curve=breaker_curve, poles=poles,
        linked_group_id=None, order_num=999,
        note='Питание дочернего щита #' + str(child_id)
    )

    # Компонент в дочернем — вводной
    add_component(
        child_id, 'input',
        rating=breaker_rating, curve=breaker_curve, poles=poles,
        order_num=1,
        note='От родительского щита #' + str(parent_panel_id)
    )

    # Связь в elec_panel_links
    try:
        return commit(
            """INSERT INTO elec_panel_links
               (parent_panel_id, child_panel_id, cable_type, length_m, route_type,
                parent_breaker_rating, parent_breaker_poles, parent_breaker_curve,
                child_input_rating, is_primary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (parent_panel_id, child_id, cable_type, length_m, route_type,
             breaker_rating, poles, breaker_curve, breaker_rating)
        )
    except Exception as e:
        print("panel link: " + str(e), flush=True)
        return None


def set_panel_link_breaker(parent_panel_id, child_id, breaker_rating,
                          breaker_poles=None, breaker_curve='C',
                          cable_type=None, length_m=None, route_type=None):
    """Устанавливает номинал автомата между щитами (создаёт оба компонента)."""
    # Удаляем старые компоненты связи (только авто, не ручные)
    commit("DELETE FROM elec_panel_components WHERE panel_id = ? AND is_manual = 0 AND component_type IN ('input','auto') AND linked_group_id IS NULL AND (note LIKE '%дочернего%' OR note LIKE '%родительского%')", (parent_panel_id,))
    commit("DELETE FROM elec_panel_components WHERE panel_id = ? AND is_manual = 0 AND component_type = 'input'", (child_id,))
    # Удаляем старую связь
    commit("DELETE FROM elec_panel_links WHERE parent_panel_id = ? AND child_panel_id = ?", (parent_panel_id, child_id))
    # Создаём заново
    return _create_panel_link_with_components(
        parent_panel_id, child_id,
        breaker_rating=breaker_rating,
        breaker_poles=breaker_poles,
        breaker_curve=breaker_curve,
        cable_type=cable_type, length_m=length_m, route_type=route_type
    )


def get_children_tree(panel_id, depth=0, max_depth=6):
    """Возвращает дерево дочерних щитов (текстом)."""
    if depth >= max_depth:
        return []
    children = get_child_panels(panel_id)
    lines = []
    indent = "  " * depth
    for c in children:
        link = _get_link(panel_id, c['id'])
        rating = (link.get('parent_breaker_rating') if link else None) or '?'
        lines.append(indent + "└ " + str(c.get('name')) + " [" + str(rating) + "А]")
        lines.extend(get_children_tree(c['id'], depth + 1, max_depth))
    return lines


def _get_link(parent_panel_id, child_id):
    row = fetchone(
        "SELECT * FROM elec_panel_links WHERE parent_panel_id = ? AND child_panel_id = ? LIMIT 1",
        (parent_panel_id, child_id)
    )
    return dict(row) if row else None


# ============================================================
# СМЕТА ЩИТА (расчёт стоимости)
# ============================================================

def calc_component_price(c):
    """Цена одного компонента (с учётом quantity).

    Приоритет:
    1. c['price_unit'] — ручная цена на конкретный компонент
    2. core.elec_prices.get_component_price (справочник + дефолт)
    """
    from core import elec_prices as prices_mod

    qty = c.get('quantity') or 1
    manual = c.get('price_unit')
    if manual:
        return round(float(manual) * qty, 2)

    ctype = c.get('component_type')
    if not ctype:
        return 0.0
    rating = c.get('rating')
    poles = c.get('poles')
    brand = c.get('brand')
    unit = 0.0
    try:
        unit = prices_mod.get_component_price(ctype, rating=rating, poles=poles, brand=brand)
    except Exception as e:
        print("calc_component_price: " + str(e), flush=True)
    return round(float(unit) * qty, 2)


def calc_panel_cost(panel_id):
    """Стоимость щита (сумма всех компонентов)."""
    comps = get_components(panel_id)
    total = 0.0
    for c in comps:
        total += calc_component_price(c)
    return round(total, 2)


def get_panel_cost_breakdown(panel_id):
    """Детально: [{component, price, source}], + итог + по типам."""
    comps = get_components(panel_id)
    lines = []
    by_type = {}
    total = 0.0
    for c in comps:
        price = calc_component_price(c)
        total += price
        ctype = c.get('component_type') or 'other'
        by_type[ctype] = by_type.get(ctype, 0) + price
        lines.append({'component': c, 'price': price})
    return {
        'lines': lines,
        'by_type': {k: round(v, 2) for k, v in by_type.items()},
        'total': round(total, 2),
    }


def format_panel_cost(panel_id):
    """Текстовая смета щита."""
    p = get_panel(panel_id)
    if not p:
        return "Щит не найден"
    data = get_panel_cost_breakdown(panel_id)
    lines = ["💰 Смета щита «" + str(p.get('name') or '?') + "»", ""]
    if not data['lines']:
        lines.append("_Компонентов нет._")
        lines.append("")
        lines.append("Запусти 🪄 Автокомплектацию сначала.")
        return chr(10).join(lines)

    for item in data['lines']:
        c = item['component']
        price = item['price']
        mark = " [ручная]" if c.get('is_manual') else ""
        lines.append("• " + format_component(c) + mark + " — " + str(price) + " ₽")

    lines.append("")
    lines.append("── По типам ──")
    for t, s in sorted(data['by_type'].items(), key=lambda x: -x[1]):
        lines.append("  " + str(t) + ": " + str(s) + " ₽")

    lines.append("")
    lines.append("💰 ИТОГО: " + str(data['total']) + " ₽")
    return chr(10).join(lines)
