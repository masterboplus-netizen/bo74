"""Модуль пользователей БО 7.4"""
from db import get_connection


def save_user(tg_id: int, name: str = None, username: str = None, role: str = 'guest') -> int:
    """Сохраняет юзера при /start. Если есть — обновляет имя."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    if row:
        # НЕ трогаем role у существующего юзера — только имя
        c.execute("UPDATE users SET name = ? WHERE tg_id = ?", (name, tg_id))
        user_id = row['id']
    else:
        c.execute("INSERT INTO users (tg_id, name, role) VALUES (?, ?, ?)", (tg_id, name, role))
        user_id = c.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user(tg_id: int) -> dict:
    """Получить юзера по tg_id"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, tg_id, name, role FROM users WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row['id'], 'tg_id': row['tg_id'], 'name': row['name'], 'role': row['role']}
    return None


def get_all_users(role: str = None) -> list:
    """Получить всех юзеров (опционально по роли)"""
    conn = get_connection()
    c = conn.cursor()
    if role:
        c.execute("SELECT id, tg_id, name, role FROM users WHERE role = ?", (role,))
    else:
        c.execute("SELECT id, tg_id, name, role FROM users")
    rows = c.fetchall()
    conn.close()
    return [{'id': r['id'], 'tg_id': r['tg_id'], 'name': r['name'], 'role': r['role']} for r in rows]


def set_role(tg_id: int, role: str):
    """Установить роль юзеру"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET role = ? WHERE tg_id = ?", (role, tg_id))
    conn.commit()
    conn.close()


def mark_onboarded(tg_id: int):
    """Отметить, что юзер прошёл онбординг."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET onboarded=1 WHERE tg_id=?", (tg_id,))
        conn.commit()
    except Exception as e:
        print(f"⚠️ mark_onboarded: {e}")
    finally:
        conn.close()


def is_onboarded(tg_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT onboarded FROM users WHERE tg_id=?", (tg_id,))
        row = c.fetchone()
        return bool(row and row[0])
    except Exception:
        return False
    finally:
        conn.close()
