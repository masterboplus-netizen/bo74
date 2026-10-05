"""core.spec — справочник. Единый источник текстов, картинок, типов, валидаций.

Никаких магических строк в коде. Всё берётся отсюда.

Расширенная версия: квартиры, дома, бани, балконы, фасады, подсветка, конструкции.

Версия: 8.1
"""
import os

# ============================================================
# ПУТИ
# ============================================================

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(_BASE, "docs", "images")


def get_image_path(filename):
    return os.path.join(IMAGES_DIR, filename)


# ============================================================
# ТИПЫ ОБЪЕКТОВ (расширенные)
# ============================================================

OBJECT_TYPES = {
    # Жилые
    "apartment": "🏢 Квартира",
    "private_house": "🏠 Частный дом",
    "townhouse": "🏘 Таунхаус",
    "dacha": "🌳 Дача",
    "cottage": "🏡 Коттедж",

    # Коммерческие
    "office": "🏢 Офис",
    "cafe": "☕ Кафе / ресторан",
    "shop": "🛍 Магазин",
    "warehouse": "📦 Склад",
    "industrial": "🏭 Промышленный",

    # Специальные
    "balcony": "🪟 Балкон / лоджия",
    "terrace": "🌤 Терраса / веранда",
    "bathhouse": "🧖 Баня / сауна",
    "garage": "🚗 Гараж",
    "landscape": "🌿 Ландшафт",
    "facade": "🏛 Фасад",
}


# ============================================================
# ТИПЫ КОМНАТ (расширенные)
# ============================================================

ROOM_TYPES = {
    # Жилые
    "living": "🛋 Гостиная",
    "bedroom": "🛏 Спальня",
    "kitchen": "🍳 Кухня",
    "kids": "🧸 Детская",
    "office_room": "💼 Кабинет",
    "dining": "🍽 Столовая",

    # Мокрые
    "bathroom": "🚿 Ванная",
    "toilet": "🚽 Санузел",
    "shower": "🚿 Душевая",
    "utility": "🧺 Постирочная",
    "boiler": "🔥 Котельная",
    "pool": "🏊 Бассейн",

    # Баня
    "steam_room": "♨️ Парная",
    "sauna": "🧖 Сауна",
    "washroom": "💧 Помывочная",
    "rest_room": "🛋 Комната отдыха",

    # Проходные
    "hallway": "🚪 Коридор",
    "hall": "🏛 Зал",
    "corridor": "🚪 Коридор",
    "staircase": "🪜 Лестница",

    # Балконы / террасы
    "balcony": "🪟 Балкон",
    "loggia": "🪟 Лоджия",
    "terrace": "🌤 Терраса",
    "veranda": "🌤 Веранда",

    # Хранение
    "dressing": "👗 Гардеробная",
    "storage": "📦 Кладовая",
    "basement": "🏚 Подвал",
    "attic": "🏠 Мансарда / чердак",
    "garage_room": "🚗 Гараж",

    # Технические
    "technical": "⚙️ Техническое",
    "elevator": "🛗 Лифт",

    # Фасад
    "facade": "🏛 Фасад",
    "roof": "🏠 Крыша",
}


# ============================================================
# ТИПЫ СЕССИЙ ЗАМЕРОВ
# ============================================================

SESSION_TYPES = {
    "initial": "Первичный (черновой)",
    "after_rough": "После черновой",
    "furniture": "Под мебель",
    "tiling": "Под плитку",
    "mirror": "Под зеркала",
    "electric": "Под электрику",
    "plumbing": "Под сантехнику",
    "lighting": "Под подсветку",
    "facade": "Под фасад",
    "roof": "Под кровлю",
    "final": "Финальный",
    "custom": "Свой",
}


# ============================================================
# ЭТАПЫ РЕМОНТА
# ============================================================

