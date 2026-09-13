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