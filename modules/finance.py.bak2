"""Модуль финансов БО 7.2"""
from db import get_connection


def add_expense(object_id: int, amount: int, category: str, note: str = None, is_personal: bool = False) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO finance (object_id, category, amount, type, date, note, is_personal) VALUES (?, ?, ?, 'expense', DATE('now'), ?, ?)",
        (object_id, category, amount, note, 1 if is_personal else 0)
    )
    finance_id = c.lastrowid
    conn.commit()
    conn.close()
    return finance_id


def add_income(object_id: int, amount: int, category: str, note: str = None) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO finance (object_id, category, amount, type, date, note) VALUES (?, ?, ?, 'income', DATE('now'), ?)",
        (object_id, category, amount, note)
    )
    finance_id = c.lastrowid
    conn.commit()
    conn.close()
    return finance_id


def get_finance_summary(object_id: int) -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM finance WHERE object_id = ? AND type = 'expense'", (object_id,))
    expense = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM finance WHERE object_id = ? AND type = 'income'", (object_id,))
    income = c.fetchone()[0] or 0
    conn.close()
    return {'expense': expense, 'income': income, 'balance': income - expense}


def get_personal_expenses() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM finance WHERE is_personal = 1 AND type = 'expense'")
    total = c.fetchone()[0] or 0
    conn.close()
    return total

def get_all_finance_summary():
    """Возвращает финансы по всем объектам"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT o.id, o.name,
               COALESCE(SUM(CASE WHEN f.type = 'income' THEN f.amount ELSE 0 END), 0) as income,
               COALESCE(SUM(CASE WHEN f.type = 'expense' THEN f.amount ELSE 0 END), 0) as expense
        FROM objects o
        LEFT JOIN finance f ON f.object_id = o.id
        WHERE o.status != 'archived'
        GROUP BY o.id, o.name
        ORDER BY o.name
    """)
    rows = c.fetchall()

    # Общая сводка
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance WHERE type = 'income'")
    total_income = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance WHERE type = 'expense'")
    total_expense = c.fetchone()[0] or 0

    conn.close()

    objects = []
    for r in rows:
        objects.append({
            'id': r[0],
            'name': r[1],
            'income': r[2],
            'expense': r[3],
            'balance': r[2] - r[3]
        })

    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'total_balance': total_income - total_expense,
        'objects': objects
    }
