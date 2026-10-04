"""core.elec — ЭОМ: группы, автоматы, кабели."""
from core.db import fetchone, fetchall, commit
from core import spec


# ============================================================
# ПИТАНИЕ ОБЪЕКТА
# ============================================================

def set_supply(object_id, phase_count=1, voltage=220, input_breaker=None,
               meter_type=None, total_load_watt=None, note=None):
    """Устанавливает тип питания объекта."""
    existing = fetchone("SELECT object_id FROM elec_supply WHERE object_id = ?", (object_id,))
    if existing:
        return commit(
            """UPDATE elec_supply SET
               phase_count = ?, voltage = ?, input_breaker = ?,
               meter_type = ?, total_load_watt = ?, note = ?,
               updated_at = CURRENT_TIMESTAMP
               WHERE object_id = ?""",
            (phase_count, voltage, input_breaker, meter_type,
             total_load_watt, note, object_id)
        )
    return commit(
        """INSERT INTO elec_supply
           (object_id, phase_count, voltage, input_breaker,
            meter_type, total_load_watt, note)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (object_id, phase_count, voltage, input_breaker,
         meter_type, total_load_watt, note)
    )


def get_supply(object_id):
    """Возвращает настройки питания или None."""
    row = fetchone("SELECT * FROM elec_supply WHERE object_id = ?", (object_id,))
    return dict(row) if row else None


# ============================================================
# ГРУППЫ
# ============================================================

def create_group(object_id, room_id, name, phase=1, purpose='socket',
                 cable_type=None, load_watt=None, breaker_type=None,
                 breaker_curve='C', ip_class='ip20',
                 is_emergency=0, diff_protection=0, note=None,
                 floor_id=None, phase_l1=1, phase_l2=0, phase_l3=0):
    """Создаёт группу. Возвращает group_id."""
    return commit(
        """INSERT INTO elec_groups
           (object_id, room_id, name, phase, purpose, cable_type,
            load_watt, breaker_type, breaker_curve, ip_class,
            is_emergency, diff_protection, note, floor_id,
            phase_l1, phase_l2, phase_l3)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, room_id, name, phase, purpose, cable_type,
         load_watt, breaker_type, breaker_curve, ip_class,
         is_emergency, diff_protection, note, floor_id,
         phase_l1, phase_l2, phase_l3)
    )


def get_group(group_id):
    row = fetchone("SELECT * FROM elec_groups WHERE id = ?", (group_id,))
    return dict(row) if row else None


def get_groups(room_id):
    rows = fetchall("SELECT * FROM elec_groups WHERE room_id = ? ORDER BY id", (room_id,))
    return [dict(r) for r in rows]


def get_groups_by_object(object_id):
    rows = fetchall("SELECT * FROM elec_groups WHERE object_id = ? ORDER BY id", (object_id,))
    return [dict(r) for r in rows]


