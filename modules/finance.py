"""Модуль финансов БО 7.7"""
from db import get_connection


def add_expense(object_id: int, amount: int, category: str, note: str = None, is_personal: bool = False, reimbursable: bool = False) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO finance (object_id, category, amount, type, date, note, is_personal, reimbursable) VALUES (?, ?, ?, 'expense', DATE('now'), ?, ?, ?)",
        (object_id, category, amount, note, 1 if is_personal else 0, 1 if reimbursable else 0)
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
    c.execute("SELECT SUM(amount) FROM finance WHERE object_id = ? AND type = 'expense' AND is_personal = 0", (object_id,))
    expense = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM finance WHERE object_id = ? AND type = 'income'", (object_id,))
    income = c.fetchone()[0] or 0
    conn.close()
    return {'expense': expense, 'income': income, 'balance': income - expense}



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
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance WHERE type = 'expense' AND is_personal = 0")
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


def get_finance_by_period(object_id: int, start_date: str, end_date: str) -> dict:
    """Финансы объекта за период (start и end в формате YYYY-MM-DD)"""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM finance "
        "WHERE object_id = ? AND type = 'income' AND date BETWEEN ? AND ?",
        (object_id, start_date, end_date)
    )
    income = c.fetchone()[0] or 0
    c.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM finance "
        "WHERE object_id = ? AND type = 'expense' AND date BETWEEN ? AND ?",
        (object_id, start_date, end_date)
    )
    expense = c.fetchone()[0] or 0
    conn.close()
    return {'income': income, 'expense': expense, 'balance': income - expense}


def get_finance_by_category(object_id: int, start_date: str, end_date: str) -> list:
    """Расходы объекта по категориям за период"""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT category, COALESCE(SUM(amount), 0) FROM finance "
        "WHERE object_id = ? AND type = 'expense' AND date BETWEEN ? AND ? "
        "GROUP BY category ORDER BY SUM(amount) DESC",
        (object_id, start_date, end_date)
    )
    rows = c.fetchall()
    conn.close()
    return [{'category': r[0] or 'прочее', 'amount': r[1]} for r in rows]
