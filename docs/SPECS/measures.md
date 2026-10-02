# SPECS/measures.md — Модуль замеров

> Спецификация модуля `core/measures.py`

---

## 1. НАЗНАЧЕНИЕ

Работа с замерами комнаты: стены, пол, потолок. Ниши. Наклоны. Углы. Прогресс обхода.

---

## 2. КАТЕГОРИИ ЗАМЕРОВ

- `wall` — стена
- `floor` — пол
- `ceiling` — потолок
- `window` — окно (устар., см. openings)
- `door` — дверь (устар.)
- `opening` — проём (устар.)
- `corner` — угол
- `other` — прочее

---

## 3. ФУНКЦИИ — ЗАМЕРЫ

### add_measure(room_id, category, **kwargs)
Создаёт замер. Возвращает measure_id.

Параметры:
- label, wall_pos, order_num, material
- length, width, height, depth, angle, unit
- angle_value, angle_method
- start_x, start_y, end_x, end_y
- has_rounded, radius
- has_hidden, hidden_note
- is_wavy, measured_bottom, measured_middle, measured_top

### get_measure(measure_id)
### get_measures(room_id, category=None)
### update_measure(measure_id, **kwargs)
### delete_measure(measure_id)

---

## 4. ФУНКЦИИ — НИШИ

### add_niche(measure_id, room_id, name, offset_x, offset_y,
             width_bottom, width_top, height, depth_bottom, depth_top,
             niche_type='rect', note=None)
### get_niches(measure_id)
### get_niches_by_room(room_id)
### update_niche(niche_id, **kwargs)
### delete_niche(niche_id)
### format_niche(n)

---

## 5. ФУНКЦИИ — НАКЛОНЫ СТЕН

### add_wall_lean(measure_id, room_id, lean_angle, lean_direction, ...)
### get_wall_lean(measure_id)
### update_wall_lean(measure_id, **kwargs)
### delete_wall_lean(measure_id)

---

## 6. ФУНКЦИИ — УГЛЫ (corners)

### add_corner(room_id, corner_number, corner_type, angle_value, ...)
### get_corner(room_id, corner_number)
### get_corners(room_id)
### update_corner(corner_id, **kwargs)
### delete_corner(corner_id)
### format_corner(c)

---

## 7. ФУНКЦИИ — ПЛОЩАДИ

### calculate_room_areas(room_id, session_id=None)
Возвращает dict:
- walls_total
- walls_net (за вычетом проёмов)
- floor
- ceiling
- openings_total
- openings (list)

Логика:
1. Суммируем площади стен = length × height.
2. Суммируем площади проёмов.
3. walls_net = walls_total − openings_total.
4. Если floor не задан — 2 самые длинные стены × друг на друга.

---

## 8. ФУНКЦИИ — ПРОГРЕСС ОБХОДА

### start_walls_round(room_id)
### complete_walls_round(room_id)
### get_walls_progress(room_id)
Возвращает:
- walls_count (0–4)
- current_step (1–4)
- started_at
- completed_at

### get_walls_ordered(room_id)
Возвращает стены, отсортированные по wall_pos (напротив, слева, у входа, справа).

---

## 9. ФОРМАТИРОВАНИЕ

### format_measure(m, show_area=False)
Строка вида: 🧱 напротив: 304 см — 9.27 м²

### format_niche(n)
Строка: 🕳 Ниша 1: 60×200×40 см
Или: 🕳 Ниша 1: низ 60×40 см, верх 80×40 см, высота 200 см

---

## 10. ПРАВИЛА

1. Все размеры — в СМ.
2. Площади — в м² (делим на 10000).
3. Одна категория — один тип записи.
4. Ниши — привязаны к measure_id стены.
5. Углы — привязаны к room_id + corner_number.
6. Прогресс обхода — 4 стены, не больше.

---

*Конец SPECS/measures.md*