WORK_STAGES = {
    # Общие
    "demolition": ("Демонтаж", 2),
    "rough": ("Черновая", 7),
    "comms": ("Коммуникации", 5),
    "plaster": ("Штукатурка", 5),
    "screed": ("Стяжка", 3),
    "finish": ("Чистовая", 15),
    "finish_work": ("Финишная", 7),
    "handover": ("Сдача", 2),

    # Фасад
    "facade_prep": ("Подготовка фасада", 3),
    "facade_insulate": ("Утепление фасада", 5),
    "facade_finish": ("Отделка фасада", 7),
    "facade_lighting": ("Подсветка фасада", 3),

    # Крыша
    "roof_demo": ("Демонтаж кровли", 2),
    "roof_rafters": ("Стропильная система", 5),
    "roof_cover": ("Кровельное покрытие", 5),
    "roof_drain": ("Водоотведение", 2),

    # Баня
    "bath_insulate": ("Утепление бани", 3),
    "bath_waterproof": ("Гидроизоляция", 2),
    "bath_wood": ("Деревянная отделка", 5),
    "bath_stove": ("Монтаж печи", 2),
    "bath_vent": ("Вентиляция", 2),

    # Ландшафт
    "land_prep": ("Подготовка участка", 3),
    "land_drain": ("Дренаж", 3),
    "land_finish": ("Отделка", 5),
    "land_lighting": ("Ландшафтная подсветка", 3),
}


# ============================================================
# МАТЕРИАЛЫ СТЕН
# ============================================================

MATERIALS = {
    "brick": "Кирпич",
    "concrete": "Бетон",
    "aerated": "Газобетон",
    "drywall": "Гипсокартон",
    "wood": "Дерево",
    "plaster": "Штукатурка",
    "ceramic": "Керамика",
    "stone": "Камень",
    "metal": "Металл",
    "glass": "Стекло",
    "other": "Прочее",
}


# ============================================================
# ТИПЫ ПРОЁМОВ
# ============================================================

OPENING_TYPES = {
    "window": "🪟 Окно",
    "door_interior": "🚪 Дверь межкомнатная",
    "door_entrance": "🚪 Дверь входная",
    "door_glass": "🚪 Стеклянная дверь",
    "vent": "💨 Вентиляция",
    "arch": "🏛 Арка",
    "portal": "🚪 Портал",
    "skylight": "☀️ Световое окно",
    "garage_door": "🚗 Ворота гаражные",
    "gate": "🚧 Ворота",
}


# ============================================================
# НАЗВАНИЯ СТЕН
# ============================================================

WALL_NAMES = {
    1: "напротив",
    2: "слева",
    3: "у входа",
    4: "справа",
}


# ============================================================
# ШАГИ ВЫСОТЫ
# ============================================================

HEIGHT_STEPS = {
    1: {
        "title": "📏 *Высота — шаг 1*",
        "subtitle": "📍 *Точка 1 — ЦЕНТР комнаты*",
        "hint": "Встань в центре комнаты, приложи дальномер к полу, наведи на потолок.",
        "prompt": "Введи результат в СМ:",
        "example": "305",
        "image": "height_scheme_step1.png",
    },
    2: {
        "title": "📏 *Высота — шаг 2*",
        "subtitle": "📍 *Точка 2 — у ЛЕВОГО угла*",
        "hint": "",
        "prompt": "Введи результат в СМ:",
        "example": "304",
        "image": "height_scheme_step2.png",
    },
    3: {
        "title": "📏 *Высота — шаг 3*",
        "subtitle": "📍 *Точка 3 — у ПРАВОГО угла*",
        "hint": "",
        "prompt": "Введи результат в СМ:",
        "example": "306",
        "image": "height_scheme_step3.png",
    },
}


# ============================================================
# ШАГИ ОБХОДА СТЕНЫ
# ============================================================

WALL_FLAGS = [
    ("niche", "С нишей"),
    ("rounded", "С закруглением"),
    ("wavy", "Разная по высоте"),
    ("hidden", "Скрытые коммуникации"),
]

