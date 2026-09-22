"""Веб-дашборд Бо 7.5 — Flask"""
from flask import Flask, render_template, request
from datetime import date, timedelta
import sys
sys.path.insert(0, '/home/runner/workspace')

from db import get_connection

app = Flask(__name__)


def get_summary():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM objects WHERE status IN ('active', 'paused', 'waiting')")
    objects_count = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('open', 'in_progress')")
    tasks_open = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'done'")
    tasks_done = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance WHERE type = 'income'")
    total_income = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance WHERE type = 'expense'")
    total_expense = c.fetchone()[0] or 0
    conn.close()
    return {
        'objects_count': objects_count,
        'tasks_open': tasks_open,
        'tasks_done': tasks_done,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_balance': total_income - total_expense,
    }


def get_objects():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT o.id, o.name, o.status, o.budget,
               COALESCE(SUM(CASE WHEN f.type = 'income' THEN f.amount ELSE 0 END), 0),
               COALESCE(SUM(CASE WHEN f.type = 'expense' THEN f.amount ELSE 0 END), 0),
               (SELECT COUNT(*) FROM tasks t WHERE t.object_id = o.id AND t.status IN ('open', 'in_progress')),
               (SELECT COUNT(*) FROM tasks t WHERE t.object_id = o.id AND t.status = 'done')
        FROM objects o
        LEFT JOIN finance f ON f.object_id = o.id
        WHERE o.status != 'archived'
        GROUP BY o.id
        ORDER BY o.name
    """)
    rows = c.fetchall()
    conn.close()
    return [{
        'id': r[0], 'name': r[1], 'status': r[2], 'budget': r[3],
        'income': r[4], 'expense': r[5], 'balance': r[4] - r[5],
        'tasks_open': r[6], 'tasks_done': r[7]
    } for r in rows]


def get_overdue():
    today = date.today().strftime('%Y-%m-%d')
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.title, t.deadline, o.name
        FROM tasks t LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status IN ('open', 'in_progress') AND t.deadline < ?
        ORDER BY t.deadline ASC
    """, (today,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'title': r[1], 'deadline': r[2], 'object': r[3] or '—'} for r in rows]


def get_object(obj_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, address, status, budget FROM objects WHERE id = ?", (obj_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    obj = {'id': row[0], 'name': row[1], 'address': row[2], 'status': row[3], 'budget': row[4]}
    c.execute("SELECT id, title, status, deadline, priority FROM tasks WHERE object_id = ? ORDER BY id DESC", (obj_id,))
    obj['tasks'] = [{'id': r[0], 'title': r[1], 'status': r[2], 'deadline': r[3], 'priority': r[4]} for r in c.fetchall()]
    c.execute("SELECT id, category, amount, date, note, type FROM finance WHERE object_id = ? ORDER BY date DESC, id DESC LIMIT 50", (obj_id,))
    obj['finance'] = [{'id': r[0], 'category': r[1], 'amount': r[2], 'date': r[3], 'note': r[4], 'type': r[5]} for r in c.fetchall()]
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance WHERE object_id = ? AND type = 'income'", (obj_id,))
    obj['income'] = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance WHERE object_id = ? AND type = 'expense'", (obj_id,))
    obj['expense'] = c.fetchone()[0] or 0
    obj['balance'] = obj['income'] - obj['expense']
    conn.close()
    return obj


@app.route('/')
def dashboard():
    return render_template('dashboard.html',
                          summary=get_summary(),
                          objects=get_objects(),
                          overdue=get_overdue(),
                          today=date.today().strftime('%d.%m.%Y'))


@app.route('/object/<int:obj_id>')
def object_detail(obj_id):
    obj = get_object(obj_id)
    if not obj:
        return "Объект не найден", 404
    return render_template('object.html', obj=obj)


if __name__ == '__main__':
    print("🚀 Дашборд Бо 7.5: http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)
