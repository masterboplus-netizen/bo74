"""Утренний дайджест и вечерний опрос БО 7.4"""
from datetime import datetime, date, timedelta
from db import get_connection
from modules.users import get_all_users
from modules.objects import get_all_objects


def build_morning_digest() -> str:
    """Утренний дайджест: задачи на сегодня + просрочка + объекты"""
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')

    conn = get_connection()
    c = conn.cursor()

    # Задачи на сегодня
    c.execute("""
        SELECT t.id, t.title, o.name as obj
        FROM tasks t LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status IN ('open', 'in_progress') AND t.deadline = ?
        ORDER BY t.priority DESC, t.id
    """, (today_str,))
    today_tasks = c.fetchall()

    # Просроченные
    c.execute("""
        SELECT t.id, t.title, t.deadline, o.name as obj
        FROM tasks t LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status IN ('open', 'in_progress') AND t.deadline < ?
        ORDER BY t.deadline ASC
    """, (today_str,))
    overdue = c.fetchall()

    # Задачи без срока
    c.execute("""
        SELECT COUNT(*) as cnt
        FROM tasks t
        WHERE t.status IN ('open', 'in_progress') AND (t.deadline IS NULL OR t.deadline = '')
    """)
    no_deadline_cnt = c.fetchone()['cnt']

    # Объекты
    c.execute("SELECT COUNT(*) as cnt FROM objects WHERE status IN ('active', 'paused', 'waiting')")
    obj_cnt = c.fetchone()['cnt']

    conn.close()

    today_str_ru = today.strftime('%d.%m.%Y')
    text = f"☀️ Доброе утро!\n📅 {today_str_ru}\n\n"

    if today_tasks:
        text += f"📋 На сегодня ({len(today_tasks)}):\n"
        for t in today_tasks:
            obj = t['obj'] or 'без объекта'
            text += f"• #{t['id']} {t['title']} — {obj}\n"
        text += "\n"
    else:
        text += "📋 На сегодня задач нет\n\n"

    if overdue:
        text += f"🔴 Просрочено ({len(overdue)}):\n"
        for t in overdue:
            obj = t['obj'] or 'без объекта'
            d = t['deadline']
            text += f"• #{t['id']} {t['title']} ({d}) — {obj}\n"
        text += "\n"

    if no_deadline_cnt:
        text += f"⚪ Без срока: {no_deadline_cnt} задач\n\n"

    text += f"🏗️ Активных объектов: {obj_cnt}\n"
    text += f"\nКоманды: /tasks /objects /finance"

    return text


def build_evening_survey() -> str:
    """Вечерний опрос: что сделал за день"""
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    today_str_ru = today.strftime('%d.%m.%Y')

    conn = get_connection()
    c = conn.cursor()

    # Что закрыто сегодня
    c.execute("""
        SELECT t.id, t.title, o.name as obj
        FROM tasks t LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status = 'done' AND DATE(t.completed_at) = ?
    """, (today_str,))
    done_today = c.fetchall()

    # Что осталось на сегодня
    c.execute("""
        SELECT t.id, t.title, o.name as obj
        FROM tasks t LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status IN ('open', 'in_progress') AND t.deadline = ?
    """, (today_str,))
    left_today = c.fetchall()

    conn.close()

    text = f"🌙 Вечерний отчёт\n📅 {today_str_ru}\n\n"

    if done_today:
        text += f"✅ Сделано сегодня ({len(done_today)}):\n"
        for t in done_today:
            obj = t['obj'] or 'без объекта'
            text += f"• {t['title']} — {obj}\n"
        text += "\n"
    else:
        text += "✅ Сегодня ничего не закрыто\n\n"

    if left_today:
        text += f"⏳ Осталось на сегодня ({len(left_today)}):\n"
        for t in left_today:
            obj = t['obj'] or 'без объекта'
            text += f"• #{t['id']} {t['title']} — {obj}\n"
        text += "\n"
        text += "Закрыть задачу: /done <id>"

    return text


async def send_morning_digest(context):
    """Отправляет утренний дайджест всем юзерам"""
    users = get_all_users()
    if not users:
        print("⚠️ Дайджест: нет юзеров в БД")
        return
    text = build_morning_digest()
    for u in users:
        try:
            await context.bot.send_message(chat_id=u['tg_id'], text=text)
        except Exception as e:
            print(f"⚠️ Не смог отправить {u['tg_id']}: {e}")
    print(f"✅ Утренний дайджест отправлен ({len(users)} юзеров)")


async def send_evening_survey(context):
    """Отправляет вечерний опрос всем юзерам"""
    users = get_all_users()
    if not users:
        print("⚠️ Вечерний опрос: нет юзеров в БД")
        return
    text = build_evening_survey()
    for u in users:
        try:
            await context.bot.send_message(chat_id=u['tg_id'], text=text)
        except Exception as e:
            print(f"⚠️ Не смог отправить {u['tg_id']}: {e}")
    print(f"✅ Вечерний опрос отправлен ({len(users)} юзеров)")