WALL_STEPS = {
    "flags": {
        "title": "🧱 *Стена {n} — {pos}*",
        "subtitle": "👁 Осмотри стену.\nОтметь особенности:",
        "image_tpl": "wall_scheme_s{n}_flags.png",
    },
    "plane": {
        "title": "🧱 *Стена {n}*",
        "subtitle": "📐 *Плоскость стены:*\n\nСтена ровная или кривая по высоте?",
        "hint": "_Если стена «горбатая» — нужно замерить в 3 точках._",
        "image_tpl": "wall_scheme_s{n}_plane.png",
    },
    "length": {
        "title": "🧱 *Стена {n} — {pos}*",
        "subtitle": "📏 *Длина стены* (СМ):",
        "hint": "⚠️ *ВАЖНО:* дальномер в режиме «от ЗАДНЕЙ СТЕНКИ».",
        "prompt": "Напиши число и отправь.",
        "image_tpl": "wall_scheme_s{n}_length.png",
    },
    "openings": {
        "title": "🧱 *Стена {n} — {pos}*",
        "subtitle": "🚪 *Есть ли на этой стене проёмы?*",
        "image_tpl": None,
    },
    "angle": {
        "title": "✅ Длина: *{length} см*",
        "subtitle": "📐 *Угол между этой стеной и следующей:*",
        "hint": "Обычно 90° — прямой угол.",
        "image_tpl": "wall_scheme_s{n}_angle.png",
    },
}


# ============================================================
# ШАГИ НИШИ
# ============================================================

NICHE_STEPS = {
    "count": {"title": "🕳 *Сколько нишей на этой стене?*"},
    "width": {
        "title": "🕳 *Ниша {i} из {count}*",
        "subtitle": "📏 *Ширина ниши* (СМ):",
        "example": "80",
        "image": "niche_width.png",
    },
    "depth": {
        "title": "🕳 *Ниша — ГЛУБИНА* (СМ):",
        "hint": "_Сколько вглубь стены. Например: 40_",
        "image": "niche_depth.png",
    },
    "height": {
        "title": "🕳 *Ниша — ВЫСОТА* (СМ):",
        "example": "200",
        "image": "niche_height.png",
    },
    "plane": {
        "title": "🕳 *Ниша ровная или неровная по высоте?*",
        "hint": "Если верх шире низа — неровная.",
    },
    "top_width": {"title": "🕳 *Ширина СВЕРХУ* (СМ):"},
    "top_depth": {"title": "🕳 *Глубина сверху* (СМ):"},
}


# ============================================================
# ТИПЫ ОСВЕЩЕНИЯ (архитектурная подсветка)
# ============================================================

LIGHTING_TYPES = {
    "facade_spot": "🔦 Прожектор фасадный",
    "facade_linear": "📏 Линейная подсветка фасада",
    "facade_contour": "🔲 Контурная подсветка",
    "facade_wall": "🏛 Wall washer",
    "land_path": "🌟 Подсветка дорожек",
    "land_lawn": "🌿 Подсветка газонов",
    "land_tree": "🌳 Подсветка деревьев",
    "land_water": "💧 Подсветка воды",
    "interior_cove": "💡 Карнизная подсветка",
    "interior_niche": "💡 Подсветка ниши",
    "interior_picture": "🖼 Подсветка картин",
    "interior_stair": "🪜 Подсветка лестницы",
    "interior_floor": "🌟 Напольная подсветка",
}

LIGHTING_TEMPERATURES = {
    "warm": "🔥 Тёплый (2700-3000K)",
    "neutral": "⚪ Нейтральный (4000K)",
    "cold": "❄️ Холодный (6000-6500K)",
    "rgb": "🌈 RGB",
    "tunable": "🎨 Tunable White",
}

LIGHTING_PROTECTION = {
    "ip20": "IP20 (внутри)",
    "ip44": "IP44 (влагостойкий)",
    "ip65": "IP65 (для улицы)",
    "ip67": "IP67 (погружной)",
    "ip68": "IP68 (под водой)",
}

LIGHTING_CONTROL = {
    "switch": "Обычный выключатель",
    "dimmer": "Диммер",
    "smart": "Smart Home",
    "dmx": "DMX",
    "sensor": "Датчик движения",
    "timer": "Таймер",
    "astronomic": "Астрономический таймер",
}


# ============================================================
# ТИПЫ КОНСТРУКЦИЙ
# ============================================================

CONSTRUCTION_TYPES = {
    "load_bearing_wall": "🧱 Несущая стена",
    "partition": "🚪 Перегородка",
    "column": "🏛 Колонна",
    "beam": "📏 Балка",
    "slab": "🛏 Перекрытие",
    "arch": "🏛 Арка",
    "niche_decor": "🕳 Декоративная ниша",
    "cornice": "🏛 Карниз",
    "pilaster": "🏛 Пилястра",
    "riser": "⬆️ Стояк",
}

