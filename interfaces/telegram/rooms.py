"""interfaces.telegram.rooms — UI комнат в Telegram."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room, create_room, delete_room
from core.rooms_ui import format_room_card, format_rooms_list
from core.measures import get_measures, calculate_room_areas, format_measure, get_walls_ordered
from core.comms import get_comms, format_comm
from core.room_objects import get_room_objects, format_room_object


def rooms_list_keyboard(object_id):
    """Клавиатура списка комнат."""
    rooms = get_rooms(object_id)
    buttons = []
    for r in rooms:
        mark = "🏠" if r.get('is_default') else "📦"
        buttons.append([InlineKeyboardButton(
            f"{mark} {r['name']}",
            callback_data=f"room_{r['id']}"
        )])
    buttons.append([InlineKeyboardButton(
        "➕ Добавить комнату",
        callback_data=f"room_add_{object_id}"
    )])
    buttons.append([InlineKeyboardButton(
        "⬅️ К объекту",
        callback_data=f"obj_{object_id}"
    )])
    return InlineKeyboardMarkup(buttons)


def room_card_keyboard(room_id):
    """Клавиатура карточки комнаты."""
    room = get_room(room_id)
    object_id = room['object_id'] if room else 0
    # Кнопка «Продолжить замер» — если есть незавершённый шаг
    extra_row = []
    import interfaces.telegram.rooms as _self
    # Просто проверим, есть ли незавершённый замер по флагам (не работает без context, но пусть будет)
    # Проверяем что замерено
    from core.measures import get_walls_ordered
    walls = get_walls_ordered(room_id)
    height_ok = bool(room.get('height_bottom') and room.get('height_middle') and room.get('height_top'))
    walls_ok = len(walls) >= 4
    
    if not height_ok and not walls:
        # Ничего не замерено
        start_btn = InlineKeyboardButton("🚀 Начать замер", callback_data=f"room_start_{room_id}")
    elif height_ok and walls_ok:
        # Всё замерено
        start_btn = InlineKeyboardButton("✅ Замер завершён", callback_data=f"room_start_{room_id}")
    else:
        # Частично
        start_btn = InlineKeyboardButton("▶️ Продолжить замер", callback_data=f"room_start_{room_id}")
    
    return InlineKeyboardMarkup([
        [start_btn],
        [InlineKeyboardButton("📐 Размеры", callback_data=f"room_measures_{room_id}"),
         InlineKeyboardButton("👁 Что замерено", callback_data=f"room_progress_{room_id}")],
        [InlineKeyboardButton("🚪 Проёмы", callback_data=f"openings_list_{room_id}"),
         InlineKeyboardButton("🔧 Коммуникации", callback_data=f"room_comms_{room_id}")],
        [InlineKeyboardButton("🪑 Мебель", callback_data=f"room_objects_{room_id}")],
        [InlineKeyboardButton("📋 Задачи", callback_data=f"room_tasks_{room_id}"),
         InlineKeyboardButton("📸 Фото", callback_data=f"room_photos_{room_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"room_del_{room_id}")],
        [InlineKeyboardButton("⬅️ К комнатам", callback_data=f"rooms_list_obj_{object_id}")],
    ])


async def show_rooms_list(update, context, object_id):
    """Показывает список комнат объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else '—'
    text = f"📦 *Комнаты «{obj_name}»*\n\n{format_rooms_list(object_id)}"
    kb = rooms_list_keyboard(object_id)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )


