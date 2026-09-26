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