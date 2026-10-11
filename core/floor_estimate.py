"""core.floor_estimate — Смета помещения (этаж, зона, гараж).

Сумма смет всех комнат помещения + работы этажа.
"""
from core.db import fetchall
from core.room_estimate import calc_room_estimate


def calc_floor_estimate(floor_id):
    """Полная смета помещения."""
    from core.floors import get_floor
    floor = get_floor(floor_id)
    if not floor:
        return None

    rooms = fetchall(
        "SELECT id, name FROM rooms WHERE floor_id = ? ORDER BY id",
        (floor_id,)
    )

    rooms_data = []
    total_rooms = 0.0
    total_materials = 0.0
    total_works = 0.0
    total_hours = 0.0

    for r in rooms:
        est = calc_room_estimate(r['id'])
        if not est:
            continue
        rooms_data.append({
            'room_id': r['id'],
            'name': r['name'],
            'total': est['total'],
            'materials': est['total_materials'],
            'works': est['total_works'],
        })
        total_rooms += est['total']
        total_materials += est['total_materials']
        total_works += est['total_works']
        total_hours += est['total_hours']

    return {
        'floor_id': floor_id,
        'floor_name': floor.get('floor_name') or f"Этаж {floor.get('floor_number')}",
        'rooms': rooms_data,
        'rooms_count': len(rooms_data),
        'total_rooms': round(total_rooms, 2),
        'total_materials': round(total_materials, 2),
        'total_works': round(total_works, 2),
        'total_hours': round(total_hours, 2),
        'total': round(total_rooms, 2),
    }


def format_floor_estimate(floor_id):
    data = calc_floor_estimate(floor_id)
    if not data:
        return "❌ Помещение не найдено"

    lines = [f"💰 Смета помещения «{data['floor_name']}»", ""]
    lines.append(f"📦 Комнат: {data['rooms_count']}")
    lines.append("")

    if data['rooms']:
        lines.append("🏠 По комнатам:")
        for r in data['rooms'][:20]:
            lines.append(f"   • {r['name']}: {r['total']} ₽")
        lines.append("")

    lines.append("── Итоги ──")
    lines.append(f"🧱 Материалы: {data['total_materials']} ₽")
    lines.append(f"👷 Работы: {data['total_works']} ₽ ({data['total_hours']} ч)")
    lines.append("")
    lines.append(f"💰 ВСЕГО: {data['total']} ₽")

    return "\n".join(lines)
