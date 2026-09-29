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
    print(f"🔍 handle_rooms_callback: data={data!r}")

    # Карточка комнаты
    _room_exclude = ("room_add_", "room_del_", "room_delok_",
                     "room_tasks_", "room_measures_", "room_measure_add_", "room_measure_cat_",
                     "room_comms_", "room_objects_", "room_photos_",
                     "room_conflicts_", "room_forecast_")
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
                "📐 Размеров пока нет.",
                reply_markup=InlineKeyboardMarkup([
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
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_measures_{room_id}")])
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
            buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_measures_{room_id}")])
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
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_measures_{room_id}")]
            ])
        )
        return

    # Позиция стены → спрашиваем про угол
    if data.startswith("wall_pos_"):
        parts = data.replace("wall_pos_", "").split("_", 1)
        room_id = int(parts[0])
        pos = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['measure_room_id'] = room_id
        context.user_data['measure_category'] = 'wall'
        context.user_data['wall_pos'] = pos
        await query.edit_message_text(
            f"🧱 *Стена {pos}*\n\n"
            f"Стена ровная или есть закругление?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_angle_none_{room_id}")],
                [InlineKeyboardButton("🔄 Закругление / кривой угол", callback_data=f"wall_angle_rounded_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_measures_{room_id}")]
            ])
        )
        return

    # Ровная → сразу длина
    if data.startswith("wall_angle_none_"):
        room_id = int(data.replace("wall_angle_none_", ""))
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
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_measures_{room_id}")]
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


