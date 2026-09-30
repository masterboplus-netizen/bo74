"""core.rooms — управление комнатами.

Комната — центральная сущность цифрового двойника объекта.
"""
from core.db import fetchone, fetchall, commit, get_conn


DEFAULT_ROOMS = [
    "Ванная", "Кухня", "Зал", "Спальня",
    "Коридор", "Балкон", "Гардеробная", "Гостиная",
    "Санузел", "Детская",
]


def create_room(object_id, name, is_default=False, order_num=0, tenant_id=1, room_type='rough', measure_method='laser'):
    """Создаёт комнату. Возвращает room_id или None если уже есть."""
    name = (name or "").strip()
    if not name:
        return None
    existing = fetchone(
        "SELECT id FROM rooms WHERE object_id = ? AND LOWER(name) = LOWER(?)",
        (object_id, name)
    )
    if existing:
        return existing['id']
    return commit(
        "INSERT INTO rooms (object_id, name, is_default, order_num, tenant_id, room_type, measure_method) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (object_id, name, 1 if is_default else 0, order_num, tenant_id, room_type, measure_method)
    )


def get_room(room_id):
    """Возвращает комнату по id."""
    row = fetchone(
        "SELECT id, object_id, name, is_default, order_num, note, "
        "area_sqm, height, tenant_id, created_at, room_type, "
        "height_bottom, height_middle, height_top, measure_method "
        "FROM rooms WHERE id = ?",
        (room_id,)
    )
    return dict(row) if row else None


def get_rooms(object_id):
    """Все комнаты объекта."""
    rows = fetchall(
        "SELECT id, name, is_default, order_num, area_sqm, height "
        "FROM rooms WHERE object_id = ? "
        "ORDER BY is_default DESC, order_num ASC, id ASC",
        (object_id,)
    )
    return [dict(r) for r in rows]


def get_room_by_name(object_id, name):
    """Комната по имени (регистронезависимо)."""
    row = fetchone(
        "SELECT id, object_id, name FROM rooms "
        "WHERE object_id = ? AND LOWER(name) = LOWER(?)",
        (object_id, (name or "").strip())
    )
    return dict(row) if row else None


def update_room(room_id, name=None, note=None, area_sqm=None, height=None,
                room_type=None, height_bottom=None, height_middle=None, height_top=None,
                measure_method=None):
    """Обновляет комнату. None — не трогать."""
    fields, params = [], []
    if name is not None:
        fields.append("name = ?"); params.append(name.strip())
    if note is not None:
        fields.append("note = ?"); params.append(note)
    if area_sqm is not None:
        fields.append("area_sqm = ?"); params.append(area_sqm)
    if height is not None:
        fields.append("height = ?"); params.append(height)
    if room_type is not None:
        fields.append("room_type = ?"); params.append(room_type)
    if height_bottom is not None:
        fields.append("height_bottom = ?"); params.append(height_bottom)
    if height_middle is not None:
        fields.append("height_middle = ?"); params.append(height_middle)
    if height_top is not None:
        fields.append("height_top = ?"); params.append(height_top)
    if measure_method is not None:
        fields.append("measure_method = ?"); params.append(measure_method)
    if not fields:
        return False
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(room_id)
    commit(f"UPDATE rooms SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_room(room_id):
    """Удаляет комнату. Отвязывает tasks/photos/finance."""
    room = get_room(room_id)
    if not room:
        return False
    commit("UPDATE tasks SET room_id = NULL WHERE room_id = ?", (room_id,))
    commit("UPDATE photos SET room_id = NULL WHERE room_id = ?", (room_id,))
    commit("UPDATE finance SET room_id = NULL WHERE room_id = ?", (room_id,))
    commit("UPDATE supplies SET room_id = NULL WHERE room_id = ?", (room_id,))
    commit("DELETE FROM room_measures WHERE room_id = ?", (room_id,))
    commit("DELETE FROM room_comms WHERE room_id = ?", (room_id,))
    commit("DELETE FROM room_objects WHERE room_id = ?", (room_id,))
    commit("DELETE FROM room_history WHERE room_id = ?", (room_id,))
    commit("DELETE FROM rooms WHERE id = ?", (room_id,))
    return True


def ensure_default_rooms(object_id, tenant_id=1):
    """Создаёт базовые комнаты, если их нет (для новых объектов)."""
    created = []
    for i, name in enumerate(DEFAULT_ROOMS):
        rid = create_room(object_id, name, is_default=True, order_num=i, tenant_id=tenant_id)
        if rid:
            created.append((rid, name))
    return created


def count_tasks_by_room(room_id):
    """Количество задач в комнате (по статусам)."""
    row = fetchone(
        "SELECT "
        "COUNT(*) as total, "
        "SUM(CASE WHEN status IN ('open','in_progress') THEN 1 ELSE 0 END) as open_cnt, "
        "SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done_cnt "
        "FROM tasks WHERE room_id = ?",
        (room_id,)
    )
    if not row:
        return {'total': 0, 'open': 0, 'done': 0}
    return {
        'total': row['total'] or 0,
        'open': row['open_cnt'] or 0,
        'done': row['done_cnt'] or 0,
    }
