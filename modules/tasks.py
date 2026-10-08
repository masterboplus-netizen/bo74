"""Модуль задач БО 7.7"""
from db import get_connection


def create_task(object_id: int, title: str, description: str = "", deadline: str = None, priority: str = 'medium', assigned_to: int = None) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (object_id, title, description, deadline, priority, assigned_to) VALUES (?, ?, ?, ?, ?, ?)",
        (object_id, title, description, deadline, priority, assigned_to)
    )
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id


def close_task(task_id: int, user_id: int = None):
    conn = get_connection()
    c = conn.cursor()
    # Читаем старый статус для истории
    c.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    old_status = row['status'] if row else 'open'
    c.execute("UPDATE tasks SET status = 'done', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))
    c.execute("INSERT INTO task_history (task_id, old_status, new_status, changed_by) VALUES (?, ?, 'done', ?)", (task_id, old_status, user_id))
    conn.commit()
    conn.close()


def cancel_task(task_id: int, reason: str = None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'cancelled' WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def get_active_tasks(user_id: int = None) -> list:
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT id, object_id, title, status, priority, deadline, assigned_to FROM tasks WHERE status IN ('open', 'in_progress')"
    params = []
    if user_id:
        query += " AND assigned_to = ?"
        params.append(user_id)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'object_id': r[1], 'title': r[2], 'status': r[3], 'priority': r[4], 'deadline': r[5], 'assigned_to': r[6]} for r in rows]


def get_tasks_by_object(object_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title, status, priority, type, assigned_to, deadline FROM tasks WHERE object_id = ? AND status NOT IN ('archived', 'cancelled')", (object_id,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'title': r[1], 'status': r[2], 'priority': r[3], 'type': r[4], 'assigned_to': r[5], 'deadline': r[6]} for r in rows]

def get_tasks_stats_by_object(object_id: int) -> dict:
    """Статистика задач объекта: всего, выполнено, открыто, просрочено"""
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tasks WHERE object_id = ?", (object_id,))
    total = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM tasks WHERE object_id = ? AND status = 'done'", (object_id,))
    done = c.fetchone()[0] or 0
    c.execute(
        "SELECT COUNT(*) FROM tasks WHERE object_id = ? AND status IN ('open', 'in_progress')",
        (object_id,)
    )
    open_count = c.fetchone()[0] or 0
    c.execute(
        "SELECT COUNT(*) FROM tasks WHERE object_id = ? AND status IN ('open', 'in_progress') "
        "AND deadline IS NOT NULL AND deadline < ?",
        (object_id, today)
    )
    overdue = c.fetchone()[0] or 0
    conn.close()
    return {
        'total': total,
        'done': done,
        'open': open_count,
        'overdue': overdue,
        'percent_done': int(done / total * 100) if total > 0 else 0
    }


def assign_task(task_id: int, tg_id: int = None):
    """Назначает задачу на юзера. tg_id=None — снять назначение."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE tasks SET assigned_to = ? WHERE id = ?", (tg_id, task_id))
    conn.commit()
    conn.close()

def get_tasks_by_assignee(tg_id: int) -> list:
    """Активные задачи конкретного исполнителя."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.object_id, t.title, t.status, t.priority, t.deadline,
               o.name as object_name
        FROM tasks t
        LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.assigned_to = ? AND t.status IN ('open', 'in_progress')
        ORDER BY (t.deadline IS NULL), t.deadline ASC
    """, (tg_id,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r['id'], 'object_id': r['object_id'], 'title': r['title'],
             'status': r['status'], 'priority': r['priority'],
             'deadline': r['deadline'], 'object_name': r['object_name']} for r in rows]


def set_task_range(task_id: int, start: str = None, end: str = None):
    """Устанавливает диапазон дат для задачи.
    start/end в формате YYYY-MM-DD. None — убрать.
    При задании диапазона одиночный deadline обнуляется."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE tasks SET deadline_start = ?, deadline_end = ?, deadline = NULL WHERE id = ?',
              (start, end, task_id))
    conn.commit()
    conn.close()

