"""Веб-дашборд Бо 7.4 — на встроенном http.server, без зависимостей"""
import http.server
import socketserver
import json
import urllib.parse
from datetime import date, timedelta
from db import get_connection

PORT = 8080


def get_summary():
    """Сводка по всем объектам"""
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

    c.execute("SELECT COALESCE(SUM(amount), 0) FROM finance WHERE type = 'expense' AND is_personal = 1")
    personal_expense = c.fetchone()[0] or 0

    conn.close()
    return {
        'objects_count': objects_count,
        'tasks_open': tasks_open,
        'tasks_done': tasks_done,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_balance': total_income - total_expense,
        'personal_expense': personal_expense
    }


def get_objects():
    """Список всех объектов со статистикой"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT o.id, o.name, o.status, o.budget,
               COALESCE(SUM(CASE WHEN f.type = 'income' THEN f.amount ELSE 0 END), 0) as income,
               COALESCE(SUM(CASE WHEN f.type = 'expense' THEN f.amount ELSE 0 END), 0) as expense,
               (SELECT COUNT(*) FROM tasks t WHERE t.object_id = o.id AND t.status IN ('open', 'in_progress')) as tasks_open,
               (SELECT COUNT(*) FROM tasks t WHERE t.object_id = o.id AND t.status = 'done') as tasks_done
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


def get_overdue_tasks():
    """Просроченные задачи"""
    today = date.today().strftime('%Y-%m-%d')
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.title, t.deadline, o.name as obj
        FROM tasks t LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status IN ('open', 'in_progress') AND t.deadline < ?
        ORDER BY t.deadline ASC
    """, (today,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'title': r[1], 'deadline': r[2], 'object': r[3] or '—'} for r in rows]


def get_object_detail(obj_id):
    """Детали объекта"""
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