async def show_room_card(update, context, room_id):
    """Показывает карточку комнаты. Работает и с текстовыми, и с фото-сообщениями."""
    room = get_room(room_id)
    if not room:
        await update.callback_query.edit_message_text("❌ Комната не найдена")
        return
    text = format_room_card(room_id)
    kb = room_card_keyboard(room_id)
    query = update.callback_query
    # Проверяем — если сообщение с фото (без текста), edit_message_text упадёт
    has_photo = bool(getattr(query.message, "photo", None))
    if has_photo:
        # Удаляем фото-сообщение и отправляем новое текстовое
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )
    else:
        try:
            await query.edit_message_text(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            # Fallback: если edit не сработал (например, сообщение слишком старое)
            if "no text in the message" in str(e).lower() or "message is not modified" not in str(e).lower():
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await query.message.chat.send_message(
                    text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
                )


async def handle_rooms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер callback'ов комнат."""
    query = update.callback_query
    await query.answer()
    data = query.data
    print(f"🔍 ROOMS: data={data!r}")
    print(f"🔍 handle_rooms_callback: data={data!r}")

    # Карточка комнаты
    _room_exclude = ("room_add_", "room_del_", "room_delok_",
                     "room_tasks_", "room_measures_", "room_measure_add_", "room_measure_cat_",
                     "room_comms_", "room_objects_", "room_photos_",
                     "room_conflicts_", "room_forecast_", "room_type_",
                     "room_method_", "room_height_", "room_start_", "room_progress_")
    if data.startswith("room_") and not data.startswith(_room_exclude):
        try:
            room_id = int(data.replace("room_", ""))
        except ValueError:
            return
        await show_room_card(update, context, room_id)
        return

    # Добавить комнату — просим ввести название
    if data.startswith("room_add_"):
        object_id = int(data.replace("room_add_", ""))
        context.user_data['waiting_for'] = 'room_name'
        context.user_data['room_object_id'] = object_id
        await query.edit_message_text(
            f"📦 *Новая комната*\n\n"
            f"Напиши название (свободный ввод):\n"
            f"_Например: «Детская Саши», «Детская 1», «Гостиная-кухня»_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"rooms_list_obj_{object_id}")]
            ])
        )
        return

    # Выбор типа помещения → создание → карточка
    if data.startswith("room_type_"):
        parts = data.replace("room_type_", "").split("_", 1)
        object_id = int(parts[0])
        room_type = parts[1]
        name = context.user_data.get('room_name_pending') or 'Комната'
        new_room_id = create_room(object_id, name, room_type=room_type)
        if new_room_id:
            context.user_data['room_name_pending'] = None
            context.user_data['waiting_for'] = None
            # Сразу показываем карточку комнаты
            await show_room_card(update, context, new_room_id)
        else:
            await query.edit_message_text("❌ Не удалось создать комнату")
        return

    # Кнопка «📏 Высота» — сначала спрашиваем «одинаковая или разная?»
    if data.startswith("room_height_ask_"):
        room_id = int(data.replace("room_height_ask_", ""))
        context.user_data['height_room_id'] = room_id
        # Спрашиваем тип замера
        await query.edit_message_text(
            f"📏 *Высота потолка*\n\n"
            f"Высота одинаковая во всей комнате\n"
            f"или отличается в разных точках?\n\n"
            f"_Обычно высота одинаковая — тогда 1 замер._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Одинаковая (1 замер)", callback_data=f"room_height_same_start_{room_id}")],
                [InlineKeyboardButton("📏 Разная (3 замера)", callback_data=f"room_height_three_start_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
        )
        return

    # Одинаковая высота — 1 замер (центр)
    if data.startswith("room_height_same_start_"):
        room_id = int(data.replace("room_height_same_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        context.user_data['height_mode'] = 'same'  # режим: одна высота
        await _show_height_step(query, context, room_id, None, step=1)
        return

    # Разная высота — 3 замера
    if data.startswith("room_height_three_start_"):
        room_id = int(data.replace("room_height_three_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        context.user_data['height_mode'] = 'three'  # режим: 3 точки
        await _show_height_step(query, context, room_id, None, step=1)
        return

    # === 👁 ЧТО ЗАМЕРЕНО ===
    if data.startswith("room_progress_"):
        room_id = int(data.replace("room_progress_", ""))
        room = get_room(room_id)
        if not room:
            await query.edit_message_text("❌ Комната не найдена")
            return

        from core.measures import get_walls_ordered, get_niches_by_room, get_walls_progress
        walls = get_walls_ordered(room_id)
        niches = get_niches_by_room(room_id) if 'get_niches_by_room' in globals() or True else []

        # Высота
        h_bottom = room.get('height_bottom')
        h_middle = room.get('height_middle')
        h_top = room.get('height_top')
        h_avg = room.get('height')
        height_ok = bool(h_bottom and h_middle and h_top)
        height_part = bool(h_bottom)

        # Стены
        walls_ok = len(walls) >= 4
        walls_part = len(walls) > 0

        # Проёмы и коммуникации — через core.db
        from core.db import fetchone
        try:
            r = fetchone("SELECT COUNT(*) as cnt FROM openings WHERE room_id = ?", (room_id,))
            openings_count = r['cnt'] if r else 0
        except Exception as e:
            print(f"⚠️ openings count: {e}")
            openings_count = 0
        try:
            r = fetchone("SELECT COUNT(*) as cnt FROM room_comms WHERE room_id = ?", (room_id,))
            comms_count = r['cnt'] if r else 0
        except Exception as e:
            print(f"⚠️ comms count: {e}")
            comms_count = 0

        # Формируем текст
        text = f"👁 *Что замерено в комнате «{room['name']}»*\n\n"

        # Высота
        if height_ok:
            text += f"📏 Высота: ✅ {int(h_avg) if h_avg == int(h_avg) else round(h_avg, 1)} см\n"
            if h_bottom == h_middle == h_top:
                text += f"   • везде одинаковая\n"
            else:
                text += f"   • центр {int(h_bottom)}, левый {int(h_middle)}, правый {int(h_top)}\n"
        elif height_part:
            text += f"📏 Высота: ⚠️ частично (только 1 точка)\n"
        else:
            text += f"📏 Высота: ❌ не замерена\n"

        # Стены
        if walls_ok:
            text += f"🧱 Стены: ✅ {len(walls)} шт.\n"
        elif walls_part:
            text += f"🧱 Стены: ⚠️ {len(walls)} из 4\n"
        else:
            text += f"🧱 Стены: ❌ не замерены\n"

        # Проёмы
        if openings_count > 0:
            text += f"🚪 Проёмы: ✅ {openings_count} шт.\n"
        else:
            text += f"🚪 Проёмы: ❌ не замерены\n"

        # Коммуникации
        if comms_count > 0:
            text += f"🔧 Коммуникации: ✅ {comms_count} шт.\n"
        else:
            text += f"🔧 Коммуникации: ❌ не замерены\n"

        text += "\n*Что дальше?*"

        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Продолжить замер", callback_data=f"room_start_{room_id}")],
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    # === 🚪 ПРОЁМЫ ===
    if data.startswith("openings_list_"):
        room_id = int(data.replace("openings_list_", ""))
        from core.measures import get_openings, format_opening, OPENING_TYPES
        openings = get_openings(room_id)
        room = get_room(room_id)
        room_name = room['name'] if room else '?'

        text = f"🚪 *Проёмы в комнате «{room_name}»*\n\n"
        if not openings:
            text += "_Пока проёмов нет._\n\n"
            text += "Добавь окна, двери или вентиляцию."
        else:
            text += f"Найдено: {len(openings)}\n\n"
            for i, o in enumerate(openings, 1):
                text += f"{i}. {format_opening(o)}\n"

        buttons = []
        for o in openings:
            label = OPENING_TYPES.get(o.get('opening_type'), '?')
            wall = o.get('wall_pos') or '?'
            buttons.append([InlineKeyboardButton(
                f"{label} ({wall})",
                callback_data=f"opening_show_{o['id']}"
            )])
        buttons.append([InlineKeyboardButton("➕ Добавить проём", callback_data=f"opening_add_{room_id}")])
        buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])

        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Добавить проём — выбор типа
    if data.startswith("opening_add_"):
        room_id = int(data.replace("opening_add_", ""))
        from core.measures import OPENING_TYPES
        buttons = []
        for code, label in OPENING_TYPES.items():
            buttons.append([InlineKeyboardButton(label, callback_data=f"opening_type_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")])
        await query.edit_message_text(
            f"🚪 *Новый проём*\n\nВыбери тип:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Выбор стены
    if data.startswith("opening_type_"):
        parts = data.replace("opening_type_", "").split("_", 1)
        room_id = int(parts[0])
        otype = parts[1]
        context.user_data['opening_room_id'] = room_id
        context.user_data['opening_type'] = otype
        from core.measures import OPENING_TYPES
        label = OPENING_TYPES.get(otype, otype)
        buttons = [
            [InlineKeyboardButton("1. Напротив", callback_data=f"opening_wall_{room_id}_напротив")],
            [InlineKeyboardButton("2. Слева", callback_data=f"opening_wall_{room_id}_слева")],
            [InlineKeyboardButton("3. У входа", callback_data=f"opening_wall_{room_id}_у входа")],
            [InlineKeyboardButton("4. Справа", callback_data=f"opening_wall_{room_id}_справа")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
        ]
        await query.edit_message_text(
            f"🚪 *{label}*\n\nНа какой стене?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Выбор стены → запрос ширины
    if data.startswith("opening_wall_"):
        parts = data.replace("opening_wall_", "").split("_", 1)
        room_id = int(parts[0])
        wall_pos = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['opening_wall_pos'] = wall_pos
        context.user_data['waiting_for'] = 'opening_width'
        await query.edit_message_text(
            f"📏 *Ширина проёма* (СМ):\n\n_Напиши число и отправь._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
            ])
        )
        return

    # Показать проём
    if data.startswith("opening_show_"):
            opening_id = int(data.replace("opening_show_", ""))
            from core.measures import get_opening, format_opening, OPENING_TYPES
            o = get_opening(opening_id)
            if not o:
                await query.edit_message_text("❌ Проём не найден")
                return

            otype = o.get('opening_type') or '?'
            label = OPENING_TYPES.get(otype, otype)
            wall_pos = o.get('wall_pos') or '?'
            width = o.get('width')
            height = o.get('height')
            sill = o.get('sill_height')
            offset = o.get('offset_x') or 0

            def fmt(v):
                if v is None or v == 0:
                    return "0"
                return str(int(v)) if v == int(v) else str(round(v, 1))

            text = f"🚪 *Проём #{opening_id}*\n\n"
            text += f"{label}\n"
            text += f"🧱 Стена: {wall_pos}\n"
            text += f"📏 Ширина: {fmt(width)} см\n"
            text += f"📏 Высота: {fmt(height)} см\n"
            if sill:
                text += f"📏 Подоконник: {fmt(sill)} см\n"
            if offset:
                text += f"📐 Смещение от угла: {fmt(offset)} см\n"

            buttons = [
                [InlineKeyboardButton("✏️ Ширина", callback_data=f"opening_edit_{opening_id}_width")],
                [InlineKeyboardButton("✏️ Высота", callback_data=f"opening_edit_{opening_id}_height")],
            ]
            if otype == 'window':
                buttons.append([InlineKeyboardButton("✏️ Подоконник", callback_data=f"opening_edit_{opening_id}_sill")])
            buttons.append([InlineKeyboardButton("✏️ Смещение от угла", callback_data=f"opening_edit_{opening_id}_offset")])
            buttons.append([InlineKeyboardButton("✏️ Стена", callback_data=f"opening_edit_{opening_id}_wall")])
            buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data=f"opening_del_{opening_id}")])
            buttons.append([InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{o['room_id']}")])

            await query.edit_message_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return

    # === РЕДАКТИРОВАНИЕ ПРОЁМА ===
    if data.startswith("opening_edit_"):
        parts = data.replace("opening_edit_", "").split("_")
        opening_id = int(parts[0])
        field = parts[1] if len(parts) > 1 else None

        from core.measures import get_opening
        o = get_opening(opening_id)
        if not o:
            await query.edit_message_text("❌ Проём не найден")
            return

        if field == 'wall':
            # Выбор стены
            buttons = [
                [InlineKeyboardButton("1. Напротив", callback_data=f"opening_set_{opening_id}_wall_напротив")],
                [InlineKeyboardButton("2. Слева", callback_data=f"opening_set_{opening_id}_wall_слева")],
                [InlineKeyboardButton("3. У входа", callback_data=f"opening_set_{opening_id}_wall_у входа")],
                [InlineKeyboardButton("4. Справа", callback_data=f"opening_set_{opening_id}_wall_справа")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_show_{opening_id}")],
            ]
            await query.edit_message_text(
                f"✏️ *Смена стены*\n\nНа какой стене?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return

        # Для остальных — просим значение
        prompt_text = {
            'width': '📏 *Новая ширина* (СМ):',
            'height': '📏 *Новая высота* (СМ):',
            'sill': '📏 *Новая высота подоконника* (СМ):',
            'offset': '📐 *Новое смещение от угла* (СМ):',
        }.get(field, 'Значение')

        context.user_data['opening_edit_id'] = opening_id
        context.user_data['opening_edit_field'] = field
        context.user_data['waiting_for'] = 'opening_edit_value'

        await query.edit_message_text(
            f"{prompt_text}\n\n_Напиши число и отправь._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_show_{opening_id}")],
            ])
        )
        return

    if data.startswith("opening_set_"):
        # opening_set_<id>_<field>_<value>
        parts = data.replace("opening_set_", "").split("_")
        opening_id = int(parts[0])
        field = parts[1]
        value = "_".join(parts[2:])
        from core.measures import update_opening
        if field == 'wall':
            update_opening(opening_id, wall_pos=value)
        # Показываем карточку
        from core.measures import get_opening
        o = get_opening(opening_id)
        if o:
            # Перенаправляем на opening_show_
            await query.edit_message_text("✅ Обновлено")
            # Имитируем открытие
            from core.measures import OPENING_TYPES
            otype = o.get('opening_type') or '?'
            label = OPENING_TYPES.get(otype, otype)
            text = f"🚪 *Проём #{opening_id}*\n\n{label}\n🧱 Стена: {o.get('wall_pos')}"
            buttons = [
                [InlineKeyboardButton("✏️ Ширина", callback_data=f"opening_edit_{opening_id}_width")],
                [InlineKeyboardButton("✏️ Высота", callback_data=f"opening_edit_{opening_id}_height")],
                [InlineKeyboardButton("⬅️ К проёму", callback_data=f"opening_show_{opening_id}")],
                [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{o['room_id']}")],
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        return

        text = f"🚪 *Проём #{opening_id}*\n\n{format_opening(o)}"
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Удалить", callback_data=f"opening_del_{opening_id}")],
                [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{o['room_id']}")],
            ])
        )
        return

    # Удалить проём
    if data.startswith("opening_del_"):
        opening_id = int(data.replace("opening_del_", ""))
        from core.measures import get_opening, delete_opening
        o = get_opening(opening_id)
        room_id = o['room_id'] if o else None
        delete_opening(opening_id)
        if room_id:
            await query.edit_message_text(
                "✅ Проём удалён",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{room_id}")],
                ])
            )
        return

    # === ОТМЕНА ДОБАВЛЕНИЯ ПРОЁМА ===
    if data.startswith("opening_cancel_"):
        room_id = int(data.replace("opening_cancel_", ""))
        # Чистим
        for k in ['opening_room_id', 'opening_type', 'opening_wall_pos',
                  'opening_width', 'opening_height', 'opening_sill',
                  'opening_offset_x']:
            context.user_data[k] = None
        context.user_data['waiting_for'] = None
        # Возвращаемся к списку проёмов
        from core.measures import get_openings, format_opening, OPENING_TYPES
        openings = get_openings(room_id)
        room = get_room(room_id)
        room_name = room['name'] if room else '?'

        text = f"🚪 *Проёмы в комнате «{room_name}»*\n\n"
        if not openings:
            text += "_Пока проёмов нет._"
        else:
            text += f"Найдено: {len(openings)}\n\n"
            for i, o in enumerate(openings, 1):
                text += f"{i}. {format_opening(o)}\n"

        buttons = []
        for o in openings:
            label = OPENING_TYPES.get(o.get('opening_type'), '?')
            buttons.append([InlineKeyboardButton(
                f"{label} ({o.get('wall_pos') or '?'})",
                callback_data=f"opening_show_{o['id']}"
            )])
        buttons.append([InlineKeyboardButton("➕ Добавить проём", callback_data=f"opening_add_{room_id}")])
        buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])

        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # === НАЗАД НА ПРЕДЫДУЩИЙ ШАГ ПРОЁМА ===
    if data.startswith("opening_back_"):
        parts = data.replace("opening_back_", "").split("_", 1)
        field = parts[0]
        room_id = int(parts[1])
        context.user_data['opening_room_id'] = room_id

        if field == 'width':
            context.user_data['waiting_for'] = 'opening_width'
            context.user_data['opening_width'] = None
            await query.edit_message_text(
                "✏️ *Изменение ширины*\n\n"
                "📏 *Ширина проёма* (СМ):\n\n"
                "_Напиши число и отправь._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Отмена", callback_data=f"opening_cancel_{room_id}")],
                ])
            )
            return

        if field == 'height':
            context.user_data['waiting_for'] = 'opening_height'
            context.user_data['opening_height'] = None
            await query.edit_message_text(
                "✏️ *Изменение высоты*\n\n"
                "📏 *Высота проёма* (СМ):\n\n"
                "_Напиши число и отправь._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Отмена", callback_data=f"opening_cancel_{room_id}")],
                ])
            )
            return

        if field == 'sill':
            context.user_data['waiting_for'] = 'opening_sill'
            context.user_data['opening_sill'] = None
            await query.edit_message_text(
                "✏️ *Изменение подоконника*\n\n"
                "📏 *Высота подоконника* (СМ):\n\n"
                "_Напиши число и отправь._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Отмена", callback_data=f"opening_cancel_{room_id}")],
                ])
            )
            return

        if field == 'offset':
            context.user_data['waiting_for'] = 'opening_offset'
            context.user_data['opening_offset_x'] = None
            await query.edit_message_text(
                "✏️ *Изменение смещения*\n\n"
                "📐 *Смещение от левого угла стены* (СМ):\n\n"
                "_Напиши число и отправь._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Отмена", callback_data=f"opening_cancel_{room_id}")],
                ])
            )
            return

    # === 🚀 МАСТЕР ЗАМЕРОВ ===
    if data.startswith("room_start_"):
        room_id = int(data.replace("room_start_", ""))
        room = get_room(room_id)
        if not room:
            await query.edit_message_text("❌ Комната не найдена")
            return

        # 1. Проверяем высоту
        h_bottom = room.get('height_bottom')
        h_middle = room.get('height_middle')
        h_top = room.get('height_top')
        height_ok = bool(h_bottom and h_middle and h_top)

        # 2. Проверяем стены
        from core.measures import get_walls_ordered
        walls = get_walls_ordered(room_id)
        walls_ok = len(walls) >= 4

        # 3. Ведём по шагам
        if not height_ok:
            # Высота не замерена (или частично)
            if h_bottom and not (h_middle and h_top):
                # Частично — продолжаем
                context.user_data['height_room_id'] = room_id
                context.user_data['height_step'] = 2 if not h_middle else 3
                context.user_data['height_bottom'] = h_bottom
                context.user_data['height_middle'] = h_middle
                context.user_data['height_top'] = h_top
                context.user_data['waiting_for'] = 'room_height_point'
                await query.edit_message_text(
                    f"🚀 *Продолжаем замер*\n\n"
                    f"📏 *Шаг 1: Высота потолка*\n"
                    f"✅ Точка 1 (центр): {h_bottom} см\n\n"
                    f"Продолжить?",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Продолжить", callback_data=f"room_height_continue_{room_id}")],
                        [InlineKeyboardButton("🔄 Заново", callback_data=f"room_height_ask_{room_id}")],
                    ])
                )
                return
            else:
                # С нуля
                context.user_data['height_room_id'] = room_id
                context.user_data['height_step'] = 1
                context.user_data['height_bottom'] = None
                context.user_data['height_middle'] = None
                context.user_data['height_top'] = None
                context.user_data['waiting_for'] = 'room_height_point'
                await query.edit_message_text(
                    f"🚀 *Мастер замеров*\n\n"
                    f"📏 *Шаг 1 из 3: Высота потолка*\n\n"
                    f"Замерим высоту в 3 точках: центр, левый угол, правый угол.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Начать", callback_data=f"room_height_ask_{room_id}")],
                        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                    ])
                )
                return

        if not walls_ok:
            # Есть высота, но стены не замерены
            context.user_data['wall_room_id'] = room_id
            context.user_data['wall_step'] = 1
            context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
            from core.measures import start_walls_round
            start_walls_round(room_id)
            await _show_wall_step(query, context, room_id, 1, phase='flags')
            return

        # Всё замерено — итог
        # (импорт calculate_room_areas уже сверху)
        areas = calculate_room_areas(room_id)
        total_length = sum((w['length'] if w['length'] else 0) for w in walls)

        text = (
            f"🎉 *Замер комнаты завершён!*\n\n"
            f"📏 Высота: {room.get('height') or '—'} см\n"
            f"🧱 Стены: {len(walls)} шт.\n"
            f"📐 Сумма длин: {total_length:.0f} см\n"
        )
        if areas.get('walls_net') is not None:
            text += f"📊 Площадь стен: {areas['walls_net']} м²\n"
        if areas.get('floor'):
            text += f"📊 Площадь пола: {areas['floor']} м²\n"

        text += "\n*Что дальше?*"

        await query.edit_message_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("🔄 Замер заново", callback_data=f"wall_round_reset_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    
    # Продолжить с точки 2 (после возврата в комнату)
    if data.startswith("room_height_continue_"):
        room_id = int(data.replace("room_height_continue_", ""))
        room = get_room(room_id)
        h_bottom = room.get('height_bottom') if room else None
        h_middle = room.get('height_middle') if room else None
        context.user_data['height_room_id'] = room_id
        context.user_data['height_bottom'] = h_bottom
        context.user_data['height_middle'] = h_middle
        context.user_data['waiting_for'] = 'room_height_point'
        if h_bottom and not h_middle:
            # С точки 2
            context.user_data['height_step'] = 2
            caption = (
                f"✅ *Точка 1 (центр):* {h_bottom} см\n\n"
                f"📏 *Высота — шаг 2 из 3*\n\n"
                f"📍 *Точка 2 — у ЛЕВОГО угла*\n\n"
                f"Перейди к левому углу (у левой стены).\n\n"
                f"*Как замерить:*\n"
                f"1. ⚙️ Проверь режим дальномера — *«от задней стенки»*\n"
                f"2. Приложи к полу, наведи на потолок\n"
                f"3. Нажми — получишь цифру\n"
                f"4. Введи в СМ\n\n"
                f"_Например: 272_"
            )
            kb_extra = [
                [InlineKeyboardButton("✅ Все три одинаковые", callback_data=f"room_height_same_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ]
            await _send_height_scheme(query, context, room_id, 2, caption, kb_extra)
        elif h_bottom and h_middle:
            # С точки 3
            context.user_data['height_step'] = 3
            caption = (
                f"✅ *Точка 2 (левый угол):* {h_middle} см\n\n"
                f"📏 *Высота — шаг 3 из 3*\n\n"
                f"📍 *Точка 3 — у ПРАВОГО угла*\n\n"
                f"Перейди к правому углу (у правой стены).\n\n"
                f"*Как замерить:*\n"
                f"1. ⚙️ Проверь режим дальномера — «от задней стенки»\n"
                f"2. Приложи к полу, наведи на потолок\n"
                f"3. Нажми — получишь цифру\n"
                f"4. Введи в СМ\n\n"
                f"_Например: 271_"
            )
            await _send_height_scheme(query, context, room_id, 3, caption)
        else:
            await _show_height_step(query, context, room_id, None, step=1)
        return

    # Выбор инструмента → инструкция + экран высоты
    if data.startswith("room_method_"):
        parts = data.replace("room_method_", "").split("_", 1)
        room_id = int(parts[0])
        method = parts[1]
        # Сохраняем инструмент
        from core.rooms import update_room
        update_room(room_id, measure_method=method)
        # Инструкция + схема + вопрос о высоте
        await _show_height_step(query, context, room_id, method, step=1)
        return

    # Кнопка «Все три одинаковые» — сразу записываем все 3 = точке 1
    if data.startswith("room_height_same_"):
        room_id = int(data.replace("room_height_same_", ""))
        # Значение точки 1 (центра) — уже сохранено в height_bottom
        center = context.user_data.get('height_bottom') or 0
        if not center:
            # Если точки 1 нет — просим ввести одну цифру (старый сценарий)
            context.user_data['height_room_id'] = room_id
            context.user_data['waiting_for'] = 'room_height_same'
            context.user_data['height_step'] = 'same'
            # Удаляем фото-сообщение и отправляем текстовое
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(
                "📏 *Высота потолка*\n\n"
                "Введи одну цифру в СМ:",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        # Записываем все три = center
        from core.rooms import update_room
        update_room(room_id, height=center, height_bottom=center, height_middle=center, height_top=center)
        # Чистим состояние
        for k in ['waiting_for', 'height_room_id', 'height_step',
                  'height_bottom', 'height_middle', 'height_top']:
            context.user_data[k] = None
        # Удаляем фото и отправляем итог
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            f"✅ *Высота потолка: {center} см* (везде одинаково)\n\n"
            f"📐 Теперь можно начать обход стен по часовой стрелке.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    if data.startswith("room_height_three_"):
        room_id = int(data.replace("room_height_three_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        await _show_height_step(query, context, room_id, None, step=1)
        return

    # Удалить комнату — подтверждение
    if data.startswith("room_del_"):
        room_id = int(data.replace("room_del_", ""))
        room = get_room(room_id)
        if not room:
            await query.edit_message_text("❌ Комната не найдена")
            return
        await query.edit_message_text(
            f"🗑 *Удалить комнату «{room['name']}»?*\n\n"
            f"Задачи, фото и расходы будут отвязаны (не удалены).",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"room_delok_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
        )
        return

    # Подтверждение удаления
    if data.startswith("room_delok_"):
        room_id = int(data.replace("room_delok_", ""))
        room = get_room(room_id)
        if room:
            object_id = room['object_id']
            delete_room(room_id)
            await show_rooms_list(update, context, object_id)
        return

    # Показать задачи комнаты (заглушка пока)
    if data.startswith("room_tasks_"):
        room_id = int(data.replace("room_tasks_", ""))
        await query.edit_message_text(
            "📋 Задачи комнаты — в разработке (следующий этап).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # Размеры
    if data.startswith("room_measures_"):
        room_id = int(data.replace("room_measures_", ""))
        measures = get_measures(room_id)
        if not measures:
            await query.edit_message_text(
                "📐 Размеров пока нет.\n\nНажми «➕ Добавить» — Бо поведёт тебя по шагам замеров.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить размер", callback_data=f"room_measure_add_{room_id}")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
            return
        lines = [f"📐 *Размеры комнаты* ({len(measures)}):\n"]
        for m in measures:
            lines.append(format_measure(m, show_area=True))
        areas = calculate_room_areas(room_id)
        lines.append("")
        lines.append(f"Стены (чистые): {areas['walls_net']} м²")
        lines.append(f"Пол: {areas['floor']} м²")
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить размер", callback_data=f"room_measure_add_{room_id}")],
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # Коммуникации
    if data.startswith("room_comms_"):
        room_id = int(data.replace("room_comms_", ""))
        comms = get_comms(room_id)
        if not comms:
            await query.edit_message_text(
                "🔧 Коммуникаций пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
            return
        lines = [f"🔧 *Коммуникации* ({len(comms)}):\n"]
        for c in comms:
            lines.append(format_comm(c))
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # Мебель/техника
    if data.startswith("room_objects_"):
        room_id = int(data.replace("room_objects_", ""))
        objects = get_room_objects(room_id)
        if not objects:
            await query.edit_message_text(
                "🪑 Мебели/техники пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
            return
        lines = [f"🪑 *Мебель/техника* ({len(objects)}):\n"]
        for o in objects:
            lines.append(format_room_object(o))
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # Добавить размер — шаг 1: выбор категории
    if data.startswith("room_measure_add_"):
        room_id = int(data.replace("room_measure_add_", ""))
        context.user_data['measure_room_id'] = room_id
        context.user_data['waiting_for'] = 'measure_category'
        cats = [("wall", "🧱 Стена"), ("floor", "📏 Пол"), ("ceiling", "⬆️ Потолок"),
                ("window", "🪟 Окно"), ("door", "🚪 Дверь"), ("corner", "📐 Угол")]
        buttons = [[InlineKeyboardButton(label, callback_data=f"room_measure_cat_{room_id}_{code}")]
                   for code, label in cats]
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")])
        await query.edit_message_text(
            "📐 *Новый размер*\n\nВыбери категорию:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Выбор категории → пошаговый ввод
    if data.startswith("room_measure_cat_"):
        parts = data.replace("room_measure_cat_", "").split("_")
        room_id = int(parts[0])
        category = parts[1]
        context.user_data['measure_category'] = category
        context.user_data['measure_room_id'] = room_id

        # Для стен — новый обход через wall_round_*
        if category == 'wall':
            await query.edit_message_text(
                "🧱 *Стены замеряются через «Обход стен».*\n\n"
                "Открой карточку комнаты → «📐 Обход стен».",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Обход стен", callback_data=f"wall_round_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")],
                ])
            )
            return

        cat_info = {
            'floor':   ('📏 Длина пола',  'горизонталь, от стены до стены'),
            'ceiling': ('📏 Длина потолка','горизонталь'),
            'window':  ('📏 Ширина окна', 'горизонталь'),
            'door':    ('📏 Ширина двери','горизонталь'),
            'opening': ('📏 Ширина проёма','горизонталь'),
        }
        label, hint = cat_info.get(category, ('📏 Длина', 'горизонталь'))

        context.user_data['waiting_for'] = 'measure_first_dim'
        await query.edit_message_text(
            f"📐 *Новый размер — {category}*\n\n"
            f"*Шаг 1 из 2*\n\n"
            f"{label}: __ м\n"
            f"_({hint})_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")]
            ])
        )
        return

        # Позиция стены → сразу к длине
    if data.startswith("wall_pos_"):
        parts = data.replace("wall_pos_", "").split("_", 1)
        room_id = int(parts[0])
        pos = parts[1] if len(parts) > 1 else 'напротив'
        if pos == 'своё':
            context.user_data['measure_room_id'] = room_id
            context.user_data['measure_category'] = 'wall'
            context.user_data['waiting_for'] = 'wall_pos_custom'
            await query.edit_message_text(
                "🧱 *Своё название стены*\n\nНапиши как называть:",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        context.user_data['measure_room_id'] = room_id
        context.user_data['measure_category'] = 'wall'
        context.user_data['wall_pos'] = pos
        # Инициализируем флаги (если ещё нет)
        context.user_data['wall_flags'] = {
            'niche': False, 'rounded': False,
            'wavy': False, 'hidden': False
        }
        await _show_wall_flags(query, context, room_id, pos)
        return

    if data.startswith("wall_pos_"):
        parts = data.replace("wall_pos_", "").split("_", 1)
        room_id = int(parts[0])
        pos = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['measure_room_id'] = room_id
        context.user_data['measure_category'] = 'wall'
        context.user_data['wall_pos'] = pos
        context.user_data['wall_rounded'] = None
        context.user_data['wall_bottom'] = None
        context.user_data['wall_middle'] = None
        context.user_data['wall_top'] = None
        await query.edit_message_text(
            f"🧱 *Стена {pos}*\n\n"
            f"Стена ровная или есть закругление?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_angle_none_{room_id}")],
                [InlineKeyboardButton("🔄 Закругление / кривой угол", callback_data=f"wall_angle_rounded_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # Ровная → спрашиваем про кривизну по высоте
    if data.startswith("wall_angle_none_"):
        room_id = int(data.replace("wall_angle_none_", ""))
        context.user_data['waiting_for'] = 'wall_wavy_ask'
        await query.edit_message_text(
            "📐 *Высота стены одинаковая везде?*\n\n"
            "Стена может быть ровной по углу, но кривой по высоте.\n"
            "Например: снизу 1.10 м, сверху 1.13 м.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Одинаковая", callback_data=f"wall_wavy_no_{room_id}")],
                [InlineKeyboardButton("📏 Разная (замерю в 3 точках)", callback_data=f"wall_wavy_yes_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # Высота разная → просим низ
    if data.startswith("wall_wavy_yes_"):
        room_id = int(data.replace("wall_wavy_yes_", ""))
        context.user_data['measure_room_id'] = room_id
        context.user_data['wall_wavy'] = 1
        context.user_data['waiting_for'] = 'wall_measured_bottom'
        await query.edit_message_text(
            "📏 *Замер внизу* (у пола):\n\nВведи в м:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Высота одинаковая → сразу длина
    if data.startswith("wall_wavy_no_"):
        room_id = int(data.replace("wall_wavy_no_", ""))
        context.user_data['measure_room_id'] = room_id
        context.user_data['wall_wavy'] = 0
        context.user_data['waiting_for'] = 'measure_first_dim'
        await query.edit_message_text(
            "📏 *Шаг 1 из 2*\n\n📏 Длина: __ м",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Закругление → методы
    if data.startswith("wall_angle_rounded_"):
        room_id = int(data.replace("wall_angle_rounded_", ""))
        await query.edit_message_text(
            "🔄 *Закругление / кривой угол*\n\n"
            "Как замерить угол?\n\n"
            "📏 *60-80-100 (рулетка)*\n"
            "Отмерь 60 и 80 см, замерь диагональ\n"
            "_Идеал: 100 см_\n\n"
            "📏 *100-100*\n"
            "Отмерь по 100 см, замерь расстояние\n"
            "_Идеал: 141 см_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📏 60-80-100", callback_data=f"wall_method_60_{room_id}")],
                [InlineKeyboardButton("📏 100-100", callback_data=f"wall_method_100_{room_id}")],
                [InlineKeyboardButton("✏️ Угол в °", callback_data=f"wall_method_deg_{room_id}")],
                [InlineKeyboardButton("⏭ Пропустить", callback_data=f"wall_angle_none_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # Метод → просим значение
    if data.startswith("wall_method_"):
        parts = data.replace("wall_method_", "").split("_", 1)
        method = parts[0]
        room_id = int(parts[1])
        context.user_data['angle_method'] = method
        if method == '60':
            prompt = "📏 Диагональ (60-80-100):\n_Идеал 100 см_\n\nВведи в см:"
        elif method == '100':
            prompt = "📏 Расстояние (100-100):\n_Идеал 141 см_\n\nВведи в см:"
        else:
            prompt = "📐 Угол в градусах (например 93):"
        context.user_data['waiting_for'] = 'wall_angle_value'
        await query.edit_message_text(
            prompt,
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # === ФИНАЛ СТЕНЫ: ровная / закругление / ниша / кривая ===
    if data.startswith("wall_final_"):
        parts = data.replace("wall_final_", "").split("_", 1)
        ftype = parts[0]
        room_id = int(parts[1])
        pending = context.user_data.get('wall_pending') or {}
        kwargs = pending.get('kwargs') or {}
        label = pending.get('label') or 'Стена'
        first = pending.get('length') or 0
        val = pending.get('height') or 0
        area = pending.get('area') or 0

        from core.measures import add_measure
        if ftype == 'none':
            add_measure(room_id, 'wall', **kwargs)
        elif ftype == 'rounded':
            kwargs['has_rounded'] = 1
            add_measure(room_id, 'wall', **kwargs)
        elif ftype == 'niche':
            kwargs['rounded_corner'] = 'niche'
            add_measure(room_id, 'wall', **kwargs)
        elif ftype == 'wavy':
            context.user_data['waiting_for'] = 'wall_measured_bottom'
            await query.edit_message_text(
                "📏 *Замер внизу* (у пола):\n\nВведи в м:",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Очищаем состояние
        for k in ['waiting_for', 'measure_room_id', 'measure_category',
                  'measure_first_value', 'wall_pending', 'wall_pos']:
            context.user_data[k] = None

        await query.edit_message_text(
            f"✅ *{label}*\n"
            f"Размер: {first} × {val} м\n"
            f"Площадь: {round(area, 2)} м²",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # Сколько нишей → запросы по каждой
    if data.startswith("wall_niche_count_"):
        parts = data.replace("wall_niche_count_", "").split("_", 1)
        count = int(parts[0])
        room_id = int(parts[1])
        context.user_data['wall_niche_count'] = count
        context.user_data['wall_niche_current'] = 1
        context.user_data['wall_niches'] = []
        context.user_data['waiting_for'] = 'wall_niche_width'
        await query.edit_message_text(
            f"🕳 *Ниша 1 из {count}*\n\n"
            f"📏 Ширина (по горизонтали) в СМ: __",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Toggle галочки особенностей стены
    if data.startswith("wall_flag_"):
        parts = data.replace("wall_flag_", "").rsplit("_", 1)
        flag = parts[0]
        room_id = int(parts[1])
        flags = context.user_data.get('wall_flags') or {
            'niche': False, 'rounded': False, 'wavy': False, 'hidden': False
        }
        flags[flag] = not flags.get(flag, False)
        context.user_data['wall_flags'] = flags
        pos = context.user_data.get('wall_pos') or 'слева'
        await _show_wall_flags(query, context, room_id, pos)
        return

    # Готово → идём по выбранным особенностям
    if data.startswith("wall_flags_done_"):
        room_id = int(data.replace("wall_flags_done_", ""))
        flags = context.user_data.get('wall_flags') or {}
        # Запоминаем порядок оставшихся шагов
        steps = []
        if flags.get('niche'):
            steps.append('niche')
        if flags.get('rounded'):
            steps.append('rounded')
        if flags.get('wavy'):
            steps.append('wavy')
        if flags.get('hidden'):
            steps.append('hidden')
        context.user_data['wall_remaining_steps'] = steps

        # Первый шаг
        if not steps:
            # Ничего не выбрано → сразу длина
            context.user_data['waiting_for'] = 'measure_first_dim'
            await query.edit_message_text(
                "📏 *Длина стены* в СМ: __",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        first = steps[0]
        context.user_data['wall_remaining_steps'] = steps[1:]
        await _do_wall_step(query, context, room_id, first)
        return

    # Фото (заглушка)
    if data.startswith("room_photos_"):
        room_id = int(data.replace("room_photos_", ""))
        await query.edit_message_text(
            "📸 Фото комнаты — в разработке (следующий этап).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return

    # === ОБХОД СТЕН (Этап 3) ===
    if data.startswith("wall_round_start_"):
        room_id = int(data.replace("wall_round_start_", ""))
        from core.measures import get_walls_progress, start_walls_round
        progress = get_walls_progress(room_id)
        if progress['walls_count'] >= 4:
            await query.edit_message_text(
                "✅ Все 4 стены уже замерены.\n\nЧто дальше?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Заново", callback_data=f"wall_round_reset_{room_id}")],
                    [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
            return
        start_walls_round(room_id)
        next_step = progress['current_step']
        context.user_data['wall_step'] = next_step
        context.user_data['wall_room_id'] = room_id
        context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
        await _show_wall_step(query, context, room_id, next_step, phase='flags')
        return

    if data.startswith("wall_round_reset_"):
        room_id = int(data.replace("wall_round_reset_", ""))
        from core.measures import delete_measure
        from core.db import commit
        walls = get_measures(room_id, category='wall')
        for w in walls:
            delete_measure(w['id'])
        commit("UPDATE rooms SET walls_started_at = NULL, walls_completed_at = NULL WHERE id = ?", (room_id,))
        context.user_data['wall_step'] = 1
        context.user_data['wall_room_id'] = room_id
        context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
        await _show_wall_step(query, context, room_id, 1, phase='flags')
        return

    if data.startswith("wall_round_flag_"):
        parts = data.replace("wall_round_flag_", "").split("_")
        flag = parts[0]
        room_id = int(parts[1])
        flags = context.user_data.get('wall_flags') or {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
        flags[flag] = not flags.get(flag, False)
        context.user_data['wall_flags'] = flags
        step = context.user_data.get('wall_step') or 1
        # Пробуем обновить caption без пересоздания PNG
        wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
        pos = wall_names.get(step, '?')
        f_niche = '✅' if flags.get('niche') else '⬜'
        f_rounded = '✅' if flags.get('rounded') else '⬜'
        f_wavy = '✅' if flags.get('wavy') else '⬜'
        f_hidden = '✅' if flags.get('hidden') else '⬜'
        caption = (
            f"🧱 *Стена {step} — {pos}*\n\n"
            f"👁 *Осмотри стену визуально.*\n"
            f"Отметь, что видишь:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{f_niche} С нишей", callback_data=f"wall_round_flag_niche_{room_id}")],
            [InlineKeyboardButton(f"{f_rounded} С закруглением", callback_data=f"wall_round_flag_rounded_{room_id}")],
            [InlineKeyboardButton(f"{f_wavy} Разная по высоте", callback_data=f"wall_round_flag_wavy_{room_id}")],
            [InlineKeyboardButton(f"{f_hidden} Скрытые коммуникации", callback_data=f"wall_round_flag_hidden_{room_id}")],
            [InlineKeyboardButton("➡️ Дальше (к плоскости)", callback_data=f"wall_round_flags_done_{room_id}")],
            [InlineKeyboardButton("⏭ Пропустить стену", callback_data=f"wall_round_skip_{room_id}")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        try:
            await query.edit_message_caption(
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
        except Exception as e:
            print(f"⚠️ edit_caption не работает: {e}")
            # Fallback — на всякий случай, если что-то не так
            try:
                await query.answer("✅ Обновлено", show_alert=False)
            except Exception:
                pass
        return

    if data.startswith("wall_round_flags_done_"):
        room_id = int(data.replace("wall_round_flags_done_", ""))
        step = context.user_data.get('wall_step') or 1
        context.user_data['wall_room_id'] = room_id
        context.user_data['wall_step'] = step
        context.user_data['waiting_for'] = 'wall_round_length'
        await _show_wall_length(query, context, room_id, step)
        return

    if data.startswith("wall_round_angle_"):
        parts = data.replace("wall_round_angle_", "").split("_")
        method = parts[0]
        room_id = int(parts[1])
        step = context.user_data.get('wall_step') or 1
        context.user_data['wall_angle_method'] = method
        if method == '90':
            context.user_data['wall_angle_value'] = 90
            context.user_data['wall_angle_method'] = '90'
            step_num = context.user_data.get('wall_step') or 1
            await _wall_save_and_next(query, context, room_id, step_num)
            return
        if method in ('60', '100'):
            context.user_data['waiting_for'] = 'wall_round_angle_val'
            hint = 'Идеал: 100 см' if method == '60' else 'Идеал: 141 см'
            # Оставляем ту же PNG (угол)
            import os
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            png_path = os.path.join(base, "docs", "images", f"wall_scheme_s{step}_angle.png")
            caption = f"📏 *Диагональ ({method})*\n_{hint}_\n\nВведи в СМ:"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
            if os.path.exists(png_path):
                try:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    with open(png_path, "rb") as f:
                        await query.message.chat.send_photo(
                            photo=f, caption=caption,
                            parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
                        )
                    return
                except Exception:
                    pass
            await query.edit_message_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            return
        if method == 'deg':
            context.user_data['waiting_for'] = 'wall_round_angle_val'
            import os
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            png_path = os.path.join(base, "docs", "images", f"wall_scheme_s{step}_angle.png")
            caption = "📐 *Угол в градусах*\n\nВведи (например 93):"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
            if os.path.exists(png_path):
                try:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    with open(png_path, "rb") as f:
                        await query.message.chat.send_photo(
                            photo=f, caption=caption,
                            parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
                        )
                    return
                except Exception:
                    pass
            await query.edit_message_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            return
        return

    if data.startswith("wall_round_plane_"):
        parts = data.replace("wall_round_plane_", "").split("_")
        plane = parts[0]
        room_id = int(parts[1])
        step = context.user_data.get('wall_step') or 1
        if plane == 'straight':
            context.user_data['wall_plane'] = 'straight'
            context.user_data['wall_bottom'] = None
            context.user_data['wall_middle'] = None
            context.user_data['wall_top'] = None
            context.user_data['wall_room_id'] = room_id
            context.user_data['wall_step'] = step
            context.user_data['waiting_for'] = 'wall_round_length'
            await _show_wall_length(query, context, room_id, step)
            return
        if plane == 'wavy':
            context.user_data['wall_plane'] = 'wavy'
            context.user_data['waiting_for'] = 'wall_round_plane_bottom'
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(
                "📏 *Замер СЛЕВА*\n\nОтойди к левому краю стены.\nВведи в СМ:",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return

    if data.startswith("wall_round_skip_"):
        room_id = int(data.replace("wall_round_skip_", ""))
        step = context.user_data.get('wall_step') or 1
        if step >= 4:
            await _wall_finish(query, context, room_id)
        else:
            context.user_data['wall_step'] = step + 1
            context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
            await _show_wall_step(query, context, room_id, step + 1, phase='flags')
        return

    # Назад к списку объектов (если комнату не нашли)
    if data.startswith("rooms_list_obj_"):
        object_id = int(data.replace("rooms_list_obj_", ""))
        await show_rooms_list(update, context, object_id)
        return



async def handle_measure_input(update, context):
    """Пошаговый ввод: 1) длина, 2) высота/ширина."""
    step = context.user_data.get('waiting_for')

    # === ПРОЁМЫ — в самом начале, ДО старой логики ===
    if step in ('opening_width', 'opening_height', 'opening_sill'):
        await _handle_opening_input(update, context, step)
        return

    # === ОБХОД СТЕН (Этап 3) — ПЕРВЫМ ДЕЛОМ, до старой логики ===
    if step in ('wall_round_length', 'wall_round_angle_val',
                'wall_round_plane_bottom', 'wall_round_plane_middle',
                'wall_round_plane_top'):
        await _handle_wall_round_input(update, context, step)
        return
    
    # === ВЫСОТА ПОТОЛКА — отдельная ветка (не требует measure_room_id) ===
    if step in ('room_height_point', 'room_height_same'):
        room_id = context.user_data.get('height_room_id')
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната, начни заново")
            return
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text(
                "❌ Нужно число. Например: `270`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        # === ОБРАБОТКА ТОЧЕК ВЫСОТЫ ===
        if step == 'room_height_same':
            from core.rooms import update_room
            update_room(room_id, height=val, height_bottom=val, height_middle=val, height_top=val)
            for k in ['waiting_for', 'height_room_id', 'height_step', 'height_bottom', 'height_middle', 'height_top']:
                context.user_data[k] = None
            await update.message.reply_text(
                f"✅ *Высота потолка:* {val} см\n\n"
                f"📐 Теперь можно начать обход стен по часовой стрелке.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
            return
        # step == 'room_height_point'
        point = context.user_data.get('height_step') or 1
        mode = context.user_data.get('height_mode') or 'three'  # 'same' или 'three'
        if point == 1:
            context.user_data['height_bottom'] = val
            # Если режим «одинаковая» — сохраняем все 3 = val
            if mode == 'same':
                from core.rooms import update_room
                update_room(room_id, height=val, height_bottom=val, height_middle=val, height_top=val)
                for k in ['waiting_for', 'height_room_id', 'height_step',
                          'height_bottom', 'height_middle', 'height_top', 'height_mode']:
                    context.user_data[k] = None
                await update.message.reply_text(
                    f"✅ *Высота: {val} см* (одинаковая везде)\n\n"
                    f"📐 *Теперь обход стен.*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                        [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                    ])
                )
                return
            # Иначе — режим «3 точки»
            context.user_data['height_step'] = 2
            from core.rooms import update_room
            update_room(room_id, height_bottom=val)
            caption = (
                f"✅ *Точка 1 (центр):* {val} см\n\n"
                f"📏 *Высота — шаг 2 из 3*\n\n"
                f"📍 *Точка 2 — у ЛЕВОГО угла*\n\n"
                f"Перейди к левому углу (у левой стены).\n\n"
                f"*Как замерить:*\n"
                f"1. ⚙️ Проверь режим дальномера — *«от задней стенки»*\n"
                f"2. Приложи к полу, наведи на потолок\n"
                f"3. Нажми — получишь цифру\n"
                f"4. Введи в СМ\n\n"
                f"_Например: 272_"
            )
            kb_extra = [
                [InlineKeyboardButton("✅ Все три одинаковые", callback_data=f"room_height_same_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ]
            await _send_height_scheme(update, context, room_id, 2, caption, kb_extra)
            return
        if point == 2:
            context.user_data['height_middle'] = val
            context.user_data['height_step'] = 3
            # Сохраняем сразу в БД
            from core.rooms import update_room
            update_room(room_id, height_middle=val)
            caption = (
                f"✅ *Точка 2 (левый угол):* {val} см\n\n"
                f"📏 *Если потолок везде одинаковый* — нажми кнопку ниже.\n"
                f"Иначе — замерь *точку 3 (правый угол)*.\n\n"
                f"📍 *Точка 3 — у ПРАВОГО угла*\n\n"
                f"*Как замерить:*\n"
                f"1. ⚙️ Проверь режим дальномера — *«от задней стенки»*\n"
                f"2. Приложи к полу, наведи на потолок\n"
                f"3. Нажми — получишь цифру\n"
                f"4. Введи в СМ\n\n"
                f"_Например: 271_"
            )
            await _send_height_scheme(update, context, room_id, 3, caption)
            return
        if point == 3:
            center = context.user_data.get('height_bottom') or 0
            left = context.user_data.get('height_middle') or 0
            right = val
            avg = round((center + left + right) / 3, 1)
            dev = round(max(center, left, right) - min(center, left, right), 1)
            from core.rooms import update_room
            update_room(room_id, height=avg, height_bottom=center, height_middle=left, height_top=right)
            for k in ['waiting_for', 'height_room_id', 'height_step', 'height_bottom', 'height_middle', 'height_top']:
                context.user_data[k] = None
            await update.message.reply_text(
                f"✅ *Все точки замерены!*\n\n"
                f"📊 *Итог:*\n"
                f"• Точка 1 (центр): {center} см\n"
                f"• Точка 2 (левый угол): {left} см\n"
                f"• Точка 3 (правый угол): {right} см\n\n"
                f"Средняя: *{avg} см*\n"
                f"Отклонение: *{dev} см*\n\n"
                f"📐 *Теперь обход стен по часовой от двери.*\n"
                f"Начнём со стены 1 (напротив).",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                    [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
            return
    
    # === СТАРАЯ ЛОГИКА (замеры стен, ниши, углы) ===
    room_id = context.user_data.get('measure_room_id')
    category = context.user_data.get('measure_category')
    if not room_id or not category:
        await update.message.reply_text("❌ Потерялась комната, начни заново")
        return

    text = (update.message.text or '').strip().replace(',', '.')
    try:
        val = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Нужно число. Например: `2.8`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    step = context.user_data.get('waiting_for')

    # Высота потолка — одна цифра (одинаковая)
    if step == 'room_height_same':
        from core.rooms import update_room
        room_id = context.user_data.get('height_room_id')
        update_room(room_id, height=val, height_bottom=val, height_middle=val, height_top=val)
        for k in ['waiting_for', 'height_room_id', 'height_step', 'height_bottom', 'height_middle', 'height_top']:
            context.user_data[k] = None
        await update.message.reply_text(
            f"✅ *Высота потолка:* {val} см\n\n"
            f"📐 Теперь можно начать обход стен по часовой стрелке.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    # Высота потолка — 3 точки
    if step == 'room_height_point':
        point = context.user_data.get('height_step') or 1
        if point == 1:
            context.user_data['height_bottom'] = val
            context.user_data['height_step'] = 2
            # Сохраняем сразу в БД (для восстановления после выхода)
            from core.rooms import update_room
            update_room(room_id, height_bottom=val)
            from core.rooms import update_room
            room_id = context.user_data.get('height_room_id')
            await update.message.reply_text(
                f"✅ *1 — левая:* {val} см\n\n"
                f"{_room_height_scheme(2)}\n\n"
                f"📏 *Точка 2 — у правой стены*\n"
                f"Введи в СМ:",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        if point == 2:
            context.user_data['height_middle'] = val
            context.user_data['height_step'] = 3
            # Сохраняем сразу в БД
            from core.rooms import update_room
            update_room(room_id, height_middle=val)
            caption = (
                f"✅ *Точка 2 (левый угол):* {val} см\n\n"
                f"📏 *Высота — шаг 3 из 3*\n\n"
                f"📍 *Точка 3 — у ПРАВОГО угла*\n\n"
                f"Перейди к правому углу (у правой стены).\n\n"
                f"*Как замерить:*\n"
                f"1. Приложи дальномер к полу\n"
                f"2. Наведи на потолок\n"
                f"3. Нажми кнопку — получишь цифру\n"
                f"4. Введи цифру в СМ"
            )
            await _send_height_scheme(update, context, room_id, 3, caption)
            return
        if point == 3:
            context.user_data['height_top'] = val
            # По новой логике: bottom = ЛЕВЫЙ угол, middle = ПРАВЫЙ угол, top = ЦЕНТР
            # Но у нас пользователь ввёл: 1=центр, 2=левый угол, 3=правый угол
            # Переименуем: center = height_bottom (точка 1), left = height_middle (точка 2), right = val (точка 3)
            center = context.user_data.get('height_bottom') or 0
            left = context.user_data.get('height_middle') or 0
            right = val
            b, m, t = left, right, center  # для БД: bottom=левый, middle=правый, top=центр (условно)
            avg = round((center + left + right) / 3, 1)
            dev = round(max(center, left, right) - min(center, left, right), 1)
            from core.rooms import update_room
            room_id = context.user_data.get('height_room_id')
            update_room(room_id, height=avg, height_bottom=center, height_middle=left, height_top=right)
            for k in ['waiting_for', 'height_room_id', 'height_step', 'height_bottom', 'height_middle', 'height_top']:
                context.user_data[k] = None
            await update.message.reply_text(
                f"✅ *3 — центр:* {val} см\n\n"
                f"📊 *Итог:*\n"
                f"• 1 (левая): {b} см\n"
                f"• 2 (правая): {m} см\n"
                f"• 3 (центр): {t} см\n\n"
                f"Средняя: *{avg} см*\n"
                f"Отклонение: *{dev} см*\n\n"
                f"📐 Теперь можно начать обход стен по часовой.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
            return

    # Замер стены: низ
    if step == 'wall_measured_bottom':
        context.user_data['wall_bottom'] = val
        context.user_data['waiting_for'] = 'wall_measured_middle'
        await update.message.reply_text(
            f"✅ Низ: *{val} м*\n\n📏 *Замер по центру*:\nВведи в м:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Замер стены: центр
    if step == 'wall_measured_middle':
        context.user_data['wall_middle'] = val
        context.user_data['waiting_for'] = 'wall_measured_top'
        await update.message.reply_text(
            f"✅ Центр: *{val} м*\n\n📏 *Замер вверху*:\nВведи в м:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Замер стены: верх → размеры длины
    if step == 'wall_measured_top':
        context.user_data['wall_top'] = val
        b = context.user_data.get('wall_bottom') or 0
        m = context.user_data.get('wall_middle') or 0
        t = val
        dev = round(max(b, m, t) - min(b, m, t), 3)
        await update.message.reply_text(
            f"✅ Верх: *{val} м*\n\n"
            f"⚠️ Отклонение: *{dev} м* ({int(dev*100)} см)\n\n"
            f"📏 *Теперь длина стены:*",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['waiting_for'] = 'measure_first_dim'
        return

    # Ниша: ширина → глубина → высота (ввод в СМ!)
    if step == 'wall_niche_width':
        current = context.user_data.get('wall_niche_current') or 1
        context.user_data['wall_niche_temp'] = {'width': round(val / 100, 4)}
        context.user_data['waiting_for'] = 'wall_niche_depth'
        await update.message.reply_text(
            f"🕳 *Ниша {current}*\n\n"
            f"📏 Глубина (в стене) в СМ: __",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if step == 'wall_niche_depth':
        temp = context.user_data.get('wall_niche_temp') or {}
        temp['depth'] = round(val / 100, 4)
        context.user_data['wall_niche_temp'] = temp
        context.user_data['waiting_for'] = 'wall_niche_height'
        await update.message.reply_text(
            f"📏 Высота ниши в СМ: __",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if step == 'wall_niche_height':
        temp = context.user_data.get('wall_niche_temp') or {}
        temp['height'] = round(val / 100, 4)
        niches = context.user_data.get('wall_niches') or []
        niches.append(temp)
        context.user_data['wall_niches'] = niches
        total = context.user_data.get('wall_niche_count') or 1
        current = context.user_data.get('wall_niche_current') or 1

        if current < total:
            context.user_data['wall_niche_current'] = current + 1
            context.user_data['wall_niche_temp'] = {}
            context.user_data['waiting_for'] = 'wall_niche_width'
            await update.message.reply_text(
                f"✅ Ниша {current} записана\n\n"
                f"🕳 *Ниша {current + 1} из {total}*\n\n"
                f"📏 Ширина: __ м",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        else:
            # Все ниши записаны → следующий шаг или длина
            remaining = context.user_data.get('wall_remaining_steps') or []
            if remaining:
                next_step = remaining[0]
                context.user_data['wall_remaining_steps'] = remaining[1:]
                await _do_wall_step_next(update, context, room_id, next_step)
                return
            # Все шаги пройдены → длина
            context.user_data['waiting_for'] = 'measure_first_dim'
            await update.message.reply_text(
                f"✅ Все ниши записаны\n\n"
                f"📏 *Длина стены* (общая, включая ниши) в СМ: __",
                parse_mode=ParseMode.MARKDOWN
            )
            return

    # Угол стены: ввод значения
    if step == 'wall_angle_value':
        method = context.user_data.get('angle_method', '60')
        angle_deg = None
        if method == '60':
            # 60-80-100: диагональ
            import math
            cos_val = (60*60 + 80*80 - val*val) / (2 * 60 * 80)
            cos_val = max(-1, min(1, cos_val))
            angle_deg = round(math.degrees(math.acos(cos_val)), 1)
        elif method == '100':
            # 100-100
            import math
            cos_val = (100*100 + 100*100 - val*val) / (2 * 100 * 100)
            cos_val = max(-1, min(1, cos_val))
            angle_deg = round(math.degrees(math.acos(cos_val)), 1)
        else:
            # напрямую градусы
            angle_deg = val

        context.user_data['angle_value'] = angle_deg
        context.user_data['wall_angle_diagonal'] = val
        context.user_data['waiting_for'] = 'measure_first_dim'

        deviation = round(abs(angle_deg - 90), 1)
        sign = '+' if angle_deg > 90 else '-'
        await update.message.reply_text(
            f"✅ Угол: *{angle_deg}°*\n"
            f"_Отклонение от прямого: {sign}{deviation}°_\n\n"
            f"Теперь размеры стены:\n"
            f"📏 Длина: __ м",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Шаг 1: первая величина (длина)
    if step == 'measure_first_dim':
        context.user_data['measure_first_value'] = val
        context.user_data['waiting_for'] = 'measure_second_dim'

        cat_info2 = {
            'wall':    ('📐 Высота стены', 'вертикаль, от пола до потолка'),
            'floor':   ('📏 Ширина пола',  'перпендикулярно длине'),
            'ceiling': ('📏 Ширина потолка','перпендикулярно длине'),
            'window':  ('📐 Высота окна',  'вертикаль'),
            'door':    ('📐 Высота двери', 'вертикаль'),
            'opening': ('📐 Высота проёма','вертикаль'),
        }
        label, hint = cat_info2.get(category, ('📏 Вторая величина', 'вертикаль'))

        await update.message.reply_text(
            f"✅ Первая: *{val} м*\n\n"
            f"*Шаг 2 из 2*\n\n"
            f"{label}: __ м\n"
            f"_({hint})_",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Шаг 2: вторая величина → создаём
    if step == 'measure_second_dim':
        first = context.user_data.get('measure_first_value')

        from core.measures import add_measure, get_measures
        existing = get_measures(room_id, category=category)

        if category == 'wall':
            pos = context.user_data.get('wall_pos') or 'напротив'
            label = f"Стена {pos}"
            av = context.user_data.get('angle_value')
            if av:
                label += f" ({av}°)"
        elif category == 'floor':
            label = 'Пол'
        elif category == 'ceiling':
            label = 'Потолок'
        elif category == 'window':
            label = f"Окно{len(existing)+1}"
        elif category == 'door':
            label = f"Дверь{len(existing)+1}"
        else:
            label = f"Элемент{len(existing)+1}"

        kwargs = {'label': label}
        if category in ('wall',):
            kwargs['length'] = first
            kwargs['height'] = val
            pos = context.user_data.get('wall_pos')
            if pos:
                kwargs['wall_pos'] = pos
            if context.user_data.get('wall_has_niche'):
                kwargs['has_rounded'] = 0  # перезапишем на 0
                kwargs['radius'] = 0
                kwargs['rounded_corner'] = 'niche'  # метка ниши
            wb = context.user_data.get('wall_bottom')
            wm = context.user_data.get('wall_middle')
            wt = context.user_data.get('wall_top')
            if wb:
                kwargs['measured_bottom'] = wb
            if wm:
                kwargs['measured_middle'] = wm
            if wt:
                kwargs['measured_top'] = wt
            if wb and wt:
                kwargs['is_wavy'] = 1 if abs(wt - wb) > 0.01 else 0
                kwargs['deviation_plus'] = round(wt - wb, 3) if wt > wb else 0
                kwargs['deviation_minus'] = round(wb - wt, 3) if wb > wt else 0
            av = context.user_data.get('angle_value')
            if av:
                kwargs['angle_value'] = av
            am = context.user_data.get('angle_method')
            if am:
                kwargs['angle_method'] = am
            ad = context.user_data.get('wall_angle_diagonal')
            if ad:
                kwargs['angle_diagonal_cm'] = ad
        elif category in ('floor', 'ceiling'):
            kwargs['length'] = first
            kwargs['width'] = val
        elif category in ('window', 'door', 'opening'):
            kwargs['length'] = first
            kwargs['height'] = val
        else:
            kwargs['length'] = first
            kwargs['width'] = val

        area = first * val

        # Для стены — СОЗДАЁМ сразу (вопрос про особенности — уже был в начале)
        if category == 'wall':
            add_measure(room_id, category, **kwargs)
            for k in ['waiting_for', 'measure_room_id', 'measure_category',
                      'measure_first_value', 'wall_pending', 'wall_pos',
                      'wall_flags', 'wall_niches', 'wall_niche_count',
                      'wall_niche_current', 'wall_niche_temp']:
                context.user_data[k] = None
            await update.message.reply_text(
                f"✅ *{label}*\n"
                f"Размер: {first} × {val} м\n"
                f"Площадь: {round(area, 2)} м²",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")]
                ])
            )
            return

        # Для остальных категорий — как было
        add_measure(room_id, category, **kwargs)

        for k in ['waiting_for', 'measure_room_id', 'measure_category',
                  'measure_first_value']:
            context.user_data[k] = None

        await update.message.reply_text(
            f"✅ *{label}* ({category})\n"
            f"Размер: {first} × {val} м\n"
            f"Площадь: {round(area, 2)} м²",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")]
            ])
        )
        return




def _room_height_scheme(step):
    """ASCII-схема комнаты с точками замеров."""
    scheme = (
        "```\n"
        "  ┌─────────────────┐\n"
        "  │                 │\n"
        "  │  1●         ●2  │  ← стены\n"
        "  │                 │\n"
        "  │       ●3        │\n"
        "  │                 │\n"
        "  │      🚪         │  ← дверь\n"
        "  └─────────────────┘\n"
        "```"
    )
    return scheme


async def _send_height_scheme(update, context, room_id, step, caption, kb_extra=None):
    """Отправляет PNG-схему + текст-подпись.
    Принимает либо Update, либо CallbackQuery.
    """
    import os
    from telegram import CallbackQuery
    # Определяем — что пришло: Update или CallbackQuery
    is_callback = isinstance(update, CallbackQuery)
    if is_callback:
        query = update
        chat = query.message.chat
    else:
        query = getattr(update, "callback_query", None)
        chat = update.effective_chat

    # Путь к схеме
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    png_path = os.path.join(base, "docs", "images", f"height_scheme_step{step}.png")
    if kb_extra:
        kb = InlineKeyboardMarkup(kb_extra)
    else:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
    if os.path.exists(png_path):
        try:
            with open(png_path, "rb") as f:
                # Удаляем старое сообщение (если из callback)
                if query:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                # Отправляем фото
                await chat.send_photo(
                    photo=f,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=kb,
                )
            return
        except Exception as e:
            print(f"⚠️ send_height_scheme: {e}")
    # Fallback — если PNG нет
    if query:
        try:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            pass
    elif hasattr(update, "message"):
        await update.message.reply_text(
            caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )


async def _show_height_step(query, context, room_id, method, step):
    """Показывает экран ввода высоты (точка 1/2/3) — с PNG-схемой."""
    # Устанавливаем состояние ожидания
    context.user_data['waiting_for'] = 'room_height_point'
    context.user_data['height_room_id'] = room_id
    context.user_data['height_step'] = step
    from telegram.constants import ParseMode as PM
    if step == 1:
        point = "📍 *Точка 1 — в ЦЕНТРЕ комнаты*"
        hint = "Встань в центр комнаты."
    elif step == 2:
        point = "📍 *Точка 2 — у ЛЕВОГО угла*"
        hint = "Перейди к левому углу (у левой стены)."
    else:
        point = "📍 *Точка 3 — у ПРАВОГО угла*"
        hint = "Перейди к правому углу (у правой стены)."
    caption = (
        f"📏 *Высота — шаг {step} из 3*\n\n"
        f"{point}\n\n"
        f"{hint}\n\n"
        f"*Как замерить:*\n"
        f"1. ⚙️ Переключи дальномер на режим *«от задней стенки»* (не от лазера!)\n"
        f"2. Приложи дальномер к полу\n"
        f"3. Наведи на потолок\n"
        f"4. Нажми кнопку — получишь цифру\n"
        f"5. Введи цифру в СМ\n\n"
        f"_Например: 270_"
    )
    # Отправляем PNG-схему с подписью
    await _send_height_scheme(query, context, room_id, step, caption)


async def reask_wall_question(update, context):
    """Если юзер прислал текст вместо кнопки — показываем кнопки заново."""
    room_id = context.user_data.get('measure_room_id')
    pos = context.user_data.get('wall_pos') or 'слева'
    if not room_id:
        return False
    await update.message.reply_text(
        f"🧱 *Стена {pos}*\n\n"
        f"Сначала выбери кнопкой:\n"
        f"— стена ровная?\n"
        f"— или есть закругление?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_angle_none_{room_id}")],
            [InlineKeyboardButton("🔄 Закругление / кривой угол", callback_data=f"wall_angle_rounded_{room_id}")],
            [InlineKeyboardButton("🕳 С нишей", callback_data=f"wall_angle_niche_{room_id}")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")]
        ])
    )
    return True



async def _show_wall_flags(query, context, room_id, pos):
    """Показывает экран с галочками особенностей стены."""
    flags = context.user_data.get('wall_flags') or {}
    f_niche = '✅' if flags.get('niche') else '⬜'
    f_rounded = '✅' if flags.get('rounded') else '⬜'
    f_wavy = '✅' if flags.get('wavy') else '⬜'
    f_hidden = '✅' if flags.get('hidden') else '⬜'
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{f_niche} С нишей", callback_data=f"wall_flag_niche_{room_id}")],
        [InlineKeyboardButton(f"{f_rounded} С закруглением", callback_data=f"wall_flag_rounded_{room_id}")],
        [InlineKeyboardButton(f"{f_wavy} Разная по высоте", callback_data=f"wall_flag_wavy_{room_id}")],
        [InlineKeyboardButton(f"{f_hidden} Скрытые коммуникации", callback_data=f"wall_flag_hidden_{room_id}")],
        [InlineKeyboardButton("✅ Готово", callback_data=f"wall_flags_done_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")]
    ])
    await query.edit_message_text(
        f"🧱 *Стена {pos}*\n\n"
        f"Отметь особенности (можно несколько):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )


async def _do_wall_step(query, context, room_id, step):
    """Обрабатывает один шаг из очереди wall_remaining_steps."""
    if step == 'niche':
        context.user_data['waiting_for'] = 'wall_niche_count'
        await query.edit_message_text(
            "🕳 *Сколько нишей на этой стене?*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1", callback_data=f"wall_niche_count_1_{room_id}")],
                [InlineKeyboardButton("2", callback_data=f"wall_niche_count_2_{room_id}")],
                [InlineKeyboardButton("3", callback_data=f"wall_niche_count_3_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")]
            ])
        )
        return
    if step == 'rounded':
        context.user_data['waiting_for'] = 'wall_rounded_radius'
        await query.edit_message_text(
            "🔄 *Закругление*\n\n"
            "📏 Радиус в СМ: __",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if step == 'wavy':
        context.user_data['waiting_for'] = 'wall_wavy_note'
        await query.edit_message_text(
            "📏 *Разная по высоте*\n\n"
            "Напиши комментарий (где больше/меньше):",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if step == 'hidden':
        context.user_data['waiting_for'] = 'wall_hidden_note'
        await query.edit_message_text(
            "🔧 *Скрытые коммуникации*\n\n"
            "Опиши что и где (трубы, кабели):",
            parse_mode=ParseMode.MARKDOWN
        )
        return



async def _do_wall_step_next(update, context, room_id, step):
    """Как _do_wall_step, но для update.message."""
    if step == 'rounded':
        context.user_data['waiting_for'] = 'wall_rounded_radius'
        await update.message.reply_text(
            "🔄 *Закругление*\n\n📏 Радиус в СМ: __",
            parse_mode=ParseMode.MARKDOWN
        )
    elif step == 'wavy':
        context.user_data['waiting_for'] = 'wall_wavy_note'
        await update.message.reply_text(
            "📏 *Разная по высоте*\n\nНапиши комментарий:",
            parse_mode=ParseMode.MARKDOWN
        )
    elif step == 'hidden':
        context.user_data['waiting_for'] = 'wall_hidden_note'
        await update.message.reply_text(
            "🔧 *Скрытые коммуникации*\n\nОпиши что и где:",
            parse_mode=ParseMode.MARKDOWN
        )


# ============================================================
# ЭТАП 3: ОБХОД СТЕН — новые функции
# ============================================================

async def _wall_send_png(query, context, room_id, step, phase, caption, kb):
    """Отправляет PNG для конкретного шага стены.
    phase: 'flags' / 'plane' / 'length' / 'angle'
    """
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    png_path = os.path.join(base, "docs", "images", f"wall_scheme_s{step}_{phase}.png")
    if os.path.exists(png_path):
        try:
            try:
                await query.message.delete()
            except Exception:
                pass
            with open(png_path, "rb") as f:
                await query.message.chat.send_photo(
                    photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
                )
            return
        except Exception as e:
            print(f"⚠️ _wall_send_png: {e}")
    # Fallback — текстом
    try:
        await query.edit_message_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        pass


async def _show_wall_step(query, context, room_id, step, phase='flags'):
    """Показывает шаг обхода стен: галочки особенностей."""
    wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
    pos = wall_names.get(step, '?')
    flags = context.user_data.get('wall_flags') or {}
    f_niche = '✅' if flags.get('niche') else '⬜'
    f_rounded = '✅' if flags.get('rounded') else '⬜'
    f_wavy = '✅' if flags.get('wavy') else '⬜'
    f_hidden = '✅' if flags.get('hidden') else '⬜'
    caption = (
        f"🧱 *Стена {step} — {pos}*\n\n"
        f"👁 *Осмотри стену визуально.*\n"
        f"Отметь, что видишь:"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{f_niche} С нишей", callback_data=f"wall_round_flag_niche_{room_id}")],
        [InlineKeyboardButton(f"{f_rounded} С закруглением", callback_data=f"wall_round_flag_rounded_{room_id}")],
        [InlineKeyboardButton(f"{f_wavy} Разная по высоте", callback_data=f"wall_round_flag_wavy_{room_id}")],
        [InlineKeyboardButton(f"{f_hidden} Скрытые коммуникации", callback_data=f"wall_round_flag_hidden_{room_id}")],
        [InlineKeyboardButton("➡️ Дальше (к длине)", callback_data=f"wall_round_flags_done_{room_id}")],
        [InlineKeyboardButton("⏭ Пропустить стену", callback_data=f"wall_round_skip_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    await _wall_send_png(query, context, room_id, step, 'flags', caption, kb)


async def _show_wall_plane(query, context, room_id, step):
    """Показывает экран «плоскость стены» с PNG."""
    caption = (
        f"🧱 *Стена {step}*\n\n"
        f"📐 *Плоскость стены:*\n\n"
        f"Встань и посмотри на стену — она ровная или кривая по высоте?\n\n"
        f"_Стрелка на схеме показывает, что смотреть._"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_round_plane_straight_{room_id}")],
        [InlineKeyboardButton("📏 Разная (3 точки)", callback_data=f"wall_round_plane_wavy_{room_id}")],
    ])
    await _wall_send_png(query, context, room_id, step, 'plane', caption, kb)


async def _show_wall_length(query, context, room_id, step):
    """Показывает экран «длина стены» с PNG."""
    caption = (
        f"🧱 *Стена {step}*\n\n"
        f"📏 *Длина стены (СМ):*\n\n"
        f"Замерь длину этой стены.\n"
        f"_Красная линия на схеме показывает, что мерить._\n\n"
        f"Напиши число и отправь."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    await _wall_send_png(query, context, room_id, step, 'length', caption, kb)


async def _show_wall_angle(query, context, room_id, step):
    """Показывает экран «угол стены» с PNG."""
    caption = (
        f"🧱 *Стена {step}*\n\n"
        f"📐 *Угол между этой стеной и следующей:*\n\n"
        f"Обычно 90° — прямой угол.\n"
        f"_Кружок на схеме показывает, какой угол мерить._"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 90° (прямой)", callback_data=f"wall_round_angle_90_{room_id}")],
        [InlineKeyboardButton("📏 60-80-100 (рулетка)", callback_data=f"wall_round_angle_60_{room_id}")],
        [InlineKeyboardButton("📏 100-100 (рулетка)", callback_data=f"wall_round_angle_100_{room_id}")],
        [InlineKeyboardButton("✏️ Угол в градусах", callback_data=f"wall_round_angle_deg_{room_id}")],
    ])
    await _wall_send_png(query, context, room_id, step, 'angle', caption, kb)


async def _wall_save_and_next(update_or_query, context, room_id, step):
    """Сохраняет текущую стену и переходит к следующей."""
    from core.measures import add_measure, complete_walls_round
    from telegram import CallbackQuery, Update

    wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
    pos = wall_names.get(step, '?')
    length = context.user_data.get('wall_length') or 0
    angle = context.user_data.get('wall_angle_value') or 90
    angle_method = context.user_data.get('wall_angle_method') or '90'
    plane = context.user_data.get('wall_plane') or 'straight'
    flags = context.user_data.get('wall_flags') or {}

    note_parts = []
    if flags.get('niche'): note_parts.append('Ниша')
    if flags.get('rounded'): note_parts.append('Закругление')
    if flags.get('wavy'): note_parts.append('Разная по высоте')
    if flags.get('hidden'): note_parts.append('Скрытые коммуникации')
    note = '; '.join(note_parts) if note_parts else None

    kwargs = {
        'label': f'Стена {pos}', 'wall_pos': pos, 'length': length,
        'unit': 'см', 'order_num': step,
        'angle_value': angle, 'angle_method': angle_method,
    }
    if plane == 'wavy':
        kwargs['measured_bottom'] = context.user_data.get('wall_bottom')
        kwargs['measured_middle'] = context.user_data.get('wall_middle')
        kwargs['measured_top'] = context.user_data.get('wall_top')
        b = kwargs.get('measured_bottom') or 0
        t = kwargs.get('measured_top') or 0
        kwargs['is_wavy'] = 1 if abs(t - b) > 0.5 else 0
    if flags.get('rounded'): kwargs['has_rounded'] = 1
    if flags.get('hidden'):
        kwargs['has_hidden'] = 1
        kwargs['hidden_note'] = note
    if note: kwargs['note'] = note

    add_measure(room_id, 'wall', **kwargs)

    for k in ['wall_length', 'wall_angle_value', 'wall_angle_method',
              'wall_angle_diagonal', 'wall_plane', 'wall_bottom',
              'wall_middle', 'wall_top']:
        context.user_data[k] = None
    context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}

    summary = f"✅ *Стена {step} ({pos}) сохранена!*\n\n"
    summary += f"📏 Длина: {length} см\n"
    summary += f"📐 Угол: {angle}°\n"

    if step >= 4:
        complete_walls_round(room_id)
        await _wall_finish(update_or_query, context, room_id, summary)
        return

    next_step = step + 1
    context.user_data['wall_step'] = next_step
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"➡️ Стена {next_step}", callback_data=f"wall_round_start_{room_id}")],
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
    ])
    # Всегда удаляем старое сообщение (если фото) и отправляем новое
    try:
        if isinstance(update_or_query, CallbackQuery):
            try:
                await update_or_query.message.delete()
            except Exception:
                pass
            await update_or_query.message.chat.send_message(
                summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        elif isinstance(update_or_query, Update):
            await update_or_query.message.reply_text(
                summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
    except Exception as e:
        print(f"⚠️ _wall_save_and_next: {e}")


async def _wall_finish(update_or_query, context, room_id, summary_prefix=''):
    """Финал обхода стен — с генерацией контура."""
    from core.measures import get_walls_ordered, calculate_room_areas
    from core.rooms import get_room
    from telegram import CallbackQuery, Update
    import os

    walls = get_walls_ordered(room_id)
    room = get_room(room_id)
    total_length = sum((w['length'] if w['length'] else 0) for w in walls)
    areas = calculate_room_areas(room_id)

    text = summary_prefix
    text += f"\n🎉 *Все 4 стены замерены!*\n\n"
    text += f"📊 *Итог комнаты «{room['name'] if room else '?'}»:*\n"
    text += f"• Стены: {len(walls)} шт.\n"
    if areas.get('walls_net') is not None:
        text += f"• Площадь стен: {areas['walls_net']} м²\n"
    if areas.get('floor'):
        text += f"• Площадь пола: {areas['floor']} м²\n"

    # Генерируем контур
    png_path = None
    try:
        from scripts.draw_room_scheme import draw_room_final
        png_path, info = draw_room_final(room_id, room_name=room['name'] if room else 'Комната')
        if png_path and os.path.exists(png_path):
            text += f"\n📐 Контур: расхождение {info['gap_percent']}%\n"
            if info['closed']:
                text += f"✅ Контур замкнут\n"
            else:
                text += f"⚠️ Не замкнут (>5%)\n"
    except Exception as e:
        print(f"⚠️ draw_room_final: {e}")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
        [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
    ])

    try:
        if isinstance(update_or_query, CallbackQuery):
            try:
                await update_or_query.message.delete()
            except Exception:
                pass
            if png_path and os.path.exists(png_path):
                with open(png_path, "rb") as f:
                    await update_or_query.message.chat.send_photo(
                        photo=f, caption=text,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
                    )
            else:
                await update_or_query.message.chat.send_message(
                    text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
        elif isinstance(update_or_query, Update):
            if png_path and os.path.exists(png_path):
                with open(png_path, "rb") as f:
                    await update_or_query.message.reply_photo(
                        photo=f, caption=text,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
                    )
            else:
                await update_or_query.message.reply_text(
                    text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
    except Exception as e:
        print(f"⚠️ _wall_finish: {e}")



async def _handle_wall_round_input(update, context, step):
    """Обработка ввода wall_round_* — вынесена из handle_measure_input."""
    room_id = context.user_data.get('wall_room_id')

    if step == 'wall_round_length':
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната (wall_round). Начни заново: карточка → Обход стен")
            return
        try:
            length_cm = int(float((update.message.text or '').replace(',', '.')))
        except ValueError:
            await update.message.reply_text("❌ Нужно число. Например: `365`", parse_mode=ParseMode.MARKDOWN)
            return
        if length_cm <= 0 or length_cm > 5000:
            await update.message.reply_text("❌ Длина от 1 до 5000 см")
            return
        context.user_data['wall_length'] = length_cm
        context.user_data['waiting_for'] = None
        step_num = context.user_data.get('wall_step') or 1
        # Сразу экран УГЛА с PNG
        import os
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        png_path = os.path.join(base, "docs", "images", f"wall_scheme_s{step_num}_angle.png")
        caption = (
            f"✅ Длина: *{length_cm} см*\n\n"
            f"📐 *Теперь угол между этой стеной и следующей:*\n\n"
            f"Обычно 90° — прямой угол.\n"
            f"_Кружок на схеме показывает, какой угол мерить._"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📐 90° (прямой)", callback_data=f"wall_round_angle_90_{room_id}")],
            [InlineKeyboardButton("📏 60-80-100 (рулетка)", callback_data=f"wall_round_angle_60_{room_id}")],
            [InlineKeyboardButton("📏 100-100 (рулетка)", callback_data=f"wall_round_angle_100_{room_id}")],
            [InlineKeyboardButton("✏️ Угол в градусах", callback_data=f"wall_round_angle_deg_{room_id}")],
        ])
        if os.path.exists(png_path):
            try:
                with open(png_path, "rb") as f:
                    await update.message.chat.send_photo(
                        photo=f, caption=caption,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
                    )
                return
            except Exception as e:
                print(f"⚠️ send_photo angle: {e}")
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return

    if step == 'wall_round_angle_val':
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната")
            return
        method = context.user_data.get('wall_angle_method')
        try:
            val = float((update.message.text or '').replace(',', '.'))
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        import math
        if method == '60':
            cos_val = (60*60 + 80*80 - val*val) / (2 * 60 * 80)
            cos_val = max(-1, min(1, cos_val))
            angle_deg = round(math.degrees(math.acos(cos_val)), 1)
        elif method == '100':
            cos_val = (100*100 + 100*100 - val*val) / (2 * 100 * 100)
            cos_val = max(-1, min(1, cos_val))
            angle_deg = round(math.degrees(math.acos(cos_val)), 1)
        else:
            angle_deg = val
        context.user_data['wall_angle_value'] = angle_deg
        await update.message.reply_text(
            f"✅ Угол: *{angle_deg}°*\n\n"
            f"📐 *Плоскость стены:*\n\nСтена ровная или кривая по высоте?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_round_plane_straight_{room_id}")],
                [InlineKeyboardButton("📏 Разная (3 точки)", callback_data=f"wall_round_plane_wavy_{room_id}")],
            ])
        )
        context.user_data['waiting_for'] = None
        return

    if step == 'wall_round_plane_bottom':
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната")
            return
        try:
            val = float((update.message.text or '').replace(',', '.'))
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        context.user_data['wall_bottom'] = val
        context.user_data['waiting_for'] = 'wall_round_plane_middle'
        await update.message.reply_text(
            f"✅ Низ: *{val} см*\n\n📏 *Замер по центру:*\nВведи в СМ:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if step == 'wall_round_plane_middle':
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната")
            return
        try:
            val = float((update.message.text or '').replace(',', '.'))
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        context.user_data['wall_middle'] = val
        context.user_data['waiting_for'] = 'wall_round_plane_top'
        await update.message.reply_text(
            f"✅ Центр: *{val} см*\n\n📏 *Замер вверху:*\nВведи в СМ:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if step == 'wall_round_plane_top':
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната")
            return
        try:
            val = float((update.message.text or '').replace(',', '.'))
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        context.user_data['wall_top'] = val
        context.user_data['waiting_for'] = 'wall_round_length'
        step_num = context.user_data.get('wall_step') or 1
        b = context.user_data.get('wall_bottom') or 0
        m = context.user_data.get('wall_middle') or 0
        t = val
        dev = round(max(b, m, t) - min(b, m, t), 1)
        # Показываем PNG длины
        import os
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        png_path = os.path.join(base, "docs", "images", f"wall_scheme_s{step_num}_length.png")
        caption = (
            f"✅ *Плоскость замерена*\n"
            f"Низ/Центр/Верх: {b}/{m}/{t} см\n"
            f"Отклонение: {dev} см\n\n"
            f"📏 *Теперь длина этой стены (СМ):*\n\n"
            f"Напиши число и отправь."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        if os.path.exists(png_path):
            try:
                with open(png_path, "rb") as f:
                    await update.message.chat.send_photo(
                        photo=f, caption=caption,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb,
                    )
                return
            except Exception as e:
                print(f"⚠️ send_photo length: {e}")
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return


async def _handle_opening_input(update, context, step):
    """Обработка ввода для проёмов."""
    room_id = context.user_data.get('opening_room_id')
    if not room_id:
        await update.message.reply_text("❌ Потерялась комната. Начни заново: карточка → Проёмы")
        context.user_data['waiting_for'] = None
        return

    try:
        val = int(float((update.message.text or '').replace(',', '.')))
    except ValueError:
        await update.message.reply_text("❌ Нужно число", parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'opening_width':
        if val <= 0 or val > 2000:
            await update.message.reply_text("❌ Ширина от 1 до 2000 см")
            return
        context.user_data['opening_width'] = val
        context.user_data['waiting_for'] = 'opening_height'
        await update.message.reply_text(
            f"🪟 *Проём*\n"
            f"📏 Ширина: *{val} см*\n"
            f"📏 Высота: *?*\n\n"
            f"*Замерь высоту (СМ):*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Изменить ширину", callback_data=f"opening_back_width_{room_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data=f"opening_cancel_{room_id}")],
            ])
        )
        return

    if step == 'opening_height':
        if val <= 0 or val > 2000:
            await update.message.reply_text("❌ Высота от 1 до 2000 см")
            return
        context.user_data['opening_height'] = val
        otype = context.user_data.get('opening_type')
        if otype == 'window':
            # Для окна — спрашиваем подоконник
            context.user_data['waiting_for'] = 'opening_sill'
            await update.message.reply_text(
                f"✅ Высота: *{val} см*\n\n"
                f"📏 *Высота подоконника* (СМ):\n\n"
                f"_Это расстояние от пола до нижнего края окна._\n"
                f"_Напиши число и отправь._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_cancel_{room_id}")],
                ])
            )
        else:
            # Для двери / вентиляции — сразу к offset
            context.user_data['waiting_for'] = 'opening_offset'
            await update.message.reply_text(
                f"✅ Высота: *{val} см*\n\n"
                f"📐 *Смещение от левого угла стены* (СМ):\n\n"
                f"_Если ровно в углу — напиши 0._\n"
                f"_Если по центру — примерно половину длины стены._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_cancel_{room_id}")],
                ])
            )
        return

    if step == 'opening_sill':
        context.user_data['opening_sill'] = val
        context.user_data['waiting_for'] = 'opening_offset'
        await update.message.reply_text(
            f"✅ Подоконник: *{val} см*\n\n"
            f"📐 *Смещение от левого угла стены* (СМ):\n\n"
            f"_Если ровно в углу — напиши 0._\n"
            f"_Если по центру — примерно половину длины стены._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_cancel_{room_id}")],
            ])
        )
        return

    if step == 'opening_offset':
        context.user_data['opening_offset_x'] = val
        await _opening_save(update, context)
        return

    if step == 'opening_edit_value':
        opening_id = context.user_data.get('opening_edit_id')
        field = context.user_data.get('opening_edit_field')
        if not opening_id or not field:
            await update.message.reply_text("❌ Данные потерялись")
            context.user_data['waiting_for'] = None
            return
        from core.measures import update_opening
        if field == 'width':
            update_opening(opening_id, width=val)
        elif field == 'height':
            update_opening(opening_id, height=val)
        elif field == 'sill':
            update_opening(opening_id, sill_height=val)
        elif field == 'offset':
            update_opening(opening_id, offset_x=val)
        context.user_data['opening_edit_id'] = None
        context.user_data['opening_edit_field'] = None
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"✅ Обновлено: {field} = {val} см",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К проёму", callback_data=f"opening_show_{opening_id}")],
            ])
        )
        return

async def _opening_save(update, context):
    """Сохраняет проём и возвращает к списку."""
    from core.measures import add_opening, OPENING_TYPES
    room_id = context.user_data.get('opening_room_id')
    otype = context.user_data.get('opening_type')
    wall_pos = context.user_data.get('opening_wall_pos')
    width = context.user_data.get('opening_width')
    height = context.user_data.get('opening_height')
    sill = context.user_data.get('opening_sill')

    if not all([room_id, otype, wall_pos, width, height]):
        await update.message.reply_text("❌ Данные потерялись. Начни заново.")
        return

    offset_x = context.user_data.get('opening_offset_x') or 0

    opening_id = add_opening(
        room_id=room_id,
        opening_type=otype,
        wall_pos=wall_pos,
        offset_x=offset_x,
        width=width,
        height=height,
        sill_height=sill,
        created_by=update.effective_user.id
    )

    # Очищаем
    for k in ['opening_room_id', 'opening_type', 'opening_wall_pos',
              'opening_width', 'opening_height', 'opening_sill',
              'opening_offset_x']:
        context.user_data[k] = None
    context.user_data['waiting_for'] = None

    label = OPENING_TYPES.get(otype, otype)
    text = (
        f"✅ *Проём добавлен!*\n\n"
        f"{label} на стене «{wall_pos}»\n"
        f"📏 {width} × {height} см"
    )
    if sill:
        text += f"\n📏 Подоконник: {sill} см"
    if offset_x:
        text += f"\n📐 Смещение: {offset_x} см от угла"

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить ещё", callback_data=f"opening_add_{room_id}")],
            [InlineKeyboardButton("🚪 К проёмам", callback_data=f"openings_list_{room_id}")],
            [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
        ])
    )
