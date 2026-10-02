"""Модуль объектов БО 7.7"""
import uuid
from db import get_connection


def create_object(name: str, address: str = None, budget: int = 0, user_id: int = None) -> int:
    conn = get_connection()
    c = conn.cursor()
    code = f"OBJ-{uuid.uuid4().hex[:8].upper()}"
    c.execute(
        "INSERT INTO objects (code, name, address, budget, created_by) VALUES (?, ?, ?, ?, ?)",
        (code, name, address, budget, user_id)
    )
    object_id = c.lastrowid
    conn.commit()
    conn.close()
    return object_id


def get_object(object_id: int) -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, code, name, address, status, budget FROM objects WHERE id = ?", (object_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'code': row[1], 'name': row[2], 'address': row[3], 'status': row[4], 'budget': row[5]}
    return None


def get_object_by_name(name: str) -> dict:
    conn = get_connection()
    c = conn.cursor()
    # 1. Точное совпадение
    c.execute("SELECT id, code, name, address, status, budget FROM objects WHERE LOWER(name) = LOWER(?) AND status != 'archived' LIMIT 1", (name,))
    row = c.fetchone()
    # 2. Fallback — LIKE
    if not row:
        c.execute("SELECT id, code, name, address, status, budget FROM objects WHERE LOWER(name) LIKE LOWER(?) AND status != 'archived' ORDER BY LENGTH(name) ASC LIMIT 1", (f'%{name}%',))
        row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'code': row[1], 'name': row[2], 'address': row[3], 'status': row[4], 'budget': row[5]}
    return None


def get_all_objects() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, code, name, status FROM objects WHERE status IN ('active', 'paused', 'waiting') ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'code': r[1], 'name': r[2], 'status': r[3]} for r in rows]


VALID_STATUSES = ('active', 'paused', 'waiting', 'completed', 'closed', 'archived')

def update_object_status(object_id: int, status: str):
    if status not in VALID_STATUSES:
        raise ValueError(f'Недопустимый статус: {status}. Доступно: {VALID_STATUSES}')
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE objects SET status = ? WHERE id = ?", (status, object_id))
    conn.commit()
    conn.close()

def update_object(object_id, name=None, address=None, budget=None, status=None):
    """Обновляет поля объекта. None — не менять."""
    conn = get_connection()
    c = conn.cursor()
    fields = []
    params = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if address is not None:
        fields.append("address = ?")
        params.append(address)
    if budget is not None:
        fields.append("budget = ?")
        params.append(budget)
    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f'Недопустимый статус: {status}')
        fields.append("status = ?")
        params.append(status)
    if not fields:
        conn.close()
        return False
    params.append(object_id)
    c.execute(f"UPDATE objects SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return True


def delete_object(object_id):
    """Удаляет объект и всё связанное."""
    from db import get_connection
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM room_measures WHERE room_id IN (SELECT id FROM rooms WHERE object_id = ?)", (object_id,))
        c.execute("DELETE FROM wall_niches WHERE room_id IN (SELECT id FROM rooms WHERE object_id = ?)", (object_id,))
        c.execute("DELETE FROM openings WHERE room_id IN (SELECT id FROM rooms WHERE object_id = ?)", (object_id,))
        c.execute("DELETE FROM room_comms WHERE room_id IN (SELECT id FROM rooms WHERE object_id = ?)", (object_id,))
        c.execute("DELETE FROM room_objects WHERE room_id IN (SELECT id FROM rooms WHERE object_id = ?)", (object_id,))
        c.execute("DELETE FROM rooms WHERE object_id = ?", (object_id,))
        c.execute("UPDATE tasks SET object_id = NULL WHERE object_id = ?", (object_id,))
        c.execute("UPDATE finance SET object_id = NULL WHERE object_id = ?", (object_id,))
        c.execute("DELETE FROM objects WHERE id = ?", (object_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"⚠️ delete_object: {e}", flush=True)
        return False
    finally:
        conn.close()


def update_object(object_id, name=None, status=None, address=None, note=None):
    """Обновляет объект."""
    from db import get_connection
    fields, params = [], []
    if name is not None:
        fields.append("name = ?"); params.append(name)
    if status is not None:
        fields.append("status = ?"); params.append(status)
    if address is not None:
        fields.append("address = ?"); params.append(address)
    if note is not None:
        fields.append("note = ?"); params.append(note)
    if not fields:
        return False
    params.append(object_id)
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(f"UPDATE objects SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        return True
    except Exception as e:
        print(f"⚠️ update_object: {e}", flush=True)
        return False
    finally:
        conn.close()
