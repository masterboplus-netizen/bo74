"""core.rooms_logic.openings — логика проёмов (без Telegram)."""
from core.openings import get_openings, add_opening, delete_opening


def get_opening_list(room_id: int) -> list:
    """Список проёмов комнаты (для Web/Mobile)."""
    openings = get_openings(room_id)
    return [{'id': o.get('id'), 'type': o.get('opening_type'), 'wall': o.get('wall_pos'),
             'width': o.get('width'), 'height': o.get('height')} for o in openings]


def add_opening_point(room_id: int, opening_type: str, wall: str, width: float, height: float, sill: float = None) -> bool:
    """Добавить проём (для Web/Mobile)."""
    try:
        add_opening(room_id=room_id, opening_type=opening_type, wall_pos=wall,
                    width=width, height=height, sill_height=sill)
        return True
    except Exception:
        return False


def delete_opening_point(opening_id: int) -> bool:
    """Удалить проём."""
    try:
        delete_opening(opening_id)
        return True
    except Exception:
        return False