# ===== HTML-ШАБЛОНЫ =====

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #0f0f0f; color: #e0e0e0; line-height: 1.5; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
h1 { color: #4ade80; margin-bottom: 20px; font-size: 28px; }
h2 { color: #e0e0e0; margin: 24px 0 12px; font-size: 20px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }
.card { background: #1a1a1a; padding: 16px; border-radius: 8px; border: 1px solid #2a2a2a; }
.card .label { color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 6px; }
.card .value { font-size: 24px; font-weight: 600; color: #fff; }
.card.income .value { color: #4ade80; }
.card.expense .value { color: #f87171; }
.card.balance .value { color: #60a5fa; }
table { width: 100%; border-collapse: collapse; background: #1a1a1a; border-radius: 8px; overflow: hidden; }
th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #2a2a2a; }
th { background: #222; color: #888; font-size: 12px; text-transform: uppercase; }
tr:last-child td { border-bottom: none; }
tr:hover { background: #222; }
a { color: #60a5fa; text-decoration: none; }
a:hover { text-decoration: underline; }
.status-active { color: #4ade80; }
.status-paused { color: #fbbf24; }
.status-waiting { color: #a78bfa; }
.positive { color: #4ade80; }
.negative { color: #f87171; }
.overdue { background: #2a1a1a; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #2a2a2a; }
.back { color: #888; font-size: 14px; }
.priority-high { color: #f87171; }
.priority-medium { color: #fbbf24; }
.priority-low { color: #4ade80; }
.done { color: #4ade80; }
.open { color: #60a5fa; }
"""


def render_dashboard():
    s = get_summary()
    objs = get_objects()
    overdue = get_overdue_tasks()

    rows = ""
    for o in objs:
        bal_class = "positive" if o['balance'] >= 0 else "negative"
        rows += f"""
        <tr>
            <td><a href="/object/{o['id']}">{o['name']}</a></td>
            <td class="status-{o['status']}">{o['status']}</td>
            <td>{o['tasks_open']} / {o['tasks_done']}</td>
            <td class="positive">{o['income']:,} ₽</td>
            <td class="negative">{o['expense']:,} ₽</td>
            <td class="{bal_class}">{o['balance']:,} ₽</td>
        </tr>"""

    overdue_rows = ""
    for t in overdue:
        overdue_rows += f"""
        <tr class="overdue">
            <td>#{t['id']}</td>
            <td>{t['title']}</td>
            <td>{t['object']}</td>
            <td>{t['deadline']}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Бо 7.4 — Дашборд</title>
    <style>{CSS}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🤖 Бо 7.4 — Дашборд</h1>
        <span style="color:#666;font-size:14px;">{date.today().strftime('%d.%m.%Y')}</span>
    </div>

    <div class="cards">
        <div class="card"><div class="label">Объектов</div><div class="value">{s['objects_count']}</div></div>
        <div class="card"><div class="label">Открытых задач</div><div class="value">{s['tasks_open']}</div></div>
        <div class="card"><div class="label">Выполнено</div><div class="value">{s['tasks_done']}</div></div>
        <div class="card income"><div class="label">Доход</div><div class="value">{s['total_income']:,} ₽</div></div>
        <div class="card expense"><div class="label">Расход</div><div class="value">{s['total_expense']:,} ₽</div></div>
        <div class="card balance"><div class="label">Баланс</div><div class="value">{s['total_balance']:,} ₽</div></div>
    </div>

    <h2>🏗️ Объекты</h2>
    <table>
        <thead><tr><th>Объект</th><th>Статус</th><th>Задачи (откр/вып)</th><th>Доход</th><th>Расход</th><th>Баланс</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>

    {f'<h2>⚠️ Просроченные задачи ({len(overdue)})</h2><table><thead><tr><th>ID</th><th>Задача</th><th>Объект</th><th>Срок</th></tr></thead><tbody>{overdue_rows}</tbody></table>' if overdue else ''}

    <p style="margin-top:32px;color:#555;font-size:12px;">Бо 7.4 · Replit · {date.today().strftime('%Y-%m-%d')}</p>
</div>
</body>
</html>"""


def render_object(obj):
    if not obj:
        return "<h1>Объект не найден</h1>"

    task_rows = ""
    for t in obj['tasks'][:50]:
        status_class = "done" if t['status'] == 'done' else "open"
        prio_class = f"priority-{t['priority'] or 'medium'}"
        task_rows += f"""
        <tr>
            <td>#{t['id']}</td>
            <td>{t['title']}</td>
            <td class="{status_class}">{t['status']}</td>
            <td class="{prio_class}">{t['priority'] or '—'}</td>
            <td>{t['deadline'] or '—'}</td>
        </tr>"""

    fin_rows = ""
    for f in obj['finance']:
        color = "positive" if f['type'] == 'income' else "negative"
        sign = "+" if f['type'] == 'income' else "−"
        fin_rows += f"""
        <tr>
            <td>{f['date']}</td>
            <td>{f['category'] or '—'}</td>
            <td class="{color}">{sign}{f['amount']:,} ₽</td>
            <td>{f['note'] or ''}</td>
        </tr>"""

    bal_class = "positive" if obj['balance'] >= 0 else "negative"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{obj['name']} — Бо 7.4</title>
    <style>{CSS}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🏗️ {obj['name']}</h1>
        <a class="back" href="/">← К дашборду</a>
    </div>

    <div class="cards">
        <div class="card"><div class="label">Статус</div><div class="value status-{obj['status']}">{obj['status']}</div></div>
        <div class="card"><div class="label">Бюджет</div><div class="value">{obj['budget']:,} ₽</div></div>
        <div class="card income"><div class="label">Доход</div><div class="value">{obj['income']:,} ₽</div></div>
        <div class="card expense"><div class="label">Расход</div><div class="value">{obj['expense']:,} ₽</div></div>
        <div class="card balance"><div class="label">Баланс</div><div class="value {bal_class}">{obj['balance']:,} ₽</div></div>
    </div>

    <h2>📋 Задачи ({len(obj['tasks'])})</h2>
    <table>
        <thead><tr><th>ID</th><th>Задача</th><th>Статус</th><th>Приоритет</th><th>Срок</th></tr></thead>
        <tbody>{task_rows or '<tr><td colspan="5" style="text-align:center;color:#666;">Нет задач</td></tr>'}</tbody>
    </table>

    <h2>💰 Финансы ({len(obj['finance'])})</h2>
    <table>
        <thead><tr><th>Дата</th><th>Категория</th><th>Сумма</th><th>Заметка</th></tr></thead>
        <tbody>{fin_rows or '<tr><td colspan="4" style="text-align:center;color:#666;">Нет операций</td></tr>'}</tbody>
    </table>
</div>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '':
            html = render_dashboard()
        elif path.startswith('/object/'):
            try:
                obj_id = int(path.split('/')[-1])
                obj = get_object_detail(obj_id)
                html = render_object(obj)
            except Exception as e:
                html = f"<h1>Ошибка: {e}</h1>"
        elif path == '/api/summary':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(get_summary(), ensure_ascii=False).encode('utf-8'))
            return
        elif path == '/api/objects':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(get_objects(), ensure_ascii=False).encode('utf-8'))
            return
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"<h1>404</h1>")
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        print(f"🌐 {self.address_string()} — {format % args}")


if __name__ == '__main__':
    print(f"🚀 Дашборд Бо 7.4 запущен: http://0.0.0.0:{PORT}")
    print(f"📊 В браузере открой: https://<твой-домен>.replit.dev:{PORT}")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n⏹️ Дашборд остановлен")
