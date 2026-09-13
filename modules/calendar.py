"""Модуль календаря БО 7.2"""
from db import get_connection
from datetime import datetime, timedelta


def add_calendar_event(user_id: int, object_id: int, task_id: int, title: str, event_date: str, priority: str = 'medium'):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO calendar_events (user_id, object_id, task_id, title, event_date, priority) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, object_id, task_id, title, event_date, priority)
    )
    conn.commit()
    conn.close()


def get_calendar_events(user_id: int, start_date: str, end_date: str) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT ce.id, ce.title, ce.event_date, ce.priority, ce.is_completed, o.name as object_name
        FROM calendar_events ce
        LEFT JOIN objects o ON ce.object_id = o.id
        WHERE ce.user_id = ? AND ce.event_date BETWEEN ? AND ?
        ORDER BY ce.event_date ASC, ce.priority DESC
    """, (user_id, start_date, end_date))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'title': r[1], 'date': r[2], 'priority': r[3], 'completed': r[4], 'object': r[5] or 'Без объекта'} for r in rows]


def get_today_events(user_id: int) -> list:
    today = datetime.now().strftime('%Y-%m-%d')
    return get_calendar_events(user_id, today, today)


def get_week_events(user_id: int) -> list:
    today = datetime.now()
    start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    end = (today + timedelta(days=6 - today.weekday())).strftime('%Y-%m-%d')
    return get_calendar_events(user_id, start, end)