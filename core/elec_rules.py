"""core.elec_rules — правила автокомплектации ЭОМ.

Все параметры можно переопределить для конкретного объекта
через system_settings с ключом 'elec_rules_<object_id>'.
"""
import json
from core.db import fetchone, commit


# ============================================================
# ДЕФОЛТНЫЕ ПРАВИЛА
# ============================================================

DEFAULT_RULES = {
    # Расчёты
    'cos_phi': 0.9,
    'safety_factor': 1.2,
    'simultaneity_factor': 0.8,
    'selectivity_factor': 1.6,
    'reserve_modules': 2,

    # Минимальные номиналы по назначению группы
    'min_rating_by_purpose': {
        'socket': 16,
        'light': 6,
        'kitchen': 16,
        'power': 16,
        'vent': 6,
        'cold': 16,
        'heat': 16,
        'emergency': 6,
        'other': 10,
    },

    # Максимум для 1-фазного автомата
    'max_breaker_1p': 63,

    # УЗО
    'uzo_sockets': True,
    'uzo_lighting': False,
    'uzo_bathroom': True,
    'uzo_kitchen': True,
    'uzo_outdoor': True,
    'rcd_sockets_ma': 30,
    'rcd_input_ma': 100,
    'prefer_dif': False,

    # Кабели
    'min_breaker_rating': 6,
    'max_breaker_rating': 100,
    'default_curve': 'C',

    # Модели (для спецификации)
    'auto_model': 'ВА47-29',
    'uzo_model': 'ВД1-63',
    'dif_model': 'АВДТ32',
    'counter_model': 'Меркурий 201',
    'switch_model': 'Рубильник Р32',
}


# ============================================================
# ЧТЕНИЕ / ПЕРЕОПРЕДЕЛЕНИЕ
# ============================================================

def get_rules(object_id=None):
    """Возвращает правила (дефолт + переопределения для объекта)."""
    rules = dict(DEFAULT_RULES)
    if object_id:
        override = _load_override(object_id)
        if override:
            rules.update(override)
    return rules


def set_rule(object_id, key, value):
    """Переопределяет правило для объекта."""
    if key not in DEFAULT_RULES:
        return False
    current = _load_override(object_id) or {}
    current[key] = value
    return _save_override(object_id, current)


def reset_rules(object_id):
    """Сбрасывает переопределения для объекта."""
    try:
        commit("DELETE FROM system_settings WHERE key = ?", (_key(object_id),))
        return True
    except Exception as e:
        print("reset_rules: " + str(e), flush=True)
        return False


def list_overrides(object_id):
    """Возвращает только переопределения (не дефолт)."""
    return _load_override(object_id) or {}


# ============================================================
# ВНУТРЕННИЕ
# ============================================================

def _key(object_id):
    return 'elec_rules_' + str(object_id)


def _load_override(object_id):
    try:
        row = fetchone("SELECT value FROM system_settings WHERE key = ?", (_key(object_id),))
        if row and row['value']:
            return json.loads(row['value'])
    except Exception as e:
        print("load_override: " + str(e), flush=True)
    return None


def _save_override(object_id, data):
    try:
        val = json.dumps(data, ensure_ascii=False)
        existing = fetchone("SELECT key FROM system_settings WHERE key = ?", (_key(object_id),))
        if existing:
            commit("UPDATE system_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
                   (val, _key(object_id)))
        else:
            commit("INSERT INTO system_settings (key, value) VALUES (?, ?)",
                   (_key(object_id), val))
        return True
    except Exception as e:
        print("save_override: " + str(e), flush=True)
        return False


def format_rules(object_id=None):
    """Текстовое представление правил (дефолт + overrides)."""
    rules = get_rules(object_id)
    overrides = list_overrides(object_id) if object_id else {}
    lines = ["Правила ЭОМ:"]
    for k in sorted(rules.keys()):
        v = rules[k]
        mark = " [изменено]" if k in overrides else ""
        lines.append("  " + k + " = " + str(v) + mark)
    return chr(10).join(lines)
