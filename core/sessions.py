"""core.sessions — сессии замеров.

Один объект — много версий замеров (initial, furniture, final).
Все замеры привязаны к session_id.
"""
from core.db import fetchone, fetchall, commit


def create_session(room_id, session_type='initial', label=None, created_by=None):
    """Создаёт новую сессию. Деактивирует старые. Возвращает session_id."""
    # Деактивируем старые
    commit("UPDATE measurement_sessions SET is_active = 0 WHERE room_id = ?", (room_id,))
    # Создаём новую
    return commit(
        """INSERT INTO measurement_sessions
           (room_id, session_type, session_label, created_by, is_active)
           VALUES (?, ?, ?, ?, 1)""",
        (room_id, session_type, label, created_by)
    )


def get_active_session(room_id):
    """Возвращает активную сессию или None."""
    row = fetchone(
        "SELECT * FROM measurement_sessions WHERE room_id = ? AND is_active = 1 LIMIT 1",
        (room_id,)
    )
    return dict(row) if row else None


def list_sessions(room_id):
    """Все сессии комнаты (по дате DESC)."""
    rows = fetchall(
        "SELECT * FROM measurement_sessions WHERE room_id = ? ORDER BY created_at DESC",
        (room_id,)
    )
    return [dict(r) for r in rows]


def get_session(session_id):
    """Одна сессия по id."""
    row = fetchone("SELECT * FROM measurement_sessions WHERE id = ?", (session_id,))
    return dict(row) if row else None


def set_active_session(session_id):
    """Делает сессию активной, остальные — нет."""
    session = get_session(session_id)
    if not session:
        return False
    commit("UPDATE measurement_sessions SET is_active = 0 WHERE room_id = ?", (session['room_id'],))
    commit("UPDATE measurement_sessions SET is_active = 1 WHERE id = ?", (session_id,))
    return True


def delete_session(session_id):
    """Удаляет сессию + все связанные замеры."""
    session = get_session(session_id)
    if not session:
        return False
    room_id = session['room_id']
    # Удаляем связанные замеры
    commit("DELETE FROM room_measures WHERE session_id = ?", (session_id,))
    commit("DELETE FROM openings WHERE session_id = ?", (session_id,))
    commit("DELETE FROM wall_niches WHERE session_id = ?", (session_id,))
    commit("DELETE FROM room_comms WHERE session_id = ?", (session_id,))
    # Удаляем сессию
    commit("DELETE FROM measurement_sessions WHERE id = ?", (session_id,))
    # Если была активной — делаем активной самую свежую оставшуюся
    remaining = list_sessions(room_id)
    if remaining:
        commit("UPDATE measurement_sessions SET is_active = 1 WHERE id = ?", (remaining[0]['id'],))
    return True


def ensure_session(room_id, session_type='initial', created_by=None):
    """Возвращает активную сессию или создаёт новую."""
    s = get_active_session(room_id)
    if s:
        return s['id']
    return create_session(room_id, session_type, None, created_by)


def get_session_summary(session_id):
    """Сводка по сессии — сколько чего замерено."""
    session = get_session(session_id)
    if not session:
        return None
    room_id = session['room_id']
    measures = fetchone("SELECT COUNT(*) as cnt FROM room_measures WHERE session_id = ?", (session_id,))
    openings = fetchone("SELECT COUNT(*) as cnt FROM openings WHERE session_id = ?", (session_id,))
    niches = fetchone("SELECT COUNT(*) as cnt FROM wall_niches WHERE session_id = ?", (session_id,))
    comms = fetchone("SELECT COUNT(*) as cnt FROM room_comms WHERE session_id = ?", (session_id,))
    return {
        'session': session,
        'measures': measures['cnt'] if measures else 0,
        'openings': openings['cnt'] if openings else 0,
        'niches': niches['cnt'] if niches else 0,
        'comms': comms['cnt'] if comms else 0,
    }
