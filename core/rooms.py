"""core.rooms — комнаты (обновлённый под новые поля)."""
from core.db import fetchone, fetchall, commit

DEFAULT_ROOMS = [
    "Ванная", "Кухня", "Зал", "Спальня",
    "Коридор", "Балкон", "Гардеробная", "Гостиная",
    "Санузел", "Детская",
]


def create_room(object_id, name, is_default=False, order_num=0, tenant_id=1,
                room_type='rough', room_subtype=None, measure_method='laser',
                floor_id=None):
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
    if floor_id is None:
        # Автопривязка к первому помещению объекта (или создание «Этаж 1»)
        try:
            _row = fetchone(
                "SELECT id FROM floors WHERE object_id = ? ORDER BY floor_number, id LIMIT 1",
                (object_id,)
            )
            if _row:
                floor_id = _row['id']
            else:
                from core.floors import create_floor
                floor_id = create_floor(object_id, floor_number=1, floor_name="Этаж 1")
        except Exception as e:
            print(f"⚠️ create_room auto-floor: {e}", flush=True)
    return commit(
        """INSERT INTO rooms
           (object_id, name, is_default, order_num, tenant_id,
            room_type, room_subtype, measure_method, floor_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (object_id, name, 1 if is_default else 0, order_num, tenant_id,
         room_type, room_subtype, measure_method, floor_id)
    )


def get_room(room_id):
    row = fetchone(
        """SELECT id, object_id, name, is_default, order_num, note,
                  area_sqm, height, tenant_id, created_at, room_type,
                  height_bottom, height_middle, height_top, measure_method,
                  floor_id, room_subtype, balcony_type, balcony_railing,
                  balcony_railing_height, is_heated
           FROM rooms WHERE id = ?""",
        (room_id,)
    )
    return dict(row) if row else None


def get_rooms(object_id, floor_id=None):
    if floor_id:
        rows = fetchall(
            """SELECT id, name, is_default, order_num, area_sqm, height, room_type
               FROM rooms WHERE object_id = ? AND floor_id = ?
               ORDER BY is_default DESC, order_num ASC, id ASC""",
            (object_id, floor_id)
        )
    else:
        rows = fetchall(
            """SELECT id, name, is_default, order_num, area_sqm, height, room_type
               FROM rooms WHERE object_id = ?
               ORDER BY is_default DESC, order_num ASC, id ASC""",
            (object_id,)
        )
    return [dict(r) for r in rows]


def update_room(room_id, **kwargs):
    """Обновляет поля. None — не трогать."""
    allowed = {"name", "note", "area_sqm", "height", "room_type",
               "height_bottom", "height_middle", "height_top",
               "measure_method", "floor_id", "room_subtype",
               "balcony_type", "balcony_railing", "balcony_railing_height",
               "is_heated"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(room_id)
    commit(f"UPDATE rooms SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_room(room_id):
    """Удаляет комнату + все замеры."""
    room = get_room(room_id)
    if not room:
        return False
    # Отвязываем задачи/фото/финансы
    for table in ('tasks', 'photos', 'finance', 'supplies'):
        try:
            commit(f"UPDATE {table} SET room_id = NULL WHERE room_id = ?", (room_id,))
        except Exception:
            pass
    # Удаляем связанное
    for table in ('room_measures', 'room_comms', 'room_objects',
                  'room_history', 'wall_niches', 'openings',
                  'measurement_sessions'):
        try:
            commit(f"DELETE FROM {table} WHERE room_id = ?", (room_id,))
        except Exception:
            pass
    commit("DELETE FROM rooms WHERE id = ?", (room_id,))
    return True


def ensure_default_rooms(object_id, tenant_id=1):
    created = []
    for i, name in enumerate(DEFAULT_ROOMS):
        rid = create_room(object_id, name, is_default=True, order_num=i, tenant_id=tenant_id)
        if rid:
            created.append((rid, name))
    return created


def count_tasks_by_room(room_id):
    row = fetchone(
        """SELECT COUNT(*) as total,
                  SUM(CASE WHEN status IN ('open','in_progress') THEN 1 ELSE 0 END) as open_cnt,
                  SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done_cnt
           FROM tasks WHERE room_id = ?""",
        (room_id,)
    )
    if not row:
        return {'total': 0, 'open': 0, 'done': 0}
    return {
        'total': row['total'] or 0,
        'open': row['open_cnt'] or 0,
        'done': row['done_cnt'] or 0,
    }
