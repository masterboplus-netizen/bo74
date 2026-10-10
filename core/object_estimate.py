"""core.object_estimate — Сводная смета объекта.

Собирает:
- сметы всех комнат объекта
- работы объекта (ЭОМ, сантехника, отделка)
- отдельные работы (доп работы)

Возвращает: {total, by_room, elec, plumbing, works, materials}
"""
from core.db import fetchall
from core.room_estimate import calc_room_estimate, format_room_estimate


def calc_object_estimate(object_id):
    """Полная сводная смета объекта.

    Возвращает dict:
    {
      'object_id': N,
      'rooms': [{room_id, name, total, materials, works}],
      'total_rooms': X,
      'elec': Y,
      'plumbing': Z,
      'works': W,
      'total': ИТОГО,
      'total_materials': X,
      'total_works': Y,
      'total_hours': H,
    }
    """
    from modules.objects import get_object
    obj = get_object(object_id)
    if not obj:
        return None

    # Все комнаты объекта
    rooms = fetchall(
        "SELECT id, name FROM rooms WHERE object_id = ? ORDER BY id",
        (object_id,)
    )

    rooms_data = []
    total_rooms = 0.0
    total_materials = 0.0
    total_works = 0.0
    total_hours = 0.0

    for r in rooms:
        rid = r['id']
        est = calc_room_estimate(rid)
        if not est:
            continue
        rooms_data.append({
            'room_id': rid,
            'name': r['name'],
            'total': est['total'],
            'materials': est['total_materials'],
            'works': est['total_works'],
            'hours': est['total_hours'],
        })
        total_rooms += est['total']
        total_materials += est['total_materials']
        total_works += est['total_works']
        total_hours += est['total_hours']

    # ЭОМ объекта
    elec_total = 0.0
    try:
        from core.elec_prices import calc_object_elec_total
        elec_data = calc_object_elec_total(object_id)
        elec_total = elec_data.get('total', 0.0)
    except Exception as e:
        print(f"⚠️ object elec: {e}", flush=True)

    # Сантехника объекта
    plumb_total = 0.0
    try:
        from core.plumbing_panels import calc_object_cost
        plumb_data = calc_object_cost(object_id)
        plumb_total = plumb_data.get('total', 0.0)
    except Exception as e:
        print(f"⚠️ object plumb: {e}", flush=True)

    total = round(total_rooms + elec_total + plumb_total, 2)

    return {
        'object_id': object_id,
        'object_name': obj.get('name'),
        'rooms': rooms_data,
        'rooms_count': len(rooms_data),
        'total_rooms': round(total_rooms, 2),
        'elec': round(elec_total, 2),
        'plumbing': round(plumb_total, 2),
        'total_materials': round(total_materials, 2),
        'total_works': round(total_works, 2),
        'total_hours': round(total_hours, 2),
        'total': total,
    }


def format_object_estimate(object_id):
    """Текстовая сводная смета объекта."""
    data = calc_object_estimate(object_id)
    if not data:
        return "❌ Объект не найден"

    lines = [f"💰 Смета объекта «{data['object_name']}»", ""]
    lines.append(f"📦 Комнат: {data['rooms_count']}")
    lines.append("")

    if data['rooms']:
        lines.append("🏠 По комнатам:")
        for r in data['rooms'][:20]:
            lines.append(
                f"   • {r['name']}: {r['total']} ₽ "
                f"(мат. {r['materials']} + раб. {r['works']})"
            )
        lines.append("")

    lines.append("── Итоги ──")
    lines.append(f"🧱 Материалы:  {data['total_materials']} ₽")
    lines.append(f"👷 Работы:     {data['total_works']} ₽ ({data['total_hours']} ч)")
    lines.append(f"⚡ ЭОМ:        {data['elec']} ₽")
    lines.append(f"🔧 Сантехника: {data['plumbing']} ₽")
    lines.append("")
    lines.append(f"💰 ВСЕГО: {data['total']} ₽")

    return "\n".join(lines)
