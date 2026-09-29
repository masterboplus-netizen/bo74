"""interfaces.telegram.rooms — UI комнат в Telegram."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room, create_room, delete_room
from core.rooms_ui import format_room_card, format_rooms_list
from core.measures import get_measures, calculate_room_areas, format_measure
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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Задачи", callback_data=f"room_tasks_{room_id}")],
        [InlineKeyboardButton("📐 Размеры", callback_data=f"room_measures_{room_id}"),
         InlineKeyboardButton("🔧 Коммуникации", callback_data=f"room_comms_{room_id}")],
        [InlineKeyboardButton("🪑 Мебель/техника", callback_data=f"room_objects_{room_id}")],
        [InlineKeyboardButton("📸 Фото", callback_data=f"room_photos_{room_id}")],
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
    """Показывает карточку комнаты."""
    room = get_room(room_id)
    if not room:
        await update.callback_query.edit_message_text("❌ Комната не найдена")
        return
    text = format_room_card(room_id)
    kb = room_card_keyboard(room_id)
    await update.callback_query.edit_message_text(
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
                     "room_conflicts_", "room_forecast_", "room_type_")
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

    # Выбор типа помещения → создание
    if data.startswith("room_type_"):
        parts = data.replace("room_type_", "").split("_", 1)
        object_id = int(parts[0])
        room_type = parts[1]
        name = context.user_data.get('room_name_pending') or 'Комната'
        new_room_id = create_room(object_id, name, room_type=room_type)
        if new_room_id:
            context.user_data['room_name_pending'] = None
            context.user_data['waiting_for'] = None
            await show_rooms_list(update, context, object_id)
        else:
            await query.edit_message_text("❌ Не удалось создать комнату")
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
            lines.append(format_measure(m))
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

        # Для стен — сначала спрашиваем позицию
        if category == 'wall':
            positions = [
                ('напротив', '⬆️ Напротив (перед тобой)'),
                ('слева', '⬅️ Слева'),
                ('справа', '➡️ Справа'),
                ('у входа', '⬇️ У входа (за спиной)'),
                ('слева дальняя', '↖️ Слева дальняя'),
                ('справа дальняя', '↗️ Справа дальняя'),
            ]
            buttons = [[InlineKeyboardButton(label, callback_data=f"wall_pos_{room_id}_{code}")]
                       for code, label in positions]
            buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")])
            await query.edit_message_text(
                f"🧱 *Новая стена*\n\n"
                f"Встань в дверном проёме, лицом в комнату.\n"
                f"Где эта стена?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
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

    # Назад к списку объектов (если комнату не нашли)
    if data.startswith("rooms_list_obj_"):
        object_id = int(data.replace("rooms_list_obj_", ""))
        await show_rooms_list(update, context, object_id)
        return



async def handle_measure_input(update, context):
    """Пошаговый ввод: 1) длина, 2) высота/ширина."""
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
            "🔄 *Закругление*\\n\\n"
            "📏 Радиус в СМ: __",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if step == 'wavy':
        context.user_data['waiting_for'] = 'wall_wavy_note'
        await query.edit_message_text(
            "📏 *Разная по высоте*\\n\\n"
            "Напиши комментарий (где больше/меньше):",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if step == 'hidden':
        context.user_data['waiting_for'] = 'wall_hidden_note'
        await query.edit_message_text(
            "🔧 *Скрытые коммуникации*\\n\\n"
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
