"""core.export.dxf — экспорт комнаты в DXF (свой генератор, без ezdxf).

Формат DXF R12 (минимальный, совместим со всеми CAD).
"""
from core.measures import get_walls_ordered, get_measures
from core.openings import get_openings
from core.niches import get_niches_by_room
from core.comms import get_comms
from core.geometry import calc_wall_coords, wall_offset_to_world
from core.rooms import get_room


def _dxf_header():
    """Заголовок DXF."""
    return """0
SECTION
2
HEADER
9
$ACADVER
1
AC1009
9
$INSUNITS
70
5
9
$MEASUREMENT
70
1
0
ENDSEC
0
SECTION
2
TABLES
0
TABLE
2
LAYER
70
6
0
LAYER
2
WALLS
70
0
62
7
6
CONTINUOUS
0
LAYER
2
OPENINGS
70
0
62
1
6
CONTINUOUS
0
LAYER
2
NICHES
70
0
62
3
6
CONTINUOUS
0
LAYER
2
COMMS
70
0
62
5
6
CONTINUOUS
0
LAYER
2
DIMENSIONS
70
0
62
4
6
CONTINUOUS
0
LAYER
2
LABELS
70
0
62
2
6
CONTINUOUS
0
ENDTAB
0
ENDSEC
0
SECTION
2
ENTITIES
"""


def _dxf_footer():
    return """0
ENDSEC
0
EOF
"""


def _line(layer, x1, y1, x2, y2):
    return f"""0
LINE
8
{layer}
10
{x1:.2f}
20
{y1:.2f}
11
{x2:.2f}
21
{y2:.2f}
"""


def _text(layer, x, y, text, height=10):
    text_escaped = str(text).replace('\\n', ' ')[:255]
    return f"""0
TEXT
8
{layer}
10
{x:.2f}
20
{y:.2f}
40
{height:.2f}
1
{text_escaped}
"""


def export_dxf(room_id, session_id=None):
    """Экспортирует комнату в DXF. Возвращает текст DXF."""
    room = get_room(room_id)
    if not room:
        return None

    walls = get_walls_ordered(room_id)
    if not walls:
        return None

    coords = calc_wall_coords(walls)
    if not coords:
        return None

    out = [_dxf_header()]

    for i in range(len(coords) - 1):
        w = coords[i]
        out.append(_line("WALLS", w['start_x'], w['start_y'], w['end_x'], w['end_y']))

    if coords:
        last = coords[-1]
        first = coords[0]
        out.append(_line("WALLS", last['end_x'], last['end_y'], first['start_x'], first['start_y']))

    wall_names = {1: 'напр', 2: 'слева', 3: 'вх', 4: 'справа'}
    for i, w in enumerate(coords):
        mx = (w['start_x'] + w['end_x']) / 2
        my = (w['start_y'] + w['end_y']) / 2
        length = w.get('length') or 0
        label = f"{int(length)}"
        out.append(_text("LABELS", mx, my + 15, label))

    wall_by_pos = {w['wall_pos']: w for w in coords}

    openings = get_openings(room_id)
    for o in openings:
        wall = wall_by_pos.get(o.get('wall_pos'))
        if not wall:
            continue
        world = wall_offset_to_world(wall, o.get('offset_x') or 0, o.get('sill_height') or 0)
        wx, wy = world[0], world[1]
        w_len = o.get('width') or 0
        if w_len > 0 and wall['length'] > 0:
            dx = (wall['end_x'] - wall['start_x']) / wall['length'] * w_len
            dy = (wall['end_y'] - wall['start_y']) / wall['length'] * w_len
            out.append(_line("OPENINGS", wx, wy, wx + dx, wy + dy))
            out.append(_text("LABELS", wx + dx / 2, wy + dy / 2 + 10, f"{int(w_len)}"))

    niches = get_niches_by_room(room_id)
    for n in niches:
        w_measure = None
        for w in walls:
            if w.get('id') == n.get('measure_id'):
                w_measure = w
                break
        if not w_measure:
            continue
        wall = wall_by_pos.get(w_measure.get('wall_pos'))
        if not wall:
            continue
        world = wall_offset_to_world(wall, n.get('offset_x') or 0, 0)
        wx, wy = world[0], world[1]
        nw = n.get('width_bottom') or 0
        if nw > 0 and wall['length'] > 0:
            dx = (wall['end_x'] - wall['start_x']) / wall['length'] * nw
            dy = (wall['end_y'] - wall['start_y']) / wall['length'] * nw
            out.append(_line("NICHES", wx, wy, wx + dx, wy + dy))
            out.append(_text("LABELS", wx + dx / 2, wy + dy / 2 - 10, f"ниша {int(nw)}"))

    comms = get_comms(room_id)
    for c in comms:
        wall = wall_by_pos.get(c.get('wall'))
        if not wall:
            continue
        world = wall_offset_to_world(wall, c.get('offset_x') or 0, c.get('offset_y') or 0)
        wx, wy = world[0], world[1]
        out.append(_text("COMMS", wx, wy, f"○ {c.get('comm_type') or '?'}"))

    out.append(_dxf_footer())
    return "".join(out)


def save_dxf(room_id, session_id=None, path=None):
    """Сохраняет DXF в файл. Возвращает путь."""
    import os
    dxf = export_dxf(room_id, session_id=session_id)
    if not dxf:
        return None
    if not path:
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tmp")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"room_{room_id}.dxf")
    with open(path, "w", encoding="utf-8") as f:
        f.write(dxf)
    return path
