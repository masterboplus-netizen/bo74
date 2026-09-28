"""core.db — универсальный адаптер БД.

Обёртка над существующим db.get_connection().
Позволяет ядру работать независимо от интерфейса.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_connection as _get_conn


def get_conn():
    """Возвращает соединение с БД (SQLite, row_factory = Row)."""
    return _get_conn()


def execute(query, params=None):
    """Выполняет запрос, возвращает cursor."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(query, params or ())
    return conn, c


def fetchone(query, params=None):
    """Возвращает одну строку или None."""
    conn, c = execute(query, params)
    row = c.fetchone()
    conn.close()
    return row


def fetchall(query, params=None):
    """Возвращает все строки."""
    conn, c = execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


def commit(query, params=None):
    """Выполняет INSERT/UPDATE/DELETE с commit. Возвращает lastrowid."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(query, params or ())
    last_id = c.lastrowid
    conn.commit()
    conn.close()
    return last_id
