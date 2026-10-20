"""core.rooms_logic.walls — логика стен (без Telegram)."""
from core.measures import get_walls_ordered, get_walls_progress


def get_wall_state(room_id: int) -> dict:
    """Возвращает прогресс обхода стен (для Web/Mobile)."""
    progress = get_walls_progress(room_id)
    walls = get_walls_ordered(room_id)
    return {
        'walls_count': progress.get('walls_count', 0),
        'current_step': progress.get('current_step', 1),
        'walls': walls,
        'is_finished': progress.get('walls_count', 0) >= 4,
    }


def get_room_areas(room_id: int) -> dict:
    """Возвращает площади стен и пола (для Web/Mobile)."""
    from core.measures import calculate_room_areas
    return calculate_room_areas(room_id)
