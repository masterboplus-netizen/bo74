"""KPI — эффективность мастеров и здоровье объектов."""
from datetime import date, datetime, timedelta
from db import get_connection


def get_master_kpi(days: int = 30) -> list:
    """KPI по мастерам за N дней."""
    start = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn = get_connection()
    c = conn.cursor()

    # Все юзеры с ролью master/prorab/designer
    c.execute("SELECT tg_id, name, role FROM users WHERE role IN ('master','prorab','designer') ORDER BY name")
    users = c.fetchall()
    result = []
    for u in users:
        tg_id = u['tg_id']
        # Закрытые задачи за период
        c.execute("""
            SELECT t.id, t.completed_at, t.deadline
            FROM tasks t
            WHERE t.assigned_to = ? AND t.status = 'done'
              AND DATE(t.completed_at) >= ?
        """, (tg_id, start))
        done = c.fetchall()
        total_done = len(done)
        in_time = 0
        total_days = 0
        for t in done:
            if t['deadline'] and t['completed_at']:
                try:
                    dl = datetime.strptime(t['deadline'], '%Y-%m-%d').date()
                    ca = datetime.strptime(t['completed_at'][:10], '%Y-%m-%d').date()
                    if ca <= dl:
                        in_time += 1
                except Exception:
                    pass
            if t['completed_at']:
                try:
                    ca = datetime.strptime(t['completed_at'][:10], '%Y-%m-%d').date()
                    # Не считаем среднее время — нет start
                except Exception:
                    pass
        # Открытые задачи
        c.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE assigned_to = ? AND status IN ('open','in_progress')
        """, (tg_id,))
        open_cnt = c.fetchone()[0] or 0
        # Просроченные
        today = date.today().strftime('%Y-%m-%d')
        c.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE assigned_to = ? AND status IN ('open','in_progress')
              AND deadline IS NOT NULL AND deadline < ?
        """, (tg_id, today))
        overdue = c.fetchone()[0] or 0
        pct = int(in_time / total_done * 100) if total_done > 0 else 0
        result.append({
            'tg_id': tg_id, 'name': u['name'], 'role': u['role'],
            'done': total_done, 'in_time': in_time,
            'pct_in_time': pct, 'open': open_cnt, 'overdue': overdue,
        })
    conn.close()
    result.sort(key=lambda x: (-x['done'], x['overdue']))
    return result


def format_master_kpi(masters: list, days: int = 30) -> str:
    """Форматирует KPI мастеров."""
    if not masters:
        return '👤 Нет мастеров для отчёта.\n\nДобавь юзеров через /set_role.'
    text = f'📊 KPI МАСТЕРОВ (за {days} дн.)\n\n'
    for m in masters:
        icons = {'master': '🔧', 'prorab': '👷', 'designer': '🎨'}
        icon = icons.get(m['role'], '👤')
        text += f"{icon} {m['name']}\n"
        text += f"  ✅ Закрыто: {m['done']}\n"
        text += f"  🎯 В срок: {m['in_time']} ({m['pct_in_time']}%)\n"
        text += f"  🔵 В работе: {m['open']}\n"
        if m['overdue']:
            text += f"  ⚠️ Просрочено: {m['overdue']}\n"
        text += '\n'
    return text


