"""Модуль объектов БО 7.2"""
from db import get_connection
from datetime import datetime


def create_object(name: str, address: str = None, budget: int = 0, user_id: int = None) -> int:
    conn = get_connection()
    c = conn.cursor()
    code = f"OBJ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
    c.execute("SELECT id, code, name, address, status, budget FROM objects WHERE name LIKE ? AND status != 'archived'", (f'%{name}%',))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'code': row[1], 'name': row[2], 'address': row[3], 'status': row[4], 'budget': row[5]}
    return None


def get_all_objects() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, code, name, status FROM objects WHERE status != 'archived' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'code': r[1], 'name': r[2], 'status': r[3]} for r in rows]


def update_object_status(object_id: int, status: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE objects SET status = ? WHERE id = ?", (status, object_id))
    conn.commit()
    conn.close()