"""Утренний дайджест и вечерний опрос БО 7.7"""
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


# === ЛОГ ОТПРАВКИ ДАЙДЖЕСТОВ (защита от пропуска) ===

def log_digest_sent(digest_type: str):
    """Записывает факт отправки дайджеста"""
    from datetime import date
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO digest_log (digest_type, sent_at) VALUES (?, ?)",
            (digest_type, date.today().strftime('%Y-%m-%d'))
        )
        conn.commit()
    except Exception as e:
        print(f"⚠️ log_digest_sent: {e}")
    conn.close()


def was_digest_sent_today(digest_type: str) -> bool:
    """Проверяет, отправлялся ли дайджест сегодня"""
    from datetime import date
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM digest_log WHERE digest_type = ? AND sent_at = ?",
        (digest_type, date.today().strftime('%Y-%m-%d'))
    )
    count = c.fetchone()[0]
    conn.close()
    return count > 0


async def send_morning_digest_with_log(context):
    """Утренний дайджест + запись в лог"""
    await send_morning_digest(context)
    log_digest_sent('morning')


async def send_evening_survey_with_log(context):
    """Вечерний опрос + запись в лог"""
    await send_evening_survey(context)
    log_digest_sent('evening')


async def catch_up_digests(context):
    """Догоняющий дайджест — при запуске бота.
    Если сегодня дайджест пропущен и время уже прошло — отправить сейчас."""
    from datetime import datetime, timezone, timedelta

    # МСК = UTC+3
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    hour_msk = now_msk.hour

    # Утренний дайджест — 9:00 МСК
    if hour_msk >= 9:
        if not was_digest_sent_today('morning'):
            print(f"📬 Догоняю утренний дайджест (сейчас {hour_msk}:xx МСК)")
            await send_morning_digest_with_log(context)
        else:
            print("✅ Утренний дайджест уже отправлен сегодня")

    # Вечерний опрос — 18:00 МСК
    if hour_msk >= 18:
        if not was_digest_sent_today('evening'):
            print(f"📬 Догоняю вечерний опрос (сейчас {hour_msk}:xx МСК)")
            await send_evening_survey_with_log(context)
        else:
            print("✅ Вечерний опрос уже отправлен сегодня")
