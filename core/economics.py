"""core.economics — экономика: маржа, P&L, налоги."""
from datetime import date, timedelta
from core.db import fetchone, fetchall, commit


def get_period_dates(period='month'):
    """Возвращает (start, end) в YYYY-MM-DD."""
    today = date.today()
    end = today.strftime('%Y-%m-%d')
    if period == 'today':
        start = end
    elif period == 'week':
        start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    elif period == 'month':
        start = today.replace(day=1).strftime('%Y-%m-%d')
    elif period == 'quarter':
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=q_start_month, day=1).strftime('%Y-%m-%d')
    elif period == 'year':
        start = today.replace(month=1, day=1).strftime('%Y-%m-%d')
    else:  # all
        start = '1970-01-01'
    return start, end


def calc_margin(object_id, period='all'):
    """Маржа по объекту."""
    start, end = get_period_dates(period)
    income_row = fetchone(
        """SELECT COALESCE(SUM(amount), 0) as s FROM finance
           WHERE object_id = ? AND type = 'income' AND date BETWEEN ? AND ?""",
        (object_id, start, end)
    )
    expense_row = fetchone(
        """SELECT COALESCE(SUM(amount), 0) as s FROM finance
           WHERE object_id = ? AND type = 'expense' AND date BETWEEN ? AND ?""",
        (object_id, start, end)
    )
    income = income_row['s'] if income_row else 0
    expense = expense_row['s'] if expense_row else 0
    profit = income - expense
    margin_pct = (profit / income * 100) if income > 0 else 0
    return {
        'object_id': object_id,
        'period': period,
        'income': income,
        'expense': expense,
        'profit': profit,
        'margin_percent': round(margin_pct, 2),
    }


def calc_margin_all(period='all'):
    """Маржа по всем объектам."""
    start, end = get_period_dates(period)
    rows = fetchall(
        """SELECT o.id, o.name,
                  COALESCE(SUM(CASE WHEN f.type='income' THEN f.amount ELSE 0 END), 0) as income,
                  COALESCE(SUM(CASE WHEN f.type='expense' THEN f.amount ELSE 0 END), 0) as expense
           FROM objects o
           LEFT JOIN finance f ON f.object_id = o.id AND f.date BETWEEN ? AND ?
           WHERE o.status != 'archived'
           GROUP BY o.id, o.name
           ORDER BY o.name""",
        (start, end)
    )
    result = []
    for r in rows:
        income = r['income'] or 0
        expense = r['expense'] or 0
        profit = income - expense
        margin_pct = (profit / income * 100) if income > 0 else 0
        result.append({
            'object_id': r['id'],
            'name': r['name'],
            'income': income,
            'expense': expense,
            'profit': profit,
            'margin_percent': round(margin_pct, 2),
        })
    return result


def calc_margin_by_work(object_id, period='all'):
    """Маржа по видам работ (заглушка — требует object_works)."""
    return []


def calc_margin_by_master(object_id, period='all'):
    """Маржа по мастерам (заглушка — требует object_works)."""
    return []


def calc_pnl(period='month'):
    """P&L за период."""
    start, end = get_period_dates(period)
    income_row = fetchone(
        "SELECT COALESCE(SUM(amount), 0) as s FROM finance WHERE type='income' AND date BETWEEN ? AND ?",
        (start, end)
    )
    expense_row = fetchone(
        "SELECT COALESCE(SUM(amount), 0) as s FROM finance WHERE type='expense' AND is_personal=0 AND date BETWEEN ? AND ?",
        (start, end)
    )
    income = income_row['s'] if income_row else 0
    expense = expense_row['s'] if expense_row else 0
    profit = income - expense
    return {
        'period': period,
        'start': start,
        'end': end,
        'income': income,
        'expense': expense,
        'profit': profit,
        'margin_percent': round((profit / income * 100) if income > 0 else 0, 2),
    }


def calc_cashflow(months=3):
    """Кассовый план на N месяцев (заглушка — простая версия)."""
    return []


def calc_taxes(period='month'):
    """Расчёт налогов (заглушка)."""
    return {
        'nds': 0,
        'usn': 0,
        'insurance': 0,
        'ndfl': 0,
        'total': 0,
    }
