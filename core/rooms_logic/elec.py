"""core.rooms_logic.elec — логика ЭОМ (без Telegram)."""
from core import elec as core_elec
try:
    from core import elec_panels as core_elec_panels
except Exception:
    core_elec_panels = None


def get_groups_by_room(room_id: int) -> list:
    """Группы ЭОМ комнаты (для Web/Mobile)."""
    if not core_elec:
        return []
    return core_elec.get_groups_by_room(room_id) or []


def get_panels_by_object(object_id: int) -> list:
    """Щиты объекта (для Web/Mobile)."""
    if not core_elec_panels:
        return []
    return core_elec_panels.get_panels(object_id) or []


def get_room_elec_summary(room_id: int) -> dict:
    """Сводка ЭОМ комнаты (группы, нагрузка, кабели)."""
    groups = get_groups_by_room(room_id)
    total_watt = sum(g.get('load_watt') or 0 for g in groups)
    return {
        'groups_count': len(groups),
        'total_watt': total_watt,
        'groups': [{'id': g.get('id'), 'name': g.get('name'),
                    'load_watt': g.get('load_watt'), 'phase': g.get('phase')} for g in groups],
    }
