"""Модуль личных расходов БО 7.4"""
from db import get_connection
from datetime import datetime, timedelta


def add_personal_expense(amount: int, category: str, note: str = None) -> int:
    """Добавляет личный расход (не привязан к объекту)"""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO finance (object_id, category, amount, type, date, note, is_personal) "
        "VALUES (NULL, ?, ?, 'expense', DATE('now'), ?, 1)",
        (category, amount, note)
    )
    finance_id = c.lastrowid
    conn.commit()
    conn.close()
    return finance_id


def get_personal_summary(period: str = 'month') -> dict:
    """Сводка личных расходов за период.
    period: 'today' | 'week' | 'month' | 'all'"""
    today = datetime.now().date()
    if period == 'today':
        start = today.strftime('%Y-%m-%d')
    elif period == 'week':
        start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    elif period == 'month':
        start = today.replace(day=1).strftime('%Y-%m-%d')
    else:  # all
        start = '1970-01-01'

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM finance "
        "WHERE is_personal = 1 AND type = 'expense' AND date >= ?",
        (start,)
    )
    row = c.fetchone()
    total, count = row[0] or 0, row[1] or 0

    # Разбивка по категориям
    c.execute(
        "SELECT category, COALESCE(SUM(amount), 0) FROM finance "
        "WHERE is_personal = 1 AND type = 'expense' AND date >= ? "
        "GROUP BY category ORDER BY SUM(amount) DESC",
        (start,)
    )
    by_category = [{'category': r[0] or 'прочее', 'amount': r[1]} for r in c.fetchall()]
    conn.close()

    return {
        'total': total,
        'count': count,
        'by_category': by_category,
        'period': period,
        'start': start
    }


def get_personal_last_entries(limit: int = 10) -> list:
    """Последние N личных расходов"""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, category, amount, date, note FROM finance "
        "WHERE is_personal = 1 AND type = 'expense' "
        "ORDER BY date DESC, id DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return [
        {'id': r[0], 'category': r[1], 'amount': r[2], 'date': r[3], 'note': r[4]}
        for r in rows
    ]
