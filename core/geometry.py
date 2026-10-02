"""core.geometry — геометрия комнаты.

Считает координаты стен, проверяет замыкание контура,
конвертирует локальные смещения в 3D-координаты.

Основа для экспорта в CAD/BIM.
"""
import math
from core.measures import get_walls_ordered


def get_wall_direction(angle_value_prev, prev_direction=90):
    """Возвращает направление стены (в градусах) после поворота на angle_value_prev."""
    # 90° — прямо. > 90 — поворот влево. < 90 — поворот вправо.
    delta = 180 - (angle_value_prev or 90)
    return prev_direction + delta


def calc_wall_coords(walls_ordered):
    """Считает координаты стен.

    Возвращает список:
    [{'wall_pos', 'length', 'angle_value',
      'start_x', 'start_y', 'end_x', 'end_y',
      'start_z', 'end_z', 'direction'}, ...]
    """
    if not walls_ordered:
        return []

    result = []
    x, y = 0.0, 0.0
    direction = 90.0  # первый вектор — вверх

    for i, w in enumerate(walls_ordered):
        length = float(w.get('length') or 0)
        angle = float(w.get('angle_value') or 90)

        if i > 0:
            direction = get_wall_direction(
                walls_ordered[i - 1].get('angle_value'),
                direction
            )

        rad = math.radians(direction)
        end_x = x + length * math.cos(rad)
        end_y = y + length * math.sin(rad)

        result.append({
            'wall_pos': w.get('wall_pos') or f'wall_{i + 1}',
            'length': length,
            'angle_value': angle,
            'start_x': round(x, 2),
            'start_y': round(y, 2),
            'end_x': round(end_x, 2),
            'end_y': round(end_y, 2),
            'start_z': 0,
            'end_z': 0,
            'direction': round(direction, 2),
        })

        x, y = end_x, end_y

    return result


def check_closure(walls_ordered):
    """Проверяет замыкание контура.

    Возвращает:
    {'closed': bool, 'gap_cm': float, 'gap_percent': float, 'total_length': float}
    """
    coords = calc_wall_coords(walls_ordered)
    if not coords:
        return {'closed': False, 'gap_cm': 0, 'gap_percent': 0, 'total_length': 0}

    start = (coords[0]['start_x'], coords[0]['start_y'])
    end = (coords[-1]['end_x'], coords[-1]['end_y'])
    gap = math.hypot(end[0] - start[0], end[1] - start[1])
    total = sum(w['length'] for w in coords)
    pct = (gap / total * 100) if total > 0 else 0

    return {
        'closed': pct < 5.0,
        'gap_cm': round(gap, 2),
        'gap_percent': round(pct, 2),
        'total_length': round(total, 2),
    }


def wall_offset_to_world(wall, offset_x, height=0):
    """Конвертирует локальное смещение вдоль стены в 3D-координаты.

    wall: {'start_x', 'start_y', 'end_x', 'end_y', 'length'}
    offset_x: расстояние от левого угла стены (СМ)
    height: высота от пола (СМ)

    Возвращает: (world_x, world_y, world_z)
    """
    sx = float(wall.get('start_x') or 0)
    sy = float(wall.get('start_y') or 0)
    ex = float(wall.get('end_x') or 0)
    ey = float(wall.get('end_y') or 0)
    length = float(wall.get('length') or 0)

    if length <= 0:
        return (round(sx, 2), round(sy, 2), round(height, 2))

    ratio = max(0.0, min(1.0, offset_x / length))
    wx = sx + (ex - sx) * ratio
    wy = sy + (ey - sy) * ratio

    return (round(wx, 2), round(wy, 2), round(height, 2))


def calc_corner_coords(walls_ordered):
    """Возвращает список углов комнаты с координатами."""
    coords = calc_wall_coords(walls_ordered)
    corners = []
    for i, w in enumerate(coords):
        corners.append({
            'id': i + 1,
            'x': w['start_x'],
            'y': w['start_y'],
        })
    # Замыкающий угол
    if coords:
        corners.append({
            'id': len(corners) + 1,
            'x': coords[-1]['end_x'],
            'y': coords[-1]['end_y'],
        })
    return corners


def get_geometry_summary(room_id):
    """Полная геометрия комнаты для экспорта."""
    walls = get_walls_ordered(room_id)
    coords = calc_wall_coords(walls)
    closure = check_closure(walls)
    corners = calc_corner_coords(walls)
    return {
        'origin': 'дверь, левый нижний угол',
        'coordinate_system': 'локальная, X вправо, Y вверх, Z высота',
        'units': 'см',
        'walls': coords,
        'corners': corners,
        'closure': closure,
    }