CONSTRUCTION_MATERIALS = {
    "concrete": "Бетон",
    "brick": "Кирпич",
    "metal": "Металл",
    "wood": "Дерево",
    "gypsum": "Гипс",
    "stone": "Камень",
    "glass": "Стекло",
    "composite": "Композит",
}


# ============================================================
# ТИПЫ КРЫШ
# ============================================================

ROOF_TYPES = {
    "flat": "Плоская",
    "gable": "Двускатная",
    "hip": "Вальмовая",
    "half_hip": "Полувальмовая",
    "mansard": "Мансардная",
    "multi": "Многоскатная",
    "shed": "Односкатная",
    "dome": "Купол",
    "conical": "Коническая",
}

ROOF_COVERINGS = {
    "metal_tile": "Металлочерепица",
    "flexible_tile": "Гибкая черепица",
    "ceramic_tile": "Керамическая черепица",
    "cement_tile": "Цементная черепица",
    "seam": "Фальцевая кровля",
    "corrugated": "Профнастил",
    "slate": "Сланец",
    "copper": "Медь",
    "zinc": "Цинк",
    "thatch": "Солома",
    "membrane": "Мембрана",
}


# ============================================================
# ВАЛИДАЦИИ
# ============================================================

VALIDATIONS = {
    "height": (50, 3000),
    "length": (10, 50000),
    "niche_width": (1, 2000),
    "niche_depth": (1, 2000),
    "niche_height": (1, 2000),
    "angle": (1, 179),
    "diagonal": (1, 50000),
    "opening_width": (10, 5000),
    "opening_height": (10, 5000),
    "opening_sill": (0, 5000),
    "comm_offset_x": (0, 50000),
    "comm_offset_y": (0, 5000),
    "comm_diameter": (5, 500),
    "comm_size": (1, 1000),
    "balcony_railing_height": (50, 200),
    "balcony_depth": (50, 500),
    "facade_area": (1, 10000),
    "roof_area": (1, 10000),
    "lighting_power": (1, 1000),
    "lighting_count": (1, 500),
}


def validate(step_name, value):
    """Проверяет значение по шагу. Возвращает (ok, error_msg)."""
    if step_name not in VALIDATIONS:
        return True, None
    lo, hi = VALIDATIONS[step_name]
    if not isinstance(value, (int, float)):
        return False, "Нужно число"
    if value < lo or value > hi:
        return False, f"Значение должно быть от {lo} до {hi}"
    return True, None


# ============================================================
# ФУНКЦИИ
# ============================================================

def get_height_step(step):
    return HEIGHT_STEPS.get(step)


def get_wall_step(step_name, n=None, pos=None, length=None):
    """Возвращает шаблон шага стены с подстановкой доступных переменных.

    Подставляет только те placeholder'ы, которые реально есть в шаблоне:
    {n}, {pos}, {length}. Это защищает от KeyError.
    """
    spec = WALL_STEPS.get(step_name)
    if not spec:
        return None
    result = dict(spec)

    def _safe_format(text, **values):
        """Форматирует, подставляя только известные ключи, остальные оставляет как есть."""
        if not text:
            return text
        # Определяем какие placeholder'ы реально есть в тексте
        import re
        placeholders = set(re.findall(r"\{(\w+)\}", text))
        available = {k: v for k, v in values.items() if k in placeholders and v is not None}
        # Если есть placeholder без значения — оставляем его буквально (не роняем)
        try:
            return text.format(**{**{k: v for k, v in values.items() if v is not None}, **{
                p: "{" + p + "}" for p in placeholders if p not in available and values.get(p) is None
            }})
        except (KeyError, IndexError):
            return text

    if "title" in result:
        result["title"] = _safe_format(
            result["title"],
            n=n, pos=pos or "", length=length if length is not None else None
        )
    if "subtitle" in result:
        result["subtitle"] = _safe_format(
            result["subtitle"],
            n=n, pos=pos or "", length=length if length is not None else None
        )
    if "image_tpl" in result and result["image_tpl"] and n is not None:
        result["image"] = result["image_tpl"].format(n=n)
    return result


