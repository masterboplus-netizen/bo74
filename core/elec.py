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
                 is_emergency=0, diff_protection=0, note=None):
    """Создаёт группу. Возвращает group_id."""
    return commit(
        """INSERT INTO elec_groups
           (object_id, room_id, name, phase, purpose, cable_type,
            load_watt, breaker_type, breaker_curve, ip_class,
            is_emergency, diff_protection, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, room_id, name, phase, purpose, cable_type,
         load_watt, breaker_type, breaker_curve, ip_class,
         is_emergency, diff_protection, note)
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
