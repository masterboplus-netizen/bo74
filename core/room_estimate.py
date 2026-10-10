"""core.room_estimate — Смета комнаты.

Считает: материалы + работы отделки + ЭОМ + сантехника.
Использует: spec.MATERIALS_DEFAULT, spec.WORK_TYPES_DEFAULT,
            core.measures, core.elec_prices, core.plumbing_panels.
"""
from core.measures import get_measures, calculate_room_areas, get_walls_ordered
from core.rooms import get_room
from core import spec


# ============================================================
# ОТДЕЛКА: МАТЕРИАЛЫ И РАБОТЫ
# ============================================================

# Карта: категория площади -> список (material_code, work_code)
# Для каждой площади применяем соответствующие материалы и работы.
FINISH_MAP = {
    'walls_net': [
        ('plaster_gips', 'finish_plaster'),
        ('putty_finish', 'finish_putty'),
        ('primer_deep', 'finish_grout'),
        ('paint_interior', 'finish_paint'),
    ],
    'floor': [
        ('screed_cement', 'finish_screed'),
        ('substrate', 'finish_laminate'),
        ('laminate', 'finish_laminate'),
    ],
    'ceiling': [
        ('putty_finish', 'finish_putty_ceil'),
        ('paint_ceiling', 'finish_paint_ceil'),
    ],
}


def _calc_materials_for_area(area_sqm, material_codes):
    """Считает материалы для площади по списку кодов."""
    result = []
    total = 0.0
    for code in material_codes:
        info = spec.MATERIALS_DEFAULT.get(code)
        if not info:
            continue
        name, category, unit, norm_per_sqm, price = info
        qty = round(area_sqm * norm_per_sqm, 2)
        cost = round(qty * price, 2)
        total += cost
        result.append({
            'code': code,
            'name': name,
            'category': category,
            'unit': unit,
            'norm_per_sqm': norm_per_sqm,
            'qty': qty,
            'price': price,
            'cost': cost,
        })
    return result, round(total, 2)


def _calc_works_for_area(area_sqm, work_codes):
    """Считает работы для площади по списку кодов. Без дублей."""
    result = []
    total = 0.0
    total_hours = 0.0
    seen = set()
    for code in work_codes:
        if code in seen:
            continue
        seen.add(code)
        info = spec.WORK_TYPES_DEFAULT.get(code)
        if not info:
            continue
        name, unit, price, hours = info
        cost = round(area_sqm * price, 2)
        h = round(area_sqm * hours, 2)
        total += cost
        total_hours += h
        result.append({
            'code': code,
            'name': name,
            'unit': unit,
            'qty': round(area_sqm, 2),
            'price': price,
            'cost': cost,
            'hours': h,
        })
    return result, round(total, 2), round(total_hours, 2)


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ: СМЕТА КОМНАТЫ
# ============================================================

