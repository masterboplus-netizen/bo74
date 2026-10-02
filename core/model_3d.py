"""core.model_3d — модель комнаты.

Собирает всё вместе: геометрия + стены + проёмы + ниши + коммуникации.
Единый источник для экспорта в CAD/BIM/JSON/PDF.
"""
from core.rooms import get_room
from core.measures import get_measures, get_walls_ordered, calculate_room_areas
from core.openings import get_openings
from core.niches import get_niches_by_room
from core.comms import get_comms
from core.geometry import get_geometry_summary, wall_offset_to_world
from core.sessions import get_active_session, get_session


def get_room_model(room_id, session_id=None):
    """Собирает полную модель комнаты.

    Возвращает dict:
    {
      'room': {...},
      'session': {...},
      'geometry': {...},
      'walls': [...],
      'openings': [...],
      'niches': [...],
      'communications': [...],
      'areas': {...},
    }
    """
    room = get_room(room_id)
    if not room:
        return None

    # Определяем сессию
    session = get_session(session_id) if session_id else get_active_session(room_id)

    # Площади
    areas = calculate_room_areas(room_id, session_id=session_id)

    # Геометрия
    geometry = get_geometry_summary(room_id)

    # Стены с координатами
    walls_raw = get_walls_ordered(room_id)
    walls = []
    for w in walls_raw:
        walls.append({
            'id': w.get('id'),
            'position': w.get('wall_pos'),
            'label': w.get('label'),
            'length': w.get('length'),
            'height': room.get('height'),
            'angle_to_next': w.get('angle_value'),
            'plane': w.get('plane') or 'straight',
            'material': w.get('material'),
            'features': {
                'niche': bool(w.get('has_niche')),
                'rounded': bool(w.get('has_rounded')),
                'wavy': bool(w.get('is_wavy')),
                'hidden': bool(w.get('has_hidden')),
            },
        })

    # Проёмы с world-координатами
    openings_raw = get_openings(room_id)
    openings = []
    for o in openings_raw:
        world = None
        wall = next((w for w in geometry['walls'] if w['wall_pos'] == o.get('wall_pos')), None)
        if wall:
            world = wall_offset_to_world(wall, o.get('offset_x') or 0, o.get('sill_height') or 0)
        openings.append({
            'id': o.get('id'),
            'type': o.get('opening_type'),
            'wall': o.get('wall_pos'),
            'offset_x': o.get('offset_x'),
            'width': o.get('width'),
            'height': o.get('height'),
            'sill_height': o.get('sill_height'),
            'world_center': world,
        })

    # Ниши с world-координатами
    niches_raw = get_niches_by_room(room_id)
    niches = []
    for n in niches_raw:
        # Определяем стену по measure_id
        wall = None
        for w in walls_raw:
            if w.get('id') == n.get('measure_id'):
                wall = next((g for g in geometry['walls'] if g['wall_pos'] == w.get('wall_pos')), None)
                break
        world = None
        if wall:
            world = wall_offset_to_world(wall, n.get('offset_x') or 0, (n.get('height') or 0) / 2)
        niches.append({
            'id': n.get('id'),
            'wall': wall['wall_pos'] if wall else None,
            'offset_x': n.get('offset_x'),
            'width_bottom': n.get('width_bottom'),
            'width_top': n.get('width_top'),
            'depth_bottom': n.get('depth_bottom'),
            'depth_top': n.get('depth_top'),
            'height': n.get('height'),
            'world_center': world,
        })

    # Коммуникации с world-координатами
    comms_raw = get_comms(room_id)
    communications = []
    for c in comms_raw:
        wall = None
        # wall в комм — это «напротив»/«слева»/«у входа»/«справа»
        for g in geometry['walls']:
            if g['wall_pos'] == c.get('wall'):
                wall = g
                break
        world = None
        if wall:
            world = wall_offset_to_world(wall, c.get('offset_x') or 0, c.get('offset_y') or 0)
        communications.append({
            'id': c.get('id'),
            'type': c.get('comm_type'),
            'wall': c.get('wall'),
            'offset_x': c.get('offset_x'),
            'offset_y': c.get('offset_y'),
            'diameter': c.get('diameter'),
            'voltage': c.get('voltage'),
            'size': c.get('size'),
            'world': world,
        })

    return {
        'room': room,
        'session': session,
        'geometry': geometry,
        'walls': walls,
        'openings': openings,
        'niches': niches,
        'communications': communications,
        'areas': areas,
    }


def get_room_areas(room_id, session_id=None):
    """Площади комнаты (обёртка для удобства)."""
    return calculate_room_areas(room_id, session_id=session_id)


def get_model_summary(room_id, session_id=None):
    """Краткая сводка модели — для UI."""
    model = get_room_model(room_id, session_id=session_id)
    if not model:
        return None
    return {
        'room_name': model['room'].get('name'),
        'walls_count': len(model['walls']),
        'openings_count': len(model['openings']),
        'niches_count': len(model['niches']),
        'comms_count': len(model['communications']),
        'areas': model['areas'],
        'closure': model['geometry']['closure'],
    }
