"""core.rooms_logic.comm — логика коммуникаций (без Telegram)."""
from core.comms import get_comms, add_comm, delete_comm


def get_comm_list(room_id: int) -> list:
    """Список коммуникаций комнаты (для Web/Mobile)."""
    comms = get_comms(room_id)
    return [{'id': c.get('id'), 'type': c.get('comm_type'), 'wall': c.get('wall'),
             'offset_x': c.get('offset_x'), 'offset_y': c.get('offset_y')} for c in comms]


def add_comm_point(room_id: int, comm_type: str, wall: str, offset_x: float = None, offset_y: float = None) -> bool:
    """Добавить коммуникацию (для Web/Mobile)."""
    try:
        add_comm(room_id=room_id, comm_type=comm_type, wall=wall, offset_x=offset_x, offset_y=offset_y)
        return True
    except Exception as e:
        print(f'add_comm_point: {e}', flush=True)
        return False


def delete_comm_point(comm_id: int) -> bool:
    """Удалить коммуникацию."""
    try:
        delete_comm(comm_id)
        return True
    except Exception:
        return False
