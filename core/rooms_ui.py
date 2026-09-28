"""core.rooms_ui — форматирование данных для UI (Telegram/Web)."""
from core.rooms import get_room, get_rooms, count_tasks_by_room
from core.measures import get_measures, calculate_room_areas, format_measure
from core.comms import get_comms, format_comm, count_comms_by_type
from core.room_objects import get_room_objects, format_room_object


def format_room_card(room_id):
    """Полная карточка комнаты — текст для Telegram."""
    room = get_room(room_id)
    if not room:
        return "❌ Комната не найдена"
    lines = [f"📦 {room['name']}"]

    if room.get('area_sqm'):
        lines.append(f"Площадь: {room['area_sqm']} м²")
    if room.get('height'):
        lines.append(f"Высота: {room['height']} м")
    if room.get('note'):
        lines.append(f"📝 {room['note']}")

    # Задачи
    t = count_tasks_by_room(room_id)
    if t['total'] > 0:
        lines.append("")
        lines.append(f"📋 Задачи: {t['done']}/{t['total']} ({t['open']} в работе)")

    # Размеры
    measures = get_measures(room_id)
    if measures:
        lines.append("")
        lines.append(f"📐 Размеров: {len(measures)}")
        areas = calculate_room_areas(room_id)
        if areas['walls_net']:
            lines.append(f"  Стены (чистые): {areas['walls_net']} м²")
        if areas['floor']:
            lines.append(f"  Пол: {areas['floor']} м²")

    # Коммуникации
    comms = get_comms(room_id)
    if comms:
        lines.append("")
        lines.append(f"🔧 Коммуникации: {len(comms)}")

    # Мебель/техника
    objects = get_room_objects(room_id)
    if objects:
        lines.append("")
        lines.append(f"🪑 Мебель/техника: {len(objects)}")

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