def get_object_health() -> list:
    """Здоровье объектов: статус, прогресс, бюджет, проблемы."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, status, budget FROM objects WHERE status IN ('active','paused','waiting') ORDER BY name")
    objects = c.fetchall()
    result = []
    for o in objects:
        # Задачи
        c.execute("SELECT COUNT(*) FROM tasks WHERE object_id = ?", (o['id'],))
        total_t = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM tasks WHERE object_id = ? AND status = 'done'", (o['id'],))
        done_t = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM tasks WHERE object_id = ? AND status IN ('open','in_progress')", (o['id'],))
        open_t = c.fetchone()[0] or 0
        today = date.today().strftime('%Y-%m-%d')
        c.execute("SELECT COUNT(*) FROM tasks WHERE object_id = ? AND status IN ('open','in_progress') AND deadline IS NOT NULL AND deadline < ?", (o['id'], today))
        overdue_t = c.fetchone()[0] or 0
        # Финансы
        c.execute("SELECT COALESCE(SUM(amount),0) FROM finance WHERE object_id = ? AND type='income'", (o['id'],))
        income = c.fetchone()[0] or 0
        c.execute("SELECT COALESCE(SUM(amount),0) FROM finance WHERE object_id = ? AND type='expense'", (o['id'],))
        expense = c.fetchone()[0] or 0
        pct = int(done_t / total_t * 100) if total_t > 0 else 0
        result.append({
            'id': o['id'], 'name': o['name'], 'status': o['status'],
            'budget': o['budget'] or 0,
            'total_tasks': total_t, 'done_tasks': done_t,
            'open_tasks': open_t, 'overdue': overdue_t,
            'pct': pct, 'income': income, 'expense': expense,
            'balance': income - expense,
        })
    conn.close()
    return result


def format_object_health(objects: list) -> str:
    """Форматирует здоровье объектов."""
    if not objects:
        return '🏗️ Нет активных объектов.'
    text = '📊 ЗДОРОВЬЕ ОБЪЕКТОВ\n\n'
    for o in objects:
        # Иконка статуса
        if o['overdue'] > 0:
            health = '🔴'
        elif o['pct'] >= 70:
            health = '🟢'
        elif o['pct'] >= 30:
            health = '🟡'
        else:
            health = '⚪'
        text += f"{health} {o['name']}\n"
        text += f"  📋 Задачи: {o['done_tasks']}/{o['total_tasks']} ({o['pct']}%)\n"
        if o['overdue']:
            text += f"  ⚠️ Просрочено: {o['overdue']}\n"
        text += f"  💰 Баланс: {o['balance']:,} ₽\n".replace(',', ' ')
        text += '\n'
    return text


def get_red_zone() -> list:
    """Проблемные объекты: просрочки, нет движения, застой."""
    conn = get_connection()
    c = conn.cursor()
    today = date.today().strftime('%Y-%m-%d')
    week_ago = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
    c.execute("SELECT id, name FROM objects WHERE status = 'active' ORDER BY name")
    objects = c.fetchall()
    result = []
    for o in objects:
        problems = []
        # Просроченные
        c.execute("SELECT COUNT(*) FROM tasks WHERE object_id = ? AND status IN ('open','in_progress') AND deadline IS NOT NULL AND deadline < ?", (o['id'], today))
        overdue = c.fetchone()[0] or 0
        if overdue:
            problems.append(f'⚠️ {overdue} просрочено')
        # Задачи без движения (не закрыты и не менялись 7 дней)
        c.execute("SELECT COUNT(*) FROM tasks WHERE object_id = ? AND status IN ('open','in_progress') AND (created_at < ? OR created_at IS NULL)", (o['id'], week_ago))
        stale = c.fetchone()[0] or 0
        if stale >= 3:
            problems.append(f'💤 {stale} задач без движения')
        # Бюджет: перерасход
        c.execute("SELECT COALESCE(SUM(amount),0) FROM finance WHERE object_id = ? AND type='expense'", (o['id'],))
        expense = c.fetchone()[0] or 0
        c.execute("SELECT budget FROM objects WHERE id = ?", (o['id'],))
        budget = (c.fetchone() or [0])[0] or 0
        if budget > 0 and expense > budget:
            problems.append(f'💸 Перерасход ({(expense - budget):,} ₽)'.replace(',', ' '))
        if problems:
            result.append({'id': o['id'], 'name': o['name'], 'problems': problems})
    conn.close()
    return result


def format_red_zone(items: list) -> str:
    """Форматирует красную зону."""
    if not items:
        return '✅ ВСЁ ОТЛИЧНО!\n\nПроблемных объектов нет.'
    text = '⚠️ КРАСНАЯ ЗОНА\n\n'
    for o in items:
        text += f"🔴 {o['name']}\n"
        for p in o['problems']:
            text += f'  • {p}\n'
        text += '\n'
    return text
