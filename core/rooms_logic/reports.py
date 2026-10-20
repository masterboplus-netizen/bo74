"""core.rooms_logic.reports — логика отчётов (без Telegram)."""
from core.measures import calculate_room_areas, get_walls_ordered
from core.openings import get_openings
from core.niches import get_niches


def get_room_report(room_id: int) -> dict:
    """Полный отчёт по комнате (для Web/Mobile)."""
    walls = get_walls_ordered(room_id)
    openings = get_openings(room_id)
    niches = get_niches(room_id)
    areas = calculate_room_areas(room_id)
    return {
        'walls_count': len(walls),
        'openings_count': len(openings),
        'niches_count': len(niches),
        'areas': areas,
        'walls': walls,
        'openings': openings,
        'niches': niches,
    }
