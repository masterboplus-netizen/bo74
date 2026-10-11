"""core.report_schedule — Расписание автоотчётов.

Управление автоотчётами: ежедневные, еженедельные, ежемесячные.
"""
from core.db import fetchone, fetchall, commit
from datetime import datetime, timedelta


FREQ_LABELS = {
    "daily": "Ежедневно",
    "weekly": "Еженедельно",
    "monthly": "Ежемесячно",
}


def create_schedule(object_id, template="summary", frequency="weekly",
                    weekday=0, day_of_month=1, hour=9, minute=0,
                    client_id=None):
    """Создаёт расписание отчёта. Возвращает schedule_id."""
    now = datetime.now()
    if frequency == "daily":
        nxt = now + timedelta(days=1)
    elif frequency == "weekly":
        nxt = now + timedelta(days=7)
    else:
        nxt = now + timedelta(days=30)
    return commit(
        """INSERT INTO report_schedule
           (client_id, object_id, template, frequency, weekday, day_of_month,
            hour, minute, next_send, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (client_id, object_id, template, frequency, weekday, day_of_month,
         hour, minute, nxt.strftime("%Y-%m-%d %H:%M:%S"))
    )


def list_schedules(object_id=None):
    if object_id:
        rows = fetchall(
            "SELECT * FROM report_schedule WHERE object_id = ? AND active = 1 ORDER BY id",
            (object_id,)
        )
    else:
        rows = fetchall(
            "SELECT * FROM report_schedule WHERE active = 1 ORDER BY id"
        )
    return [dict(r) for r in rows]


def delete_schedule(schedule_id):
    commit("UPDATE report_schedule SET active = 0 WHERE id = ?", (schedule_id,))
    return True


def format_schedules(object_id=None):
    rows = list_schedules(object_id)
    if not rows:
        return "📅 Расписаний нет."
    lines = ["📅 Расписания автоотчётов:", ""]
    for r in rows:
        freq = FREQ_LABELS.get(r.get("frequency"), r.get("frequency"))
        h = r.get("hour") or 0
        m = r.get("minute") or 0
        nxt = r.get("next_send") or "?"
        lines.append(f"   • #{r['id']} {freq} в {h:02d}:{m:02d} → {nxt}")
    return "\n".join(lines)
