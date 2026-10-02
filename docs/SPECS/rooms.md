# SPECS/rooms.md — Модуль комнат

> Спецификация модуля `interfaces/telegram/rooms.py` + `core/rooms.py`

---

## 1. НАЗНАЧЕНИЕ

Ведёт замерщика за руку при обмере комнаты. Показывает картинки, проверяет ввод, сохраняет данные, восстанавливает прогресс.

---

## 2. ФУНКЦИИ ЯДРА (core/rooms.py)

### create_room(object_id, name, room_type='rough', measure_method='laser')
Создаёт комнату. Возвращает room_id.
Проверяет: нет ли уже комнаты с таким именем в объекте.

### get_room(room_id)
Возвращает dict: id, object_id, name, room_type, height, height_bottom, height_middle, height_top, measure_method, geometry_locked_at, geometry_gap_percent, coord_origin_note.

### get_rooms(object_id)
Все комнаты объекта.

### update_room(room_id, **kwargs)
Обновляет поля. None — не трогать.

### delete_room(room_id)
Удаляет комнату + все замеры, проёмы, ниши, коммуникации, объекты.

### ensure_default_rooms(object_id)
Создаёт базовые комнаты (Ванная, Кухня, Зал, Спальня, Коридор, Балкон, Гардеробная, Гостиная, Санузел, Детская).

---

## 3. UI-ФУНКЦИИ (interfaces/telegram/rooms.py)

### show_rooms_list(update, context, object_id)
Показывает список комнат объекта.

### show_room_card(update, context, room_id)
Показывает карточку комнаты.

### room_card_keyboard(room_id)
Клавиатура карточки.

Кнопки:
- [🚀 Начать замер / ▶️ Продолжить / ✅ Замер завершён]
- [📐 Размеры] [👁 Что замерено]
- [🚪 Проёмы] [🔧 Коммуникации]
- [🪑 Мебель]
- [📋 Задачи] [📸 Фото]
- [✏️ Переименовать]
- [🗑 Удалить]
- [📤 Экспорт] (новое)
- [⬅️ К комнатам]

### handle_rooms_callback(update, context)
Главный роутер callback'ов комнат.

Обрабатывает префиксы:
- rooms_list_*, room_*, wall_*, openings_*, opening_*, comm_*, obj_*

---

## 4. МАСТЕР ЗАМЕРОВ — ПОСЛЕДОВАТЕЛЬНОСТЬ

### 4.1. room_start_<room_id>
Точка входа. Проверяет:
- Высота замерена? → нет → к высоте.
- Стены замерены? → нет → к обходу стен.
- Всё замерено? → финал.

### 4.2. Высота
- room_height_ask_ → одинаково/разно.
- room_height_same_start_ → 1 замер.
- room_height_three_start_ → 3 замера.
- _show_height_step(query, context, room_id, step) — шаг.
- room_height_same_ — если «все одинаковые».

### 4.3. Обход стен
- wall_round_start_<room_id> — точка входа.
- Восстанавливает из wall_drafts, если есть черновик.
- Иначе — начинает с галочек стены 1.

### 4.4. Стена — галочки (flags)
- _show_wall_step(query, context, room_id, step, phase='flags')
- Кнопки wall_round_flag_{flag}_{room_id}
- wall_round_flags_done_ — переход к плоскости.

### 4.5. Стена — плоскость (plane)
- _show_wall_plane(query, context, room_id)
- Кнопки wall_round_plane_straight_ / wall_round_plane_wavy_

### 4.6. Стена — длина (length)
- _show_wall_length(query, context, room_id, step)
- Ввод текста: waiting_for='wall_round_length'

### 4.7. Стена — проёмы (openings)
- _show_wall_openings(query, context, room_id, step)
- Кнопки wall_round_open_win_ / wall_round_open_door_ / wall_round_open_vent_
- wall_round_openings_done_ — переход к углу.

### 4.8. Стена — угол (angle)
- _show_wall_angle(query, context, room_id, step)
- Кнопки wall_round_angle_90 / 60 / 100 / deg

### 4.9. Доп. шаги (ниши, rounded, wavy, hidden)
- _do_wall_step(query, context, room_id, first)
- Обрабатывает по очереди то, что в wall_remaining_steps.

### 4.10. Ниша
- wall_niche_count_<count>_<room_id>
- Шаги: niche_width → niche_depth → niche_height → niche_plane
- Ровная: wall_niche_plane_rect_
- Неровная: wall_niche_plane_irr_ → niche_top_width → niche_top_depth

### 4.11. Сохранение стены
- _wall_save_and_next(query, context, room_id, step)
- add_measure + add_niche для каждой ниши
- Очистка wall_drafts
- Переход к следующей стене или финалу

### 4.12. Финал
- _wall_finish(query, context, room_id, summary_prefix)
- Расчёт площадей
- Рисует room_{id}_final.png

---

## 5. ЧЕРНОВИК (wall_drafts)

### _save_wall_draft(context, room_id, step_name)
Сохраняет всё в wall_drafts:
- step_num, step_name
- flags (JSON)
- length, plane, angle_value, angle_method
- niches (JSON), niche_count, niche_current, niche_temp (JSON)
- remaining_steps (JSON)

### _load_wall_draft(context, room_id)
Восстанавливает из wall_drafts в context.user_data.
Возвращает step_name.

### _clear_wall_draft(room_id)
Удаляет черновик после успешного сохранения стены.

---

## 6. ОБРАБОТКА ТЕКСТА

### handle_measure_input(update, context)
Роутер по waiting_for.

### _handle_wall_round_input(update, context, step)
Обработка ввода при обходе:
- wall_round_length
- wall_round_angle_val
- wall_niche_width
- wall_niche_depth
- wall_niche_height
- wall_niche_top_width
- wall_niche_top_depth
- wall_rounded_radius
- wall_wavy_note
- wall_hidden_note
- wall_round_plane_bottom / middle / top

### _handle_wall_round_opening_input(update, context, step)
Ввод размеров проёма при обходе:
- wall_round_opening_width
- wall_round_opening_height

---

## 7. ПРАВИЛА

1. Никаких магических строк — всё из `core/spec.py`.
2. Каждый шаг — отдельная функция `_show_*`.
3. Черновик — после КАЖДОГО изменения.
4. Восстановление — по всем подшагам (`niche_width`, `niche_depth`, `niche_height`, `niche_plane`).
5. Специфичные callback — раньше универсальных.
6. Один вход — один выход (handle_measure_input).

---

*Конец SPECS/rooms.md*
