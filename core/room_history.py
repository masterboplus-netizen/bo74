"""core.room_history — история изменений комнаты."""
import json
from core.db import fetchone, fetchall, commit


def add_event(room_id, event_type, event_data=None, user_id=None, tenant_id=1):
    """Добавляет событие в историю.
    event_type: 'measure_added' / 'comm_added' / 'object_added' /
                'task_done' / 'photo_added' / 'conflict' / 'update' / ...
    event_data: dict (сохраняется как JSON).
    """
    data_json = json.dumps(event_data, ensure_ascii=False) if event_data else None
    return commit(
        "INSERT INTO room_history (room_id, event_type, event_data, user_id, tenant_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (room_id, event_type, data_json, user_id, tenant_id)
    )


def get_history(room_id, limit=50):
    """Последние N событий комнаты."""
    rows = fetchall(
        "SELECT id, event_type, event_data, user_id, created_at "
        "FROM room_history WHERE room_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (room_id, limit)
    )
    result = []
    for r in rows:
        d = dict(r)
        if d.get('event_data'):
            try:
                d['event_data'] = json.loads(d['event_data'])
            except Exception:
                pass
        result.append(d)
    return result


def get_history_by_type(room_id, event_type, limit=50):
    """История по конкретному типу события."""
    rows = fetchall(
        "SELECT id, event_type, event_data, user_id, created_at "
        "FROM room_history WHERE room_id = ? AND event_type = ? "
        "ORDER BY id DESC LIMIT ?",
        (room_id, event_type, limit)
    )
    result = []
    for r in rows:
        d = dict(r)
        if d.get('event_data'):
            try:
                d['event_data'] = json.loads(d['event_data'])
            except Exception:
                pass
        result.append(d)
    return result


def count_events_by_type(room_id):
    """Счётчик событий по типам."""
    rows = fetchall(
        "SELECT event_type, COUNT(*) as cnt FROM room_history "
        "WHERE room_id = ? GROUP BY event_type",
        (room_id,)
    )
    return {r['event_type']: r['cnt'] for r in rows}


def clear_history(room_id):
    """Удаляет историю комнаты."""
    commit("DELETE FROM room_history WHERE room_id = ?", (room_id,))
    return True
