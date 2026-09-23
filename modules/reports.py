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


def get_object_photos_stats(object_id: int) -> dict:
    """Статистика фото объекта: всего + по этапам."""
    from db import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM photos WHERE object_id = ?", (object_id,))
    total = c.fetchone()[0] or 0

    c.execute("""
        SELECT stage, COUNT(*) as cnt FROM photos
        WHERE object_id = ?
        GROUP BY stage
    """, (object_id,))
    by_stage = {}
    for r in c.fetchall():
        by_stage[r['stage'] or 'progress'] = r['cnt']
    conn.close()
    return {'total': total, 'by_stage': by_stage}


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

    # Фото
    try:
        ph = get_object_photos_stats(report['object']['id'])
        if ph['total'] > 0:
            text += f"\n📸 ФОТО: {ph['total']}\n"
            stage_names = {'before': '📸 До', 'progress': '🔵 Процесс', 'after': '✅ После', 'document': '📄 Документы'}
            for st, cnt in ph['by_stage'].items():
                text += f"  • {stage_names.get(st, st)}: {cnt}\n"
    except Exception:
        pass

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

# ============================================================
# ОТЧЁТЫ ПО ЗАДАЧАМ (за период, по объектам)
# ============================================================

def get_closed_tasks_report(period: str = 'week') -> dict:
    """Закрытые задачи за период, сгруппированные по объектам.
    period: 'today' | 'week' | 'month' | 'all'"""
    start, end = get_period_dates(period)

    conn = get_connection_from_db()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.title, t.completed_at, t.priority,
               o.id as obj_id, o.name as obj_name
        FROM tasks t
        LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status = 'done'
          AND t.completed_at IS NOT NULL
          AND DATE(t.completed_at) >= ?
          AND DATE(t.completed_at) <= ?
        ORDER BY o.name, t.completed_at DESC
    """, (start, end))
    rows = c.fetchall()
    conn.close()

    by_object = {}
    for r in rows:
        obj_name = r['obj_name'] or 'Без объекта'
        if obj_name not in by_object:
            by_object[obj_name] = {
                'object_id': r['obj_id'],
                'tasks': []
            }
        by_object[obj_name]['tasks'].append({
            'id': r['id'],
            'title': r['title'],
            'completed_at': r['completed_at'],
            'priority': r['priority'],
        })

    total = sum(len(v['tasks']) for v in by_object.values())

    return {
        'period': period,
        'start': start,
        'end': end,
        'total': total,
        'by_object': by_object,
    }


def format_closed_tasks_report(report: dict) -> str:
    """Форматирует отчёт о закрытых задачах."""
    period_names = {
        'today': 'сегодня',
        'week': 'за 7 дней',
        'month': 'за месяц',
        'all': 'за всё время',
    }
    period_name = period_names.get(report['period'], report['period'])

    if report['total'] == 0:
        return f"✅ Что сделано ({period_name}):\n\nЗадач не закрыто."

    text = f"✅ ЧТО СДЕЛАНО ({period_name})\n"
    text += f"Всего закрыто: {report['total']}\n\n"

    for obj_name, data in report['by_object'].items():
        text += f"🏗️ {obj_name} ({len(data['tasks'])})\n"
        for t in data['tasks']:
            # Дата закрытия
            d = ''
            if t['completed_at']:
                try:
                    d = ' — ' + t['completed_at'][:10]
                except Exception:
                    pass
            text += f"  • #{t['id']} {t['title']}{d}\n"
        text += "\n"

    if len(text) > 4000:
        text = text[:3900] + "\n\n... (список обрезан)"

    return text


def get_open_tasks_report() -> dict:
    """Открытые + просроченные задачи, сгруппированные по объектам."""
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')

    conn = get_connection_from_db()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.title, t.status, t.deadline, t.priority,
               o.id as obj_id, o.name as obj_name
        FROM tasks t
        LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status IN ('open', 'in_progress')
        ORDER BY (t.deadline IS NULL), t.deadline ASC
    """)
    rows = c.fetchall()
    conn.close()

    by_object = {}
    total = 0
    overdue_total = 0

    for r in rows:
        obj_name = r['obj_name'] or 'Без объекта'
        if obj_name not in by_object:
            by_object[obj_name] = {'object_id': r['obj_id'], 'tasks': []}

        is_overdue = bool(r['deadline'] and r['deadline'] < today)
        if is_overdue:
            overdue_total += 1

        by_object[obj_name]['tasks'].append({
            'id': r['id'],
            'title': r['title'],
            'status': r['status'],
            'deadline': r['deadline'],
            'priority': r['priority'],
            'overdue': is_overdue,
        })
        total += 1

    return {
        'total': total,
        'overdue': overdue_total,
        'by_object': by_object,
    }


def format_open_tasks_report(report: dict) -> str:
    """Форматирует отчёт о задачах в работе."""
    if report['total'] == 0:
        return "🔄 Что в работе:\n\nНет открытых задач."

    text = f"🔄 ЧТО В РАБОТЕ\n"
    text += f"Всего: {report['total']}"
    if report['overdue']:
        text += f" (из них просрочено: {report['overdue']})"
    text += "\n\n"

    for obj_name, data in report['by_object'].items():
        text += f"🏗️ {obj_name} ({len(data['tasks'])})\n"
        for t in data['tasks']:
            d = ''
            if t['deadline']:
                mark = '🔴 ' if t['overdue'] else ''
                d = f" — {mark}{t['deadline']}"
            text += f"  • #{t['id']} {t['title']}{d}\n"
        text += "\n"

    if len(text) > 4000:
        text = text[:3900] + "\n\n... (список обрезан)"

    return text


def get_connection_from_db():
    """Локальный импорт, чтобы не тянуть в начало файла."""
    from db import get_connection
    return get_connection()