def update_group(group_id, **kwargs):
    allowed = {"name", "phase", "purpose", "cable_type", "load_watt",
               "breaker_type", "breaker_curve", "ip_class",
               "is_emergency", "diff_protection", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(group_id)
    commit(f"UPDATE elec_groups SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_group(group_id):
    commit("UPDATE room_comms SET group_id = NULL WHERE group_id = ?", (group_id,))
    commit("DELETE FROM elec_cables WHERE group_id = ?", (group_id,))
    commit("DELETE FROM elec_groups WHERE id = ?", (group_id,))
    return True


# ============================================================
# ПРИВЯЗКА ТОЧЕК К ГРУППАМ
# ============================================================

def assign_comm_to_group(comm_id, group_id):
    """Привязывает точку к группе."""
    commit("UPDATE room_comms SET group_id = ? WHERE id = ?", (group_id, comm_id))
    return True


def get_comms_by_group(group_id):
    rows = fetchall("SELECT * FROM room_comms WHERE group_id = ? ORDER BY id", (group_id,))
    return [dict(r) for r in rows]


# ============================================================
# РАСЧЁТЫ
# ============================================================

def calc_group_load(group_id):
    """Расчётная мощность группы (Вт)."""
    g = get_group(group_id)
    if not g:
        return 0
    return g.get('load_watt') or 0


def calc_total_load(object_id):
    """Суммарная мощность всех групп объекта."""
    groups = get_groups_by_object(object_id)
    return sum(g.get('load_watt') or 0 for g in groups)


def calc_current(load_watt, phase=1, voltage=220):
    """Расчёт тока (А)."""
    if phase == 3:
        # I = P / (√3 × U × cos φ), cos φ ≈ 0.9
        return round(load_watt / (1.73 * voltage * 0.9), 2)
    return round(load_watt / (voltage * 0.9), 2)


def pick_breaker(load_watt, phase=1, curve='C'):
    """Подбирает автомат: возвращает (rating, curve)."""
    current = calc_current(load_watt, phase)
    rating = spec.pick_breaker_by_current(current)
    return rating, curve


def pick_cable(load_watt, phase=1, voltage=220):
    """Подбирает кабель: возвращает код типа."""
    current = calc_current(load_watt, phase, voltage)
    return spec.pick_cable_by_current(current, phase)


def auto_fill_group(group_id, voltage=220):
    """Автоматически подбирает автомат и кабель для группы по load_watt."""
    g = get_group(group_id)
    if not g:
        return False
    load = g.get('load_watt') or 0
    if load <= 0:
        return False
    phase = g.get('phase') or 1
    curve = g.get('breaker_curve') or 'C'
    rating, _ = pick_breaker(load, phase, curve)
    cable = pick_cable(load, phase, voltage)
    breaker_type = f"{'3P' if phase == 3 else '1P'} {curve}{rating}"
    update_group(group_id, breaker_type=breaker_type, cable_type=cable)
    return True


# ============================================================
# ФОРМАТИРОВАНИЕ
# ============================================================

def format_group(g):
    """Форматирует группу в строку."""
    icon = "🚨" if g.get('is_emergency') else spec.PURPOSE_TYPES.get(g.get('purpose'), '📦').split(' ', 1)[0]
    name = g.get('name') or '—'
    phase = g.get('phase') or 1
    load = g.get('load_watt') or 0
    breaker = g.get('breaker_type') or '—'
    cable = g.get('cable_type') or '—'
    diff = " + УЗО" if g.get('diff_protection') else ""
    return f"{icon} *{name}*\n   {phase}ф · {int(load)} Вт · {breaker}{diff}\n   Кабель: {cable}"


def format_supply(object_id):
    """Форматирует питание объекта."""
    s = get_supply(object_id)
    if not s:
        return "⚡ Питание объекта: не настроено"
    phase = s.get('phase_count') or 1
    voltage = s.get('voltage') or 220
    input_b = s.get('input_breaker') or '—'
    meter = s.get('meter_type') or '—'
    total = s.get('total_load_watt') or 0
    return (
        f"⚡ *Питание объекта*\\n"
        f"   Фаз: {phase} ({voltage}В)\\n"
        f"   Вводной автомат: {input_b}\\n"
        f"   Счётчик: {meter}\\n"
        f"   Общая нагрузка: {int(total)} Вт"
    )


def get_summary(object_id):
    """Сводка по ЭОМ объекта."""
    groups = get_groups_by_object(object_id)
    supply = get_supply(object_id)
    total_load = sum(g.get('load_watt') or 0 for g in groups)
    emergency = [g for g in groups if g.get('is_emergency')]
    with_uzo = [g for g in groups if g.get('diff_protection')]
    phase = (supply or {}).get('phase_count') or 1
    voltage = (supply or {}).get('voltage') or 220
    total_current = calc_current(total_load, phase, voltage)
    return {
        'groups_count': len(groups),
        'total_load_watt': total_load,
        'total_current_a': total_current,
        'emergency_count': len(emergency),
        'diff_protection_count': len(with_uzo),
        'phase_count': phase,
        'voltage': voltage,
    }

# ============================================================
# ЭОМ ОБЪЕКТА (полная логика)
# ============================================================

def get_all_groups(object_id):
    """Все группы объекта (синоним get_groups_by_object)."""
    return get_groups_by_object(object_id)


def calc_supply_breaker(object_id, safety_factor=1.2):
    """Подбор вводного автомата по суммарной нагрузке объекта."""
    supply = get_supply(object_id) or {}
    phase = supply.get('phase_count') or 1
    voltage = supply.get('voltage') or (380 if phase == 3 else 220)
    total_watt = calc_total_load(object_id)
    # Запас 20%
    total_watt_with_margin = total_watt * safety_factor
    current = calc_current(total_watt_with_margin, phase, voltage)
    rating = spec.pick_breaker_by_current(current)
    curve = 'C'
    prefix = '3P' if phase == 3 else '1P'
    return {
        'rating': rating,
        'curve': curve,
        'breaker_type': f"{prefix} {curve}{rating}",
        'current_a': current,
        'total_watt': total_watt,
    }


def format_elec_full(object_id):
    """Полный ЭОМ объекта текстом."""
    supply = get_supply(object_id) or {}
    groups = get_all_groups(object_id)

    phase = supply.get('phase_count') or 1
    voltage = supply.get('voltage') or (380 if phase == 3 else 220)
    total_watt = calc_total_load(object_id)
    total_current = calc_current(total_watt, phase, voltage)
    supply_breaker = calc_supply_breaker(object_id)

    lines = [
        f"⚡ *ЭОМ объекта*\n",
        f"🔌 Питание: {phase}-фазное ({voltage}В)",
        f"   Вводной автомат: *{supply_breaker['breaker_type']}*",
        f"   Счётчик: {supply.get('meter_type') or '—'}",
        f"",
        f"📊 Суммарная нагрузка: *{int(total_watt)} Вт* · {total_current} А",
        f"📋 Групп: *{len(groups)}*",
    ]

    if groups:
        lines.append("")
        for g in groups:
            icon = "🚨" if g.get('is_emergency') else (spec.PURPOSE_TYPES.get(g.get('purpose'), '📦').split(' ', 1)[0])
            name = g.get('name') or '—'
            ph = g.get('phase') or 1
            w = g.get('load_watt') or 0
            breaker = g.get('breaker_type') or '—'
            cable = g.get('cable_type') or '—'
            diff = " + УЗО" if g.get('diff_protection') else ""
            lines.append(f"   {icon} *{name}*")
            lines.append(f"      {ph}ф · {int(w)} Вт · {breaker}{diff} · {cable}")

    return "\n".join(lines)

# ============================================================
# РАБОТА С ФАЗАМИ L1 / L2 / L3
# ============================================================

def get_active_phases(group_id):
    """Возвращает список активных фаз группы: ['L1'], ['L1','L2'] и т.д."""
    g = get_group(group_id)
    if not g:
        return []
    result = []
    if g.get('phase_l1'):
        result.append('L1')
    if g.get('phase_l2'):
        result.append('L2')
    if g.get('phase_l3'):
        result.append('L3')
    return result


def calc_group_current(group_id, voltage=220, cos_phi=0.9):
    """Ток группы с учётом задействованных фаз."""
    g = get_group(group_id)
    if not g:
        return 0
    load = g.get('load_watt') or 0
    phases = get_active_phases(group_id)
    n = len(phases) or 1
    if n == 1:
        return round(load / (voltage * cos_phi), 2)
    # 2ф или 3ф: I = P / (√3 × U_лин × cos φ), U_лин = 380
    u_line = 380 if n >= 2 else voltage
    return round(load / (1.73 * u_line * cos_phi), 2)


def auto_pick_phase(object_id, load_watt=0):
    """Находит наименее загруженную фазу.
    Возвращает 'L1', 'L2' или 'L3'.
    """
    groups = get_groups_by_object(object_id)
    loads = {'L1': 0, 'L2': 0, 'L3': 0}
    for g in groups:
        w = g.get('load_watt') or 0
        if g.get('phase_l1'):
            loads['L1'] += w
        if g.get('phase_l2'):
            loads['L2'] += w
        if g.get('phase_l3'):
            loads['L3'] += w
    return min(loads, key=loads.get)


def calc_balance(object_id):
    """Распределение нагрузки по фазам L1/L2/L3 + перекос."""
    groups = get_groups_by_object(object_id)
    loads = {'L1': 0, 'L2': 0, 'L3': 0}
    for g in groups:
        w = g.get('load_watt') or 0
        if g.get('phase_l1'):
            loads['L1'] += w
        if g.get('phase_l2'):
            loads['L2'] += w
        if g.get('phase_l3'):
            loads['L3'] += w
    max_load = max(loads.values()) or 1
    min_load = min(loads.values())
    imbalance = round((max_load - min_load) / max_load * 100, 1) if max_load else 0
    return {
        'l1_watt': loads['L1'],
        'l2_watt': loads['L2'],
        'l3_watt': loads['L3'],
        'imbalance_percent': imbalance,
        'balanced': imbalance < 20,
    }


def assign_phases_by_load(group_id, object_id, load_watt):
    """Автоматически раскидывает фазы для группы:
    - 1ф нагрузка → на самую свободную фазу
    - 2ф/3ф → сразу на все нужные
    """
    g = get_group(group_id)
    if not g:
        return False
    n_phases = g.get('phase') or 1
    if n_phases >= 3:
        # Трёхфазная — все три
        update_group(group_id, phase_l1=1, phase_l2=1, phase_l3=1)
        return True
    if n_phases == 2:
        # Двухфазная — две самые свободные
        bal = calc_balance(object_id)
        order = sorted(
            [('L1', bal['l1_watt']), ('L2', bal['l2_watt']), ('L3', bal['l3_watt'])],
            key=lambda x: x[1]
        )
        best = {order[0][0], order[1][0]}
        update_group(group_id,
                     phase_l1=1 if 'L1' in best else 0,
                     phase_l2=1 if 'L2' in best else 0,
                     phase_l3=1 if 'L3' in best else 0)
        return True
    # 1ф — самая свободная
    best = auto_pick_phase(object_id, load_watt)
    update_group(group_id,
                 phase_l1=1 if best == 'L1' else 0,
                 phase_l2=1 if best == 'L2' else 0,
                 phase_l3=1 if best == 'L3' else 0)
    return True


def format_phase_distribution(object_id):
    """Текст распределения по фазам."""
    bal = calc_balance(object_id)
    l1 = bal['l1_watt']
    l2 = bal['l2_watt']
    l3 = bal['l3_watt']
    imb = bal['imbalance_percent']
    icon = '✅' if bal['balanced'] else '⚠️'
    return (
        f"📊 *Распределение по фазам*\n"
        f"   L1: {int(l1)} Вт\n"
        f"   L2: {int(l2)} Вт\n"
        f"   L3: {int(l3)} Вт\n"
        f"   {icon} Перекос: {imb}%"
    )

# ============================================================
# СВЯЗЬ ГРУППА ↔ КОМНАТА (через точки)
# ============================================================

def get_groups_by_floor(floor_id):
    """Все группы щита этажа (все группы помещения)."""
    rows = fetchall(
        "SELECT * FROM elec_groups WHERE floor_id = ? ORDER BY id",
        (floor_id,)
    )
    return [dict(r) for r in rows]


def get_groups_by_room(room_id):
    """Группы, которые ОБСЛУЖИВАЮТ эту комнату (через точки в room_comms).

    Одна группа может обслуживать несколько комнат.
    Возвращает список уникальных групп.
    """
    rows = fetchall(
        """SELECT DISTINCT g.*
           FROM elec_groups g
           INNER JOIN room_comms c ON c.group_id = g.id
           WHERE c.room_id = ?
           ORDER BY g.id""",
        (room_id,)
    )
    return [dict(r) for r in rows]


def get_rooms_by_group(group_id):
    """Комнаты, в которых есть точки этой группы.

    Возвращает список комнат (id, name) + количество точек.
    """
    rows = fetchall(
        """SELECT r.id, r.name, COUNT(c.id) as points_count
           FROM rooms r
           INNER JOIN room_comms c ON c.room_id = r.id
           WHERE c.group_id = ?
           GROUP BY r.id, r.name
           ORDER BY r.id""",
        (group_id,)
    )
    return [dict(r) for r in rows]


def get_points_of_group(group_id):
    """Все точки группы (в любых комнатах)."""
    rows = fetchall(
        """SELECT c.*, r.name as room_name
           FROM room_comms c
           LEFT JOIN rooms r ON r.id = c.room_id
           WHERE c.group_id = ?
           ORDER BY c.room_id, c.id""",
        (group_id,)
    )
    return [dict(r) for r in rows]


def get_group_load_actual(group_id):
    """Фактическая нагрузка группы (сумма мощностей точек, если заданы).

    Пока у точек нет мощности — возвращает 0.
    """
    # TODO: когда у room_comms появится поле power_watt — суммировать
    return 0


def assign_point_to_group(comm_id, group_id):
    """Привязывает точку к группе. Синоним assign_comm_to_group."""
    return assign_comm_to_group(comm_id, group_id)


def unassign_point_from_group(comm_id):
    """Отвязывает точку от группы."""
    commit("UPDATE room_comms SET group_id = NULL WHERE id = ?", (comm_id,))
    return True


def format_group_with_rooms(group_id):
    """Форматирует группу с указанием обслуживаемых комнат."""
    g = get_group(group_id)
    if not g:
        return ""
    rooms = get_rooms_by_group(group_id)
    icon = "🚨" if g.get('is_emergency') else spec.PURPOSE_TYPES.get(g.get('purpose'), '📦').split(' ', 1)[0]
    name = g.get('name') or '—'
    phase = g.get('phase') or 1
    load = g.get('load_watt') or 0
    breaker = g.get('breaker_type') or '—'
    cable = g.get('cable_type') or '—'
    if rooms:
        rooms_str = ", ".join(f"{r['name']} ({r['points_count']})" for r in rooms)
    else:
        rooms_str = "—"
    return (
        f"{icon} *{name}*\n"
        f"   {phase}ф · {int(load)} Вт · {breaker} · {cable}\n"
        f"   Комнаты: {rooms_str}"
    )


# ============================================================
# КУХОННЫЕ ШАБЛОНЫ (кафе/рестораны)
# ============================================================

def get_kitchen_equipment():
    """Возвращает список кухонного оборудования из справочника."""
    result = []
    for code, val in spec.KITCHEN_EQUIPMENT.items():
        if isinstance(val, (list, tuple)) and len(val) >= 3:
            result.append((code, val[0], int(val[1]), int(val[2])))
    return result

def create_kitchen_group(object_id, floor_id, equip_code):
    """Создаёт группу ЭОМ для одной единицы кухонного оборудования."""
    equip = spec.KITCHEN_EQUIPMENT.get(equip_code)
    if not equip:
        return None
    if not isinstance(equip, (list, tuple)) or len(equip) < 3:
        return None
    name_label = equip[0]
    load_watt = int(equip[1])
    phase = int(equip[2])
    purpose = 'kitchen'
    voltage = 380 if phase == 3 else 220
    current = calc_current(load_watt, phase, voltage)
    rating, curve = pick_breaker(load_watt, phase, 'C')
    cable = pick_cable(load_watt, phase, voltage)
    breaker_type = ('3P' if phase == 3 else '1P') + ' ' + curve + str(rating)
    group_name = name_label + ' ' + str(load_watt) + 'W'
    return create_group(
        object_id=object_id,
        room_id=None,
        name=group_name,
        phase=phase,
        purpose=purpose,
        cable_type=cable,
        load_watt=load_watt,
        breaker_type=breaker_type,
        breaker_curve=curve,
        floor_id=floor_id,
    )
