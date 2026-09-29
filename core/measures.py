"""core.measures — размеры комнат (гибкие)."""
from core.db import fetchone, fetchall, commit


# Категории размеров
MEASURE_CATEGORIES = [
    ("wall", "🧱 Стена"),
    ("floor", "📏 Пол"),
    ("ceiling", "⬆️ Потолок"),
    ("window", "🪟 Окно"),
    ("door", "🚪 Дверь"),
    ("opening", "🕳 Проём"),
    ("corner", "📐 Угол"),
    ("other", "📦 Прочее"),
]


def add_measure(room_id, category, label=None, length=None, width=None,
                height=None, depth=None, angle=None, unit="м", note=None,
                tenant_id=1, created_by=None,
                wall_pos=None, angle_value=None, angle_method=None,
                angle_diagonal_cm=None, has_rounded=None, radius=None,
                rounded_corner=None,
                measured_bottom=None, measured_middle=None, measured_top=None,
                is_wavy=None, deviation_plus=None, deviation_minus=None):
    """Добавляет размер. Возвращает measure_id."""
    return commit(
        "INSERT INTO room_measures "
        "(room_id, category, label, length, width, height, depth, angle, "
        "unit, note, tenant_id, created_by, "
        "wall_pos, angle_value, angle_method, angle_diagonal_cm, "
        "has_rounded, radius, rounded_corner, "
        "measured_bottom, measured_middle, measured_top, "
        "is_wavy, deviation_plus, deviation_minus) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (room_id, category, label, length, width, height, depth, angle,
         unit, note, tenant_id, created_by,
         wall_pos, angle_value, angle_method, angle_diagonal_cm,
         has_rounded, radius, rounded_corner,
         measured_bottom, measured_middle, measured_top,
         is_wavy, deviation_plus, deviation_minus)
    )


def get_measure(measure_id):
    row = fetchone(
        "SELECT * FROM room_measures WHERE id = ?", (measure_id,)
    )
    return dict(row) if row else None


def get_measures(room_id, category=None):
    """Все размеры комнаты (опц. фильтр по категории)."""
    if category:
        rows = fetchall(
            "SELECT * FROM room_measures WHERE room_id = ? AND category = ? "
            "ORDER BY id",
            (room_id, category)
        )
    else:
        rows = fetchall(
            "SELECT * FROM room_measures WHERE room_id = ? ORDER BY category, id",
            (room_id,)
        )
    return [dict(r) for r in rows]


def update_measure(measure_id, **kwargs):
    """Обновляет поля размера. kwargs: length, width, ..."""
    allowed = {"label", "length", "width", "height", "depth", "angle",
               "unit", "note", "category"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(measure_id)
    commit(f"UPDATE room_measures SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_measure(measure_id):
    commit("DELETE FROM room_measures WHERE id = ?", (measure_id,))
    return True


def calculate_room_areas(room_id):
    """Считает площади: стены, пол, потолок. Учитывает окна/двери."""
    measures = get_measures(room_id)
    walls_total = 0.0
    walls_without_openings = 0.0
    floor_area = 0.0
    ceiling_area = 0.0
    openings_total = 0.0
    openings = []

    for m in measures:
        L = m.get('length') or 0
        W = m.get('width') or 0
        H = m.get('height') or 0
        cat = m.get('category')
        if cat == 'wall':
            area = L * H if (L and H) else (W * H if (W and H) else 0)
            walls_total += area
        elif cat == 'floor':
            area = L * W if (L and W) else 0
            floor_area += area
        elif cat == 'ceiling':
            area = L * W if (L and W) else 0
            ceiling_area += area
        elif cat in ('window', 'door', 'opening'):
            area = L * H if (L and H) else (L * W if (L and W) else 0)
            openings_total += area
            openings.append({'label': m.get('label') or cat, 'area': round(area, 2)})

    walls_without_openings = max(walls_total - openings_total, 0)

    return {
        'walls_total': round(walls_total, 2),
        'walls_net': round(walls_without_openings, 2),
        'floor': round(floor_area, 2),
        'ceiling': round(ceiling_area, 2),
        'openings_total': round(openings_total, 2),
        'openings': openings,
    }


def format_measure(m):
    """Форматирует один размер в строку."""
    cat_icons = dict(MEASURE_CATEGORIES)
    icon = cat_icons.get(m.get('category'), '📏')
    label = m.get('label') or m.get('category')
    parts = []
    for key, symb in [('length', 'Д'), ('width', 'Ш'), ('height', 'В'),
                      ('depth', 'Г'), ('angle', '°')]:
        v = m.get(key)
        if v:
            if key == 'angle':
                parts.append(f"{int(v)}°")
            else:
                parts.append(f"{symb}{v}")
    dims = ' × '.join(parts) if parts else '—'
    return f"{icon} {label}: {dims}"


def group_measures_by_category(room_id):
    """Возвращает dict: category -> [measures]."""
    measures = get_measures(room_id)
    grouped = {}
    for m in measures:
        cat = m.get('category') or 'other'
        grouped.setdefault(cat, []).append(m)
    return grouped