def get_niche_step(step_name, i=None, count=None):
    spec = NICHE_STEPS.get(step_name)
    if not spec:
        return None
    result = dict(spec)
    if i is not None and count is not None and "title" in result:
        result["title"] = result["title"].format(i=i, count=count)
    return result


def get_wall_name(n):
    return WALL_NAMES.get(n, "?")


def get_session_label(code):
    return SESSION_TYPES.get(code, code)


def get_material_label(code):
    return MATERIALS.get(code, code)


def get_object_type_label(code):
    return OBJECT_TYPES.get(code, code)


def get_room_type_label(code):
    return ROOM_TYPES.get(code, code)


def get_opening_label(code):
    return OPENING_TYPES.get(code, code)


def get_lighting_label(code):
    return LIGHTING_TYPES.get(code, code)


def get_construction_label(code):
    return CONSTRUCTION_TYPES.get(code, code)


def get_roof_label(code):
    return ROOF_TYPES.get(code, code)


def get_stage_label(code):
    s = WORK_STAGES.get(code)
    return s[0] if s else code


def get_stage_days(code):
    s = WORK_STAGES.get(code)
    return s[1] if s else 0


# ============================================================
# СПИСКИ ДЛЯ UI
# ============================================================

def list_object_types():
    return [(k, v) for k, v in OBJECT_TYPES.items()]


def list_room_types():
    return [(k, v) for k, v in ROOM_TYPES.items()]


def list_session_types():
    return [(k, v) for k, v in SESSION_TYPES.items()]


def list_materials():
    return [(k, v) for k, v in MATERIALS.items()]


def list_opening_types():
    return [(k, v) for k, v in OPENING_TYPES.items()]


def list_lighting_types():
    return [(k, v) for k, v in LIGHTING_TYPES.items()]


def list_construction_types():
    return [(k, v) for k, v in CONSTRUCTION_TYPES.items()]


def list_roof_types():
    return [(k, v) for k, v in ROOF_TYPES.items()]


def list_roof_coverings():
    return [(k, v) for k, v in ROOF_COVERINGS.items()]

# ============================================================
# ЭЛЕКТРИКА (ЭОМ)
# ============================================================

# Назначение групп
PURPOSE_TYPES = {
    "light":     "💡 Освещение",
    "socket":    "🔌 Розеточная группа",
    "power":     "⚡ Силовая группа (380В)",
    "vent":      "💨 Вентиляция",
    "cold":      "❄️ Холод",
    "heat":      "🔥 Отопление",
    "kitchen":   "🍳 Кухонное оборудование",
    "emergency": "🚨 Аварийная линия",
    "other":     "📦 Прочее",
}

# Кривые автоматов
BREAKER_CURVES = {
    "B": "B (освещение, 3-5 × In)",
    "C": "C (розетки, 5-10 × In)",
    "D": "D (моторы, 10-20 × In)",
}

# Номиналы автоматов (А)
BREAKER_RATINGS = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100]

# Типы кабелей
CABLE_TYPES = {
    "3x1.5":  "ВВГнг-LS 3×1.5 (1ф, свет, до 16А)",
    "3x2.5":  "ВВГнг-LS 3×2.5 (1ф, розетки, до 25А)",
    "3x4":    "ВВГнг-LS 3×4 (1ф, до 32А)",
    "3x6":    "ВВГнг-LS 3×6 (1ф, до 40А)",
    "5x1.5":  "ВВГнг-LS 5×1.5 (3ф, свет)",
    "5x2.5":  "ВВГнг-LS 5×2.5 (3ф, до 25А)",
    "5x4":    "ВВГнг-LS 5×4 (3ф, до 32А)",
    "5x6":    "ВВГнг-LS 5×6 (3ф, до 40А)",
    "5x10":   "ВВГнг-LS 5×10 (3ф, до 63А)",
}

# Способы прокладки
ROUTE_TYPES = {
    "штроба":       "Штроба в стене",
    "гофра":        "Гофра по потолку",
    "кабель-канал": "Кабель-канал",
    "лоток":        "Кабельный лоток",
    "стяжка":       "В стяжке пола",
    "открыто":      "Открыто по стене",
}

