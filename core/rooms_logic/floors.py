"""core.rooms_logic.floors — логика помещений (без Telegram)."""
try:
    from core import floors as core_floors
except Exception:
    core_floors = None


def get_floors_by_object(object_id: int) -> list:
    """Помещения объекта (для Web/Mobile)."""
    if not core_floors:
        return []
    return core_floors.get_floors(object_id) or []


def get_rooms_by_floor(floor_id: int) -> list:
    """Комнаты помещения."""
    if not core_floors:
        return []
    return core_floors.get_rooms_of_floor(floor_id) or []
