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


# ============================================================
# НИШИ (несколько на стену, разные размеры низа/верха)
# ============================================================

def add_niche(measure_id, room_id, name=None,
              offset_x=None, offset_y=None,
              width_bottom=None, width_top=None,
              height=None,
              depth_bottom=None, depth_top=None,
              niche_type='rect', note=None):
    """Добавляет нишу на стену. Возвращает niche_id."""
    return commit(
        "INSERT INTO wall_niches "
        "(measure_id, room_id, name, offset_x, offset_y, "
        "width_bottom, width_top, height, depth_bottom, depth_top, "
        "niche_type, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (measure_id, room_id, name, offset_x, offset_y,
         width_bottom, width_top, height, depth_bottom, depth_top,
         niche_type, note)
    )

def get_niches(measure_id):
    """Все ниши стены."""
    rows = fetchall(
        "SELECT * FROM wall_niches WHERE measure_id = ? ORDER BY id",
        (measure_id,)
    )
    return [dict(r) for r in rows]

def get_niches_by_room(room_id):
    """Все ниши комнаты."""
    rows = fetchall(
        "SELECT * FROM wall_niches WHERE room_id = ? ORDER BY measure_id, id",
        (room_id,)
    )
    return [dict(r) for r in rows]

def update_niche(niche_id, **kwargs):
    """Обновляет поля ниши."""
    allowed = {"name", "offset_x", "offset_y", "width_bottom", "width_top",
               "height", "depth_bottom", "depth_top", "niche_type", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(niche_id)
    commit(f"UPDATE wall_niches SET {', '.join(fields)} WHERE id = ?", params)
    return True

def delete_niche(niche_id):
    commit("DELETE FROM wall_niches WHERE id = ?", (niche_id,))
    return True

def format_niche(n):
    """Форматирует нишу для UI."""
    name = n.get('name') or 'Ниша'
    wb = n.get('width_bottom') or 0
    wt = n.get('width_top') or 0
    h = n.get('height') or 0
    db_ = n.get('depth_bottom') or 0
    dt = n.get('depth_top') or 0
    if abs(wb - wt) < 0.1 and abs(db_ - dt) < 0.1:
        # Обычная прямоугольная
        return f"🕳 {name}: {wb}×{h}×{db_} см"
    else:
        # Разные низ/верх
        return (f"🕳 {name}: низ {wb}×{db_} см, верх {wt}×{dt} см, "
                f"высота {h} см")


# ============================================================
# НАКЛОНЫ СТЕНЫ
# ============================================================

def add_wall_lean(measure_id, room_id,
                  lean_angle=None, lean_direction=None,
                  offset_top_x=None, offset_top_y=None,
                  twist_angle=None, note=None):
    """Добавляет/обновляет наклон стены. Возвращает lean_id."""
    existing = get_wall_lean(measure_id)
    if existing:
        update_wall_lean(measure_id,
                         lean_angle=lean_angle,
                         lean_direction=lean_direction,
                         offset_top_x=offset_top_x,
                         offset_top_y=offset_top_y,
                         twist_angle=twist_angle,
                         note=note)
        return existing['id']
    return commit(
        "INSERT INTO wall_lean "
        "(measure_id, room_id, lean_angle, lean_direction, "
        "offset_top_x, offset_top_y, twist_angle, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (measure_id, room_id, lean_angle, lean_direction,
         offset_top_x, offset_top_y, twist_angle, note)
    )

def get_wall_lean(measure_id):
    """Возвращает наклон стены (или None)."""
    row = fetchone(
        "SELECT * FROM wall_lean WHERE measure_id = ?",
        (measure_id,)
    )
    return dict(row) if row else None

def update_wall_lean(measure_id, **kwargs):
    """Обновляет наклон стены."""
    allowed = {"lean_angle", "lean_direction", "offset_top_x", "offset_top_y",
               "twist_angle", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(measure_id)
    commit(f"UPDATE wall_lean SET {', '.join(fields)} WHERE measure_id = ?", params)
    return True

def delete_wall_lean(measure_id):
    commit("DELETE FROM wall_lean WHERE measure_id = ?", (measure_id,))
    return True


# ============================================================
# УГЛЫ МЕЖДУ СТЕНАМИ (corners)
# ============================================================

def add_corner(room_id, corner_number,
               corner_type='straight', angle_value=None,
               radius=None, radius_note=None,
               deviation_bottom=None, deviation_top=None,
               note=None):
    """Добавляет/обновляет угол комнаты. Возвращает corner_id."""
    existing = get_corner(room_id, corner_number)
    if existing:
        update_corner(existing['id'],
                      corner_type=corner_type,
                      angle_value=angle_value,
                      radius=radius,
                      radius_note=radius_note,
                      deviation_bottom=deviation_bottom,
                      deviation_top=deviation_top,
                      note=note)
        return existing['id']
    return commit(
        "INSERT INTO wall_corners "
        "(room_id, corner_number, corner_type, angle_value, "
        "radius, radius_note, deviation_bottom, deviation_top, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (room_id, corner_number, corner_type, angle_value,
         radius, radius_note, deviation_bottom, deviation_top, note)
    )

