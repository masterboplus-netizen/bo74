"""core.room_objects — мебель и техника в комнате."""
from core.db import fetchone, fetchall, commit


OBJ_TYPES = [
    ("furniture", "🪑 Мебель"),
    ("appliance", "🔌 Техника"),
    ("sanitary", "🚿 Сантехника"),
    ("decor", "🖼 Декор"),
    ("lighting", "💡 Освещение"),
    ("other", "📦 Прочее"),
]

STATUSES = [
    ("planned", "📝 Планируется"),
    ("ordered", "📦 Заказано"),
    ("delivered", "🚚 Доставлено"),
    ("installed", "✅ Установлено"),
]


def add_room_object(room_id, name, obj_type=None, catalog_item_id=None,
                    length=None, width=None, height=None,
                    wall=None, offset_x=None, offset_y=None,
                    needs_water=0, needs_sewer=0, needs_power=0,
                    power_kw=None, status="planned", note=None,
                    tenant_id=1, created_by=None):
    """Добавляет мебель/технику. Возвращает object_id."""
    return commit(
        "INSERT INTO room_objects "
        "(room_id, name, obj_type, catalog_item_id, length, width, height, "
        "wall, offset_x, offset_y, needs_water, needs_sewer, needs_power, "
        "power_kw, status, note, tenant_id, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (room_id, name, obj_type, catalog_item_id, length, width, height,
         wall, offset_x, offset_y, needs_water, needs_sewer, needs_power,
         power_kw, status, note, tenant_id, created_by)
    )


def get_room_object(obj_id):
    row = fetchone("SELECT * FROM room_objects WHERE id = ?", (obj_id,))
    return dict(row) if row else None


def get_room_objects(room_id, obj_type=None):
    """Все объекты комнаты (опц. фильтр по типу)."""
    if obj_type:
        rows = fetchall(
            "SELECT * FROM room_objects WHERE room_id = ? AND obj_type = ? ORDER BY id",
            (room_id, obj_type)
        )
    else:
        rows = fetchall(
            "SELECT * FROM room_objects WHERE room_id = ? ORDER BY obj_type, id",
            (room_id,)
        )
    return [dict(r) for r in rows]


def update_room_object(obj_id, **kwargs):
    """Обновляет поля."""
    allowed = {"name", "obj_type", "catalog_item_id", "length", "width",
               "height", "wall", "offset_x", "offset_y", "needs_water",
               "needs_sewer", "needs_power", "power_kw", "status", "note"}
    fields, params = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            params.append(v)
    if not fields:
        return False
    params.append(obj_id)
    commit(f"UPDATE room_objects SET {', '.join(fields)} WHERE id = ?", params)
    return True


def delete_room_object(obj_id):
    commit("DELETE FROM room_objects WHERE id = ?", (obj_id,))
    return True


def get_obj_type_label(obj_type):
    """Метка типа."""
    for code, label in OBJ_TYPES:
        if code == obj_type:
            return label
    return obj_type or "📦 Прочее"


def get_status_label(status):
    """Метка статуса."""
    for code, label in STATUSES:
        if code == status:
            return label
    return status or "—"


def format_room_object(o):
    """Форматирует объект в строку."""
    label = get_obj_type_label(o.get('obj_type'))
    status = get_status_label(o.get('status'))
    parts = []
    if o.get('length') and o.get('width') and o.get('height'):
        parts.append(f"{o['length']}×{o['width']}×{o['height']}м")
    if o.get('wall'):
        parts.append(f"стена {o['wall']}")
    if o.get('power_kw'):
        parts.append(f"{o['power_kw']}кВт")
    dims = ' · '.join(parts)
    return f"{label} {o.get('name')} [{status}]{' — ' + dims if dims else ''}"


def get_requirements(obj_id):
    """Требования объекта: вода, слив, свет."""
    o = get_room_object(obj_id)
    if not o:
        return {}
    return {
        'needs_water': bool(o.get('needs_water')),
        'needs_sewer': bool(o.get('needs_sewer')),
        'needs_power': bool(o.get('needs_power')),
        'power_kw': o.get('power_kw') or 0,
    }


def check_object_fit(obj_id):
    """Проверяет, влезает ли объект в комнату по размерам.
    Возвращает список проблем."""
    from core.measures import get_measures
    from core.rooms import get_room

    o = get_room_object(obj_id)
    if not o:
        return [{'level': 'error', 'msg': 'Объект не найден'}]

    room = get_room(o['room_id'])
    if not room:
        return [{'level': 'error', 'msg': 'Комната не найдена'}]

    issues = []
    measures = get_measures(o['room_id'], category='wall')

    if o.get('height') and room.get('height'):
        if o['height'] > room['height']:
            issues.append({
                'level': 'critical',
                'msg': f"Высота объекта {o['height']}м > высоты комнаты {room['height']}м"
            })

    if o.get('wall') and o.get('length'):
        wall_m = next((m for m in measures if m.get('label', '').endswith(o['wall'])), None)
        if wall_m:
            wall_len = wall_m.get('length') or 0
            offset = o.get('offset_x') or 0
            if offset + o['length'] > wall_len:
                issues.append({
                    'level': 'critical',
                    'msg': f"Объект не влезает: {offset}+{o['length']} > {wall_len}м"
                })

    return issues