# Степени защиты (IP)
IP_CLASSES = {
    "ip20": "IP20 (сухие)",
    "ip44": "IP44 (влажные, кухни)",
    "ip54": "IP54 (мокрые)",
    "ip65": "IP65 (улица)",
    "ip68": "IP68 (под водой)",
}

# Фазы
PHASE_TYPES = {
    1: "1-фазный (220В)",
    3: "3-фазный (380В)",
}

# Спецоборудование для кафе/ресторанов (мощность типичная, Вт)
KITCHEN_EQUIPMENT = {
    "плита_4_конф":      ("🍳 Плита 4-конфорочная",  8000, 3),
    "плита_6_конф":      ("🍳 Плита 6-конфорочная",  12000, 3),
    "пароконвектомат":   ("♨️ Пароконвектомат",       9000, 3),
    "жарочный_шкаф":     ("🔥 Жарочный шкаф",         6000, 3),
    "фритюрница":        ("🍟 Фритюрница",            5000, 3),
    "посудомоечная":     ("🍽 Посудомоечная машина",  4500, 1),
    "холодильник":       ("🧊 Холодильник",           500, 1),
    "холод_камера":      ("❄️ Холодильная камера",    2000, 1),
    "морозильник":       ("🧊 Морозильник",           800, 1),
    "вытяжка":           ("💨 Вытяжка",               1500, 1),
    "кондиционер":       ("❄️ Кондиционер",           2500, 1),
    "микроволновка":     ("📻 Микроволновка",         1500, 1),
    "кофемашина":        ("☕ Кофемашина",            3000, 1),
    "бойлер":            ("💧 Бойлер",                3000, 1),
    "тестомес":          ("🥖 Тестомес",               1000, 1),
}

# Силовые розетки (3-фазные)
POWER_SOCKETS = {
    "cee16": "🔌 CEE 16A (380В, 3P+N+E)",
    "cee32": "🔌 CEE 32A (380В, 3P+N+E)",
    "cee63": "🔌 CEE 63A (380В, 3P+N+E)",
}


def get_purpose_label(code):
    return PURPOSE_TYPES.get(code, code)


def get_cable_label(code):
    return CABLE_TYPES.get(code, code)


def get_route_label(code):
    return ROUTE_TYPES.get(code, code)


def get_ip_label(code):
    return IP_CLASSES.get(code, code)


def get_phase_label(code):
    return PHASE_TYPES.get(code, f"{code}-фазный")


def pick_cable_by_current(current_a, phase=1):
    """Подбирает тип кабеля по току и числу фаз.
    
    Для 1-фазного: 16А → 3x1.5, 25А → 3x2.5, 32А → 3x4, 40А → 3x6
    Для 3-фазного: 16А → 5x1.5, 25А → 5x2.5, 32А → 5x4, 40А → 5x6
    """
    if phase == 3:
        table = [(16, "5x1.5"), (25, "5x2.5"), (32, "5x4"), (40, "5x6"), (999, "5x10")]
    else:
        table = [(16, "3x1.5"), (25, "3x2.5"), (32, "3x4"), (40, "3x6"), (999, "3x6")]
    for limit, code in table:
        if current_a <= limit:
            return code
    return table[-1][1]


def pick_breaker_by_current(current_a):
    """Подбирает номинал автомата по току (следующий стандартный)."""
    for rating in BREAKER_RATINGS:
        if rating >= current_a:
            return rating
    return BREAKER_RATINGS[-1]



# ============================================================
# ЦЕНЫ КОМПОНЕНТОВ (дефолтные, для смет)
# ============================================================

COMPONENT_PRICES_DEFAULT = {
    # Автоматы модульные (EKF ВА47-29, IEK)
    'auto_1p': 250,
    'auto_2p': 450,
    'auto_3p': 700,
    'auto_4p': 900,
    # УЗО (ВД1-63)
    'uzo_2p': 1500,
    'uzo_4p': 3500,
    # Дифавтоматы (АВДТ32)
    'dif_2p': 2500,
    'dif_4p': 4500,
    # Рубильники
    'switch_2p': 500,
    'switch_4p': 1200,
    # Счётчики
    'counter_1p': 2500,
    'counter_3p': 5000,
    # Шины
    'busbar_n': 150,
    'busbar_pe': 150,
    # Клеммы
    'clamp': 20,
}