def get_corner(room_id, corner_number):
    """Конкретный угол комнаты."""
    row = fetchone(
        "SELECT * FROM wall_corners WHERE room_id = ? AND corner_number = ?",
        (room_id, corner_number)
    )
    return dict(row) if row else None

def get_corners(room_id):
    """Все углы комнаты."""
    rows = fetchall(
        "SELECT * FROM wall_corners WHERE room_id = ? ORDER BY corner_number",
        (room_id,)
    )
    return [dict(r) for r in rows]

def update_corner(corner_id, **kwargs):
    """Обновляет поля угла."""
    allowed = {"corner_type", "angle_value", "radius", "radius_note",
               "deviation_bottom", "deviation_top", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(corner_id)
    commit(f"UPDATE wall_corners SET {', '.join(fields)} WHERE id = ?", params)
    return True

def delete_corner(corner_id):
    commit("DELETE FROM wall_corners WHERE id = ?", (corner_id,))
    return True

def format_corner(c):
    """Форматирует угол для UI."""
    num = c.get('corner_number')
    ctype = c.get('corner_type', 'straight')
    angle = c.get('angle_value')
    radius = c.get('radius')

    type_names = {
        'straight': '📐 Прямой',
        'rounded': '🔄 Закруглённый',
        'angled': '📐 Наклонный',
        'irregular': '❓ Неправильный',
    }
    name = type_names.get(ctype, ctype)

    parts = [f"Угол {num}: {name}"]
    if angle:
        parts.append(f"{angle}°")
    if radius:
        parts.append(f"R={radius} см")
    return " · ".join(parts)


# ============================================================
# ПРОГРЕСС ОБХОДА СТЕН
# ============================================================

def start_walls_round(room_id):
    """Помечает начало обхода стен."""
    from datetime import datetime
    commit(
        "UPDATE rooms SET walls_started_at = ? WHERE id = ?",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), room_id)
    )

def complete_walls_round(room_id):
    """Помечает завершение обхода стен."""
    from datetime import datetime
    commit(
        "UPDATE rooms SET walls_completed_at = ? WHERE id = ?",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), room_id)
    )

def get_walls_progress(room_id):
    """Возвращает прогресс обхода стен.
    Возвращает: {'started': bool, 'completed': bool,
                 'walls_count': int, 'current_step': int}
    """
    room = fetchone(
        "SELECT walls_started_at, walls_completed_at, contour_check_passed "
        "FROM rooms WHERE id = ?",
        (room_id,)
    )
    if not room:
        return {'started': False, 'completed': False,
                'walls_count': 0, 'current_step': 1}

    # Считаем, сколько стен замерено
    walls = fetchall(
        "SELECT id, wall_pos, order_num FROM room_measures "
        "WHERE room_id = ? AND category = 'wall' "
        "ORDER BY COALESCE(order_num, id)",
        (room_id,)
    )
    walls_count = len(walls)

    return {
        'started': bool(room.get('walls_started_at')),
        'completed': bool(room.get('walls_completed_at')),
        'contour_passed': bool(room.get('contour_check_passed')),
        'walls_count': walls_count,
        'current_step': walls_count + 1 if walls_count < 4 else 4,
        'walls': [dict(w) for w in walls],
    }

def get_wall_by_pos(room_id, wall_pos):
    """Находит стену по позиции (напротив / слева / у входа / справа)."""
    row = fetchone(
        "SELECT * FROM room_measures "
        "WHERE room_id = ? AND category = 'wall' AND wall_pos = ? "
        "ORDER BY id DESC LIMIT 1",
        (room_id, wall_pos)
    )
    return dict(row) if row else None

def get_walls_ordered(room_id):
    """Все стены комнаты в порядке обхода (order_num)."""
    rows = fetchall(
        "SELECT * FROM room_measures "
        "WHERE room_id = ? AND category = 'wall' "
        "ORDER BY COALESCE(order_num, id)",
        (room_id,)
    )
    return [dict(r) for r in rows]

