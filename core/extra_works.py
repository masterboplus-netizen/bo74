"""core.extra_works — Отдельные (внеплановые) работы.

Доп работы: демонтаж, срочные переделки, "доделать после прораба".
Добавляются в смету объекта отдельной строкой.
"""
from core.db import fetchone, fetchall, commit
from core import spec


def add_extra_work(object_id, title, qty=1, price=0, unit='шт', note=None):
    """Добавляет внеплановую работу. Возвращает work_id."""
    total = round((qty or 0) * (price or 0), 2)
    return commit(
        """INSERT INTO extra_works
           (object_id, title, qty, unit, price, total, note)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (object_id, title, qty, unit, price, total, note)
    )


def get_extra_work(work_id):
    row = fetchone("SELECT * FROM extra_works WHERE id = ?", (work_id,))
    return dict(row) if row else None


def get_extra_works(object_id):
    rows = fetchall(
        "SELECT * FROM extra_works WHERE object_id = ? ORDER BY id DESC",
        (object_id,)
    )
    return [dict(r) for r in rows]


def delete_extra_work(work_id):
    commit("DELETE FROM extra_works WHERE id = ?", (work_id,))
    return True


def calc_extra_total(object_id):
    rows = fetchall(
        "SELECT COALESCE(SUM(total), 0) as s FROM extra_works WHERE object_id = ?",
        (object_id,)
    )
    return round(rows[0]['s'] if rows else 0, 2)


def format_extra_works(object_id):
    works = get_extra_works(object_id)
    if not works:
        return "🔨 Отдельных работ нет."
    lines = ["🔨 Отдельные работы:", ""]
    total = 0.0
    for w in works:
        lines.append(
            f"   • {w['title']}: {w['qty']} {w['unit']} × {w['price']} ₽ = {w['total']} ₽"
        )
        total += w['total']
    lines.append("")
    lines.append(f"💰 Итого: {round(total, 2)} ₽")
    return "\n".join(lines)