def get_task_range(task_id: int) -> dict:
    """Возвращает диапазон задачи."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT deadline, deadline_start, deadline_end FROM tasks WHERE id = ?', (task_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return {'deadline': None, 'start': None, 'end': None}
    return {'deadline': r[0], 'start': r[1], 'end': r[2]}


def update_task(task_id, title=None, description=None, priority=None,
                assigned_to=None, deadline=None, status=None):
    """Обновляет поля задачи. None — не менять."""
    conn = get_connection()
    c = conn.cursor()
    fields = []
    params = []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if priority is not None:
        fields.append("priority = ?")
        params.append(priority)
    if assigned_to is not None:
        fields.append("assigned_to = ?")
        params.append(assigned_to)
    if deadline is not None:
        fields.append("deadline = ?")
        params.append(deadline)
    if status is not None:
        fields.append("status = ?")
        params.append(status)
    if not fields:
        conn.close()
        return False
    params.append(task_id)
    c.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return True


# ============================================================
# ДНЕВНИК РАБОТ (task_progress)
# ============================================================

def add_progress(task_id, hours=None, qty=None, unit=None, description=None,
                 raw_text=None, type="work", source="text", user_id=None):
    """Добавляет запись в дневник работ."""
    from core.db import commit
    return commit(
        """INSERT INTO task_progress
        (task_id, user_id, hours, qty, unit, description, raw_text, type, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (task_id, user_id, hours, qty, unit, description, raw_text, type, source)
    )


def get_task_progress(task_id, limit=50):
    """Все записи по задаче."""
    from core.db import fetchall
    rows = fetchall(
        "SELECT * FROM task_progress WHERE task_id = ? ORDER BY work_date DESC, id DESC LIMIT ?",
        (task_id, limit)
    )
    return [dict(r) for r in rows]


def calc_task_hours(task_id):
    """Сумма часов по всем записям."""
    from core.db import fetchone
    r = fetchone("SELECT COALESCE(SUM(hours), 0) AS s FROM task_progress WHERE task_id = ?", (task_id,))
    return round(float(r["s"]) if r else 0, 2)


def calc_task_qty(task_id):
    """Сумма объёма по всем записям type=work."""
    from core.db import fetchone
    r = fetchone("SELECT COALESCE(SUM(qty), 0) AS s FROM task_progress WHERE task_id = ? AND type = 'work'", (task_id,))
    return round(float(r["s"]) if r else 0, 2)


def calc_task_rework(task_id):
    """Сумма переделок."""
    from core.db import fetchone
    r = fetchone("SELECT COALESCE(SUM(qty), 0) AS s FROM task_progress WHERE task_id = ? AND type = 'rework'", (task_id,))
    return round(float(r["s"]) if r else 0, 2)


def format_progress_bar(percent):
    """Прогресс-бар"""
    percent = max(0, min(100, int(percent or 0)))
    filled = percent // 10
    return chr(0x2588) * filled + chr(0x2591) * (10 - filled) + " " + str(percent) + "%"


def format_task_progress(task_id):
    """Текстовый дневник задачи."""
    rows = get_task_progress(task_id)
    if not rows:
        return "_Записей пока нет._"
    lines = []
    for r in rows[:10]:
        d = str(r.get("work_date") or "?")
        h = r.get("hours")
        q = r.get("qty")
        u = r.get("unit") or ""
        desc = r.get("description") or r.get("raw_text") or ""
        t = r.get("type") or "work"
        icon = {"work": chr(0x1f528), "rework": chr(0x1f504), "pause": chr(0x23f8), "material": chr(0x1f4e6)}.get(t, chr(0x1f528))
        parts = [d]
        if h: parts.append(str(h) + "ч")
        if q: parts.append(str(q) + " " + u)
        line = chr(0x2022) + " " + " · ".join(parts)
        if desc:
            line += " — " + str(desc)[:60]
        lines.append(icon + " " + line)
    return chr(10).join(lines)
