"""core.rooms_ui — форматирование данных для UI (Telegram/Web)."""
from core.rooms import get_room, get_rooms, count_tasks_by_room
from core.measures import get_measures, calculate_room_areas, format_measure
from core.comms import get_comms, format_comm, count_comms_by_type
from core.room_objects import get_room_objects, format_room_object


def format_room_card(room_id):
    """Краткая карточка комнаты — что замерено."""
    room = get_room(room_id)
    if not room:
        return "❌ Комната не найдена"

    lines = [f"📦 {room['name']}"]

    # Высота
    if room.get('height'):
        _h = room['height']
        _h_str = f"{_h:.2f}".rstrip('0').rstrip('.').replace('.', ',')
        lines.append(f"Высота: {_h_str} см")

    # Тип помещения
    rt = room.get('room_type')
    if rt:
        rt_names = {'rough': 'Черновая', 'finish': 'Чистовая', 'mid': 'Промежуточная'}
        if rt in rt_names:
            lines.append(f"Тип: {rt_names[rt]}")

    # Размеры
    measures = get_measures(room_id)
    if measures:
        areas = calculate_room_areas(room_id)
        lines.append("")
        # Считаем количество по типам
        walls_count = len([m for m in measures if m.get('category') == 'wall'])
        if walls_count:
            lines.append(f"🧱 Стены: {walls_count} шт.")
        if areas.get('walls_net') is not None:
            lines.append(f"📐 Площадь стен: {areas['walls_net']} м²")
        if areas.get('floor'):
            lines.append(f"📐 Площадь пола: {areas['floor']} м²")
    else:
        lines.append("")
        lines.append("_Замеры ещё не начаты_")

    if room.get('note'):
        lines.append("")
        lines.append(f"📝 {room['note']}")

    return "\n".join(lines)


def format_rooms_list(object_id):
    """Список комнат объекта (для меню)."""
    rooms = get_rooms(object_id)
    if not rooms:
        return "Комнат пока нет"
    lines = [f"📦 Комнаты объекта ({len(rooms)}):"]
    for r in rooms:
        t = count_tasks_by_room(r['id'])
        mark = "🏠" if r.get('is_default') else "📦"
        line = f"{mark} {r['name']}"
        if t['total'] > 0:
            line += f" — {t['done']}/{t['total']}"
        lines.append(line)
    return "\n".join(lines)
