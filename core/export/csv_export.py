"""core.export.csv — экспорт замеров комнаты в CSV."""
import csv
import io
from core.rooms import get_room
from core.measures import get_measures, get_walls_ordered
from core.openings import get_openings
from core.niches import get_niches_by_room


def export_csv(room_id, session_id=None):
    """Возвращает CSV-строку со всеми замерами."""
    room = get_room(room_id)
    if not room:
        return None
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Комната", room.get('name', '')])
    writer.writerow(["Высота", room.get('height', '')])
    writer.writerow([])
    writer.writerow(["Тип", "Позиция", "Длина", "Высота", "Площадь"])
    walls = get_walls_ordered(room_id, session_id=session_id)
    total_area = 0
    for w in walls:
        L = w.get('length') or 0
        H = room.get('height') or 0
        area = (L * H) / 10000
        total_area += area
        writer.writerow(["Стена", w.get('wall_pos', ''), L, H, round(area, 2)])
    writer.writerow([])
    writer.writerow(["ИТОГО площадь стен (м2)", round(total_area, 2)])
    return output.getvalue()


def save_csv(room_id, session_id=None, path=None):
    """Сохраняет CSV в файл. Возвращает путь."""
    content = export_csv(room_id, session_id=session_id)
    if not content:
        return None
    if not path:
        path = f"/tmp/room_{room_id}.csv"
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(content)
    return path
