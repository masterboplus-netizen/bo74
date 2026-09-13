"""Модуль задач БО 7.2"""
from db import get_connection


def create_task(object_id: int, title: str, description: str = "", deadline: str = None, priority: str = 'medium') -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (object_id, title, description, deadline, priority) VALUES (?, ?, ?, ?, ?)",
        (object_id, title, description, deadline, priority)
    )
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id


def close_task(task_id: int, user_id: int = None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'done', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))
    c.execute("INSERT INTO task_history (task_id, old_status, new_status, changed_by) VALUES (?, 'open', 'done', ?)", (task_id, user_id))
    conn.commit()
    conn.close()


def cancel_task(task_id: int, reason: str = None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'cancelled' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def get_active_tasks(user_id: int = None) -> list:
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT id, object_id, title, status, priority, deadline FROM tasks WHERE status IN ('open', 'in_progress')"
    params = []
    if user_id:
        query += " AND assigned_to = ?"
        params.append(user_id)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'object_id': r[1], 'title': r[2], 'status': r[3], 'priority': r[4], 'deadline': r[5]} for r in rows]


def get_tasks_by_object(object_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title, status, priority, type, assigned_to, deadline FROM tasks WHERE object_id = ? AND status != 'archived'", (object_id,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'title': r[1], 'status': r[2], 'priority': r[3], 'type': r[4], 'assigned_to': r[5], 'deadline': r[6]} for r in rows]