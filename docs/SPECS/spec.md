# SPECS/spec.md — Модуль-справочник

> Спецификация модуля `core/spec.py`

---

## 1. НАЗНАЧЕНИЕ

Единый источник правды для текстов, картинок, типов, валидаций. Никаких магических строк в коде.

---

## 2. СТРУКТУРА

### HEIGHT_STEPS
Тексты шагов высоты.
Ключи: 1, 2, 3 (номер точки).
Значения: dict с title, subtitle, hint, example, image.

### WALL_STEPS
Тексты шагов обхода стены.
Ключи: flags, plane, length, openings, angle.
Значения: dict с title (шаблон), subtitle, flags (для flags), image_tpl.

### NICHE_STEPS
Тексты шагов ниши.
Ключи: count, width, depth, height, plane.

### SESSION_TYPES
Типы сессий замеров:
initial, after_rough, furniture, tiling, mirror, electric, plumbing, final, custom.

### WORK_STAGES
Этапы ремонта:
demolition, rough, comms, plaster, screed, finish, finish_work, handover.

### WORK_TYPES
Виды работ (165+). Импорт из data/works.json.

### MATERIALS
Материалы стен:
brick, concrete, aerated, drywall, wood, plaster, other.

### OBJECT_TYPES
Типы объектов:
bare_walls, ready_repair, cosmetic, frequent_works, designer, commercial.

### OPENING_TYPES
Типы проёмов:
window, door_interior, door_entrance, vent, arch.

### COMM_TYPES
19 типов коммуникаций (импорт из data/comm_types.json).

### VALIDATIONS
Все валидации:
- height: 50-1000
- length: 10-5000
- niche_width/depth/height: 1-2000
- angle: 1-179
- diameter: 5-500
- voltage: 220/380
- size: 1-1000

---

## 3. ФУНКЦИИ

### get_step_spec(step_name)
Возвращает всё для шага: title, subtitle, hint, image, validation.

### get_image_path(step_name, **kwargs)
Возвращает путь к картинке.
Шаблоны: wall_scheme_s{n}_{phase}.png

### get_wall_names()
Возвращает {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}.

### get_session_types()
### get_materials()
### get_object_types()

---

## 4. ПРАВИЛА

1. Все тексты — здесь. Не в коде.
2. Все картинки — здесь. Не в коде.
3. Все валидации — здесь. Не в коде.
4. Один источник — один файл.
5. Обновление — здесь. Все интерфейсы сразу видят.

---

*Конец SPECS/spec.md*
