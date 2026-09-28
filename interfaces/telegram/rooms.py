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

    # Карточка комнаты
    if data.startswith("room_") and not data.startswith(("room_add_", "room_del_", "room_tasks_", "room_measures_", "room_comms_", "room_objects_", "room_photos_")):
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