def calc_room_estimate(room_id, session_id=None):
    """Полная смета комнаты.

    Возвращает dict:
    {
      'room': {...},
      'areas': {walls_net, floor, ceiling, ...},
      'materials': [...],
      'works': [...],
      'elec': {...},
      'plumbing': {...},
      'total_materials': X,
      'total_works': Y,
      'total_elec': Z,
      'total_plumbing': W,
      'total': ИТОГО,
      'total_hours': часы,
    }
    """
    room = get_room(room_id)
    if not room:
        return None

    object_id = room.get('object_id')
    areas = calculate_room_areas(room_id, session_id=session_id)

    materials_all = []
    works_all = []
    total_materials = 0.0
    total_works = 0.0
    total_hours = 0.0

    # === Отделка ===
    for area_key, pairs in FINISH_MAP.items():
        area = areas.get(area_key) or 0
        if area <= 0:
            continue
        mat_codes = [p[0] for p in pairs]
        work_codes = [p[1] for p in pairs]
        mats, mat_total = _calc_materials_for_area(area, mat_codes)
        wrks, wrk_total, wrk_hours = _calc_works_for_area(area, work_codes)
        materials_all.extend(mats)
        works_all.extend(wrks)
        total_materials += mat_total
        total_works += wrk_total
        total_hours += wrk_hours

    # === ЭОМ ===
    elec = {'total': 0.0, 'details': []}
    if object_id:
        try:
            from core.elec_prices import calc_object_elec_total
            elec_data = calc_object_elec_total(object_id)
            elec = {'total': elec_data.get('total', 0.0), 'details': elec_data}
        except Exception as e:
            print(f"⚠️ elec estimate: {e}", flush=True)

    # === Сантехника ===
    plumb = {'total': 0.0, 'details': []}
    if object_id:
        try:
            from core.plumbing_panels import calc_object_cost
            plumb_data = calc_object_cost(object_id)
            plumb = {'total': plumb_data.get('total', 0.0), 'details': plumb_data}
        except Exception as e:
            print(f"⚠️ plumb estimate: {e}", flush=True)

    total = round(total_materials + total_works + elec['total'] + plumb['total'], 2)

    return {
        'room': room,
        'areas': areas,
        'materials': materials_all,
        'works': works_all,
        'elec': elec,
        'plumbing': plumb,
        'total_materials': round(total_materials, 2),
        'total_works': round(total_works, 2),
        'total_elec': elec['total'],
        'total_plumbing': plumb['total'],
        'total': total,
        'total_hours': round(total_hours, 2),
    }


# ============================================================
# ФОРМАТИРОВАНИЕ
# ============================================================

def format_room_estimate(room_id, session_id=None):
    """Текстовая смета комнаты (для UI)."""
    data = calc_room_estimate(room_id, session_id=session_id)
    if not data:
        return "❌ Комната не найдена"

    room = data['room']
    areas = data['areas']
    name = room.get('name') or f"Комната #{room_id}"

    lines = [f"💰 Смета комнаты «{name}»", ""]

    # === Площади ===
    lines.append("📐 Площади:")
    if areas.get('walls_net') is not None:
        lines.append(f"   Стены: {areas['walls_net']} м²")
    if areas.get('floor'):
        lines.append(f"   Пол: {areas['floor']} м²")
    if areas.get('ceiling'):
        lines.append(f"   Потолок: {areas['ceiling']} м²")
    lines.append("")

    # === Материалы ===
    if data['materials']:
        lines.append("🧱 Материалы:")
        for m in data['materials']:
            lines.append(
                f"   {m['name']}: {m['qty']} {m['unit']} × {m['price']} ₽ = {m['cost']} ₽"
            )
        lines.append(f"   ─── Итого материалы: {data['total_materials']} ₽")
        lines.append("")

    # === Работы ===
    if data['works']:
        lines.append("👷 Работы:")
        for w in data['works']:
            lines.append(
                f"   {w['name']}: {w['qty']} {w['unit']} × {w['price']} ₽ = {w['cost']} ₽ ({w['hours']} ч)"
            )
        lines.append(f"   ─── Итого работы: {data['total_works']} ₽ ({data['total_hours']} ч)")
        lines.append("")

    # === ЭОМ ===
    if data['total_elec'] > 0:
        lines.append(f"⚡ ЭОМ: {data['total_elec']} ₽")
        lines.append("")

    # === Сантехника ===
    if data['total_plumbing'] > 0:
        lines.append(f"🔧 Сантехника: {data['total_plumbing']} ₽")
        lines.append("")

    # === ИТОГО ===
    lines.append("─────────────────")
    lines.append(f"💰 ВСЕГО: {data['total']} ₽")

    return "\n".join(lines)


def get_room_estimate_summary(room_id):
    """Краткая сводка сметы комнаты."""
    data = calc_room_estimate(room_id)
    if not data:
        return None
    return {
        'room_name': data['room'].get('name'),
        'materials': data['total_materials'],
        'works': data['total_works'],
        'elec': data['total_elec'],
        'plumbing': data['total_plumbing'],
        'total': data['total'],
        'hours': data['total_hours'],
    }
