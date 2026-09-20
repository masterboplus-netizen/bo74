"""Модуль отчётов БО 7.4"""
from datetime import date, timedelta
from modules.objects import get_object, get_all_objects
from modules.finance import get_finance_by_period, get_finance_by_category, get_finance_summary
from modules.tasks import get_tasks_stats_by_object


def get_period_dates(period: str) -> tuple:
    """Возвращает (start_date, end_date) в формате YYYY-MM-DD"""
    today = date.today()
    end = today.strftime('%Y-%m-%d')
    if period == 'today':
        start = today.strftime('%Y-%m-%d')
    elif period == 'week':
        start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    elif period == 'month':
        start = today.replace(day=1).strftime('%Y-%m-%d')
    else:  # all
        start = '1970-01-01'
    return start, end


def get_object_report(object_id: int, period: str = 'month') -> dict:
    """Полный отчёт по объекту за период"""
    obj = get_object(object_id)
    if not obj:
        return None

    start, end = get_period_dates(period)

    # Финансы
    fin = get_finance_by_period(object_id, start, end)
    by_category = get_finance_by_category(object_id, start, end)

    # Задачи (всего, а не за период — но с разбивкой)
    tasks = get_tasks_stats_by_object(object_id)

    return {
        'object': obj,
        'period': period,
        'start': start,
        'end': end,
        'finance': fin,
        'by_category': by_category,
        'tasks': tasks
    }


def format_object_report(report: dict) -> str:
    """Форматирует отчёт объекта в текст"""
    if not report:
        return "❌ Объект не найден"

    obj = report['object']
    period_names = {
        'today': 'сегодня',
        'week': 'за 7 дней',
        'month': 'за месяц',
        'all': 'за всё время'
    }
    period_name = period_names.get(report['period'], report['period'])

    text = f"📊 ОТЧЁТ: {obj['name']}\n"
    text += f"Период: {period_name} ({report['start']} — {report['end']})\n\n"

    # Финансы
    fin = report['finance']
    text += "💰 ФИНАНСЫ\n"
    text += f"Доход: {fin['income']} ₽\n"
    text += f"Расход: {fin['expense']} ₽\n"
    text += f"Баланс: {fin['balance']} ₽\n\n"

    # По категориям
    if report['by_category']:
        text += "📊 ПО КАТЕГОРИЯМ:\n"
        for item in report['by_category'][:10]:
            text += f"• {item['category']}: {item['amount']} ₽\n"
        text += "\n"

    # Задачи
    t = report['tasks']
    text += "📋 ЗАДАЧИ\n"
    text += f"Всего: {t['total']}\n"
    text += f"Выполнено: {t['done']} ({t['percent_done']}%)\n"
    text += f"В работе: {t['open']}\n"
    if t['overdue']:
        text += f"⚠️ Просрочено: {t['overdue']}\n"

    return text


def get_summary_report(period: str = 'month') -> dict:
    """Сводный отчёт по всем объектам за период"""
    start, end = get_period_dates(period)
    objects = get_all_objects()

    total_income = 0
    total_expense = 0
    objects_data = []

    for o in objects:
        fin = get_finance_by_period(o['id'], start, end)
        if fin['income'] > 0 or fin['expense'] > 0:
            objects_data.append({
                'id': o['id'],
                'name': o['name'],
                'income': fin['income'],
                'expense': fin['expense'],
                'balance': fin['balance']
            })
            total_income += fin['income']
            total_expense += fin['expense']

    return {
        'period': period,
        'start': start,
        'end': end,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_balance': total_income - total_expense,
        'objects': objects_data
    }


def format_summary_report(report: dict) -> str:
    """Форматирует сводный отчёт в текст"""
    period_names = {
        'today': 'сегодня',
        'week': 'за 7 дней',
        'month': 'за месяц',
        'all': 'за всё время'
    }
    period_name = period_names.get(report['period'], report['period'])

    text = f"📊 СВОДНЫЙ ОТЧЁТ ({period_name})\n\n"
    text += f"💰 Доход: {report['total_income']} ₽\n"
    text += f"💸 Расход: {report['total_expense']} ₽\n"
    text += f"💼 Баланс: {report['total_balance']} ₽\n\n"

    if report['objects']:
        text += "🏗️ ПО ОБЪЕКТАМ:\n"
        for o in report['objects'][:15]:
            sign = "+" if o['balance'] >= 0 else ""
            text += f"• {o['name']}: {sign}{o['balance']} ₽\n"
    else:
        text += "За этот период операций не было."

    return text
