"""core.conflicts — проверка конфликтов в комнате.

Проверяет пересечения мебели с коммуникациями,
требования техники (вода/слив/свет),
габариты относительно размеров.
"""
from core.rooms import get_room
from core.measures import get_measures
from core.comms import get_comms
from core.room_objects import get_room_objects


def _interval_overlap(a_start, a_len, b_start, b_len):
    """Проверяет пересечение двух отрезков [a_start, a_start+a_len] и [b_start, b_start+b_len]."""
    if a_start is None or b_start is None:
        return False
    a_end = a_start + (a_len or 0)
    b_end = b_start + (b_len or 0)
    return not (a_end <= b_start or b_end <= a_start)


# Коммуникации, которые "прячутся" за мебелью — не считаем конфликтом
_IGNORE_TYPES = ('electric', 'weak')

def check_object_vs_comms(obj, comms):
    """Мебель ↔ коммуникации: пересечение на одной стене.
    Розетки и слаботочка НЕ считаются конфликтом (их прячут за мебелью).
    Проверяем реальные пересечения с трубами/газом/сливом.
    """
    issues = []
    if not obj.get('wall') or obj.get('offset_x') is None:
        return issues
    obj_len = obj.get('length') or 0.001
    obj_h = obj.get('height') or 0
    obj_y0 = obj.get('offset_y') or 0
    obj_y1 = obj_y0 + obj_h
    for c in comms:
        if c.get('wall') != obj['wall']:
            continue
        if c.get('comm_type') in _IGNORE_TYPES:
            continue  # розетки/слаботочка — прячут за мебелью
        if c.get('offset_x') is None:
            continue
        if not _interval_overlap(obj.get('offset_x'), obj_len, c.get('offset_x'), 0.05):
            continue
        # Проверяем Y (высоту): пересекается ли мебель с коммуникацией?
        comm_y = c.get('offset_y')
        if comm_y is not None and obj_h > 0:
            if comm_y > obj_y1 or comm_y < obj_y0:
                continue  # по высоте не пересекаются
        issues.append({
            'level': 'critical',
            'type': 'furniture_vs_comm',
            'msg': f"«{obj['name']}» перекрывает «{c.get('label') or c['comm_type']}» "
                   f"(стена {obj['wall']}, X={c.get('offset_x')}м)",
            'object_id': obj['id'],
            'comm_id': c['id'],
        })
    return issues


def check_object_power(obj, comms):
    """Техника ↔ розетки: есть ли свет рядом, хватит ли мощности."""
    issues = []
    if not obj.get('needs_power'):
        return issues
    power_kw = obj.get('power_kw') or 0
    # Ищем розетки на той же стене
    sockets = [c for c in comms
               if c.get('comm_type') == 'electric' and c.get('wall') == obj.get('wall')]
    if not sockets:
        issues.append({
            'level': 'critical',
            'type': 'no_power_nearby',
            'msg': f"«{obj['name']}» требует электричество, "
                   f"но розеток на стене {obj.get('wall') or '?'} нет",
            'object_id': obj['id'],
        })
        return issues
    if power_kw >= 3.5:
        issues.append({
            'level': 'important',
            'type': 'high_power',
            'msg': f"«{obj['name']}» — {power_kw}кВт, нужна отдельная линия 16A",
            'object_id': obj['id'],
        })
    return issues


def check_object_water_sewer(obj, comms):
    """Техника ↔ вода/слив."""
    issues = []
    has_water = any(c.get('comm_type') in ('water_cold', 'water_hot') for c in comms)
    has_sewer = any(c.get('comm_type') == 'sewer' for c in comms)
    if obj.get('needs_water') and not has_water:
        issues.append({
            'level': 'critical',
            'type': 'no_water',
            'msg': f"«{obj['name']}» требует воду, но в комнате нет ХВС/ГВС",
            'object_id': obj['id'],
        })
    if obj.get('needs_sewer') and not has_sewer:
        issues.append({
            'level': 'critical',
            'type': 'no_sewer',
            'msg': f"«{obj['name']}» требует слив, но в комнате нет канализации",
            'object_id': obj['id'],
        })
    return issues


def check_object_vs_room(obj, room, measures):
    """Мебель ↔ размеры комнаты."""
    issues = []
    if obj.get('height') and room.get('height'):
        if obj['height'] > room['height'] - 0.05:
            issues.append({
                'level': 'critical',
                'type': 'height_overflow',
                'msg': f"«{obj['name']}» ({obj['height']}м) выше потолка ({room['height']}м)",
                'object_id': obj['id'],
            })
    return issues


def check_conflicts(room_id):
    """Полная проверка конфликтов в комнате."""
    room = get_room(room_id)
    if not room:
        return [{'level': 'error', 'msg': 'Комната не найдена'}]

    measures = get_measures(room_id)
    comms = get_comms(room_id)
    objects = get_room_objects(room_id)

    issues = []
    for obj in objects:
        issues += check_object_vs_comms(obj, comms)
        issues += check_object_power(obj, comms)
        issues += check_object_water_sewer(obj, comms)
        issues += check_object_vs_room(obj, room, measures)

    return issues


def format_conflicts(issues):
    """Форматирует список конфликтов."""
    if not issues:
        return "✅ Конфликтов нет — всё чисто!"

    icons = {'critical': '🔴', 'important': '🟡', 'info': '🟢', 'error': '⚠️'}
    lines = [f"⚠️ Найдено конфликтов: {len(issues)}", ""]
    for i in issues:
        lines.append(f"{icons.get(i['level'], '•')} {i['msg']}")
    return "\n".join(lines)