def get_default_price(component_type, poles=None):
    """Возвращает дефолтную цену по типу компонента.

    Логика:
    1. component_type + '_' + poles + 'p' (например auto_1p)
    2. component_type
    3. Первый ключ с префиксом component_type + '_' (fallback)
    """
    key = component_type
    if poles:
        key = component_type + '_' + str(poles) + 'p'
    if key in COMPONENT_PRICES_DEFAULT:
        return COMPONENT_PRICES_DEFAULT[key]
    if component_type in COMPONENT_PRICES_DEFAULT:
        return COMPONENT_PRICES_DEFAULT[component_type]
    # Fallback: ищем по префиксу
    prefix = str(component_type) + '_'
    for k, v in COMPONENT_PRICES_DEFAULT.items():
        if k.startswith(prefix):
            return v
    # Дополнительные алиасы
    aliases = {
        'auto': 250,
        'uzo': 1500,
        'dif': 2500,
        'switch': 500,
        'counter': 3000,
        'busbar': 150,
        'clamp': 20,
        'input': 250,
    }
    if component_type in aliases:
        return aliases[component_type]
    return 0


# ============================================================
# ЦЕНЫ КАБЕЛЯ (₽/м)
# ============================================================

CABLE_PRICES_DEFAULT = {
    '3x1.5':  80,
    '3x2.5':  120,
    '3x4':    180,
    '3x6':    250,
    '5x1.5':  130,
    '5x2.5':  180,
    '5x4':    280,
    '5x6':    380,
    '5x10':   550,
}


def get_cable_price(cable_type):
    """Возвращает цену кабеля за метр по типу."""
    if not cable_type:
        return 0
    return CABLE_PRICES_DEFAULT.get(cable_type, 0)


# ============================================================
# ЦЕНЫ РАСХОДНИКОВ (₽/м — для прокладки)
# ============================================================

CONSUMABLE_PRICES_DEFAULT = {
    'gofra':    30,     # гофра
    'shtroba':  200,    # штробление
    'lotok':    150,    # кабельный лоток
    'styazhka': 100,    # прокладка в стяжке
    'otkryto':  50,     # открытая прокладка
    'klipsa':   15,     # клипсы
}


def get_consumable_price(route_type):
    """Возвращает цену расходника за метр по типу прокладки."""
    if not route_type:
        return 0
    return CONSUMABLE_PRICES_DEFAULT.get(route_type, 0)


# ============================================================
# ВИДЫ РАБОТ (дефолтные, для смет)
# ============================================================

WORK_TYPES_DEFAULT = {
    # Электромонтаж
    'elec_shtroba':      ('Штробление под кабель', 'м', 200),
    'elec_cable':        ('Прокладка кабеля', 'м', 80),
    'elec_socket':       ('Установка розетки', 'шт', 350),
    'elec_switch':       ('Установка выключателя', 'шт', 300),
    'elec_light':        ('Установка светильника', 'шт', 500),
    'elec_panel_mount':  ('Монтаж щита', 'шт', 3500),
    'elec_breaker_mount':('Монтаж автомата', 'шт', 300),
    # Сантехника
    'plumb_shtroba':     ('Штробление под трубу', 'м', 250),
    'plumb_pipe':        ('Прокладка трубы', 'м', 150),
    'plumb_socket':      ('Установка смесителя', 'шт', 500),
    'plumb_toilet':      ('Установка унитаза', 'шт', 1500),
    'plumb_sink':        ('Установка раковины', 'шт', 800),
    'plumb_bath':        ('Установка ванны', 'шт', 2500),
    'plumb_shower':      ('Установка душевой кабины', 'шт', 2000),
    'plumb_radiator':    ('Установка радиатора', 'шт', 1500),
    'plumb_boiler':      ('Монтаж бойлера', 'шт', 2500),
}


def get_work_label(code):
    if code in WORK_TYPES_DEFAULT:
        return WORK_TYPES_DEFAULT[code][0]
    return code


def get_work_unit(code):
    if code in WORK_TYPES_DEFAULT:
        return WORK_TYPES_DEFAULT[code][1]
    return 'шт'


def get_work_price(code):
    if code in WORK_TYPES_DEFAULT:
        return WORK_TYPES_DEFAULT[code][2]
    return 0
