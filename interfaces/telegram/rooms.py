"""interfaces.telegram.rooms — UI комнат в Telegram (v2, чистый)."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room, create_room, delete_room, update_room
from core.rooms_ui import format_room_card, format_rooms_list
from core.measures import (
    get_measures, calculate_room_areas, format_measure, get_walls_ordered,
    add_measure, add_niche, add_opening, delete_measure,
    start_walls_round, complete_walls_round, get_walls_progress,
    get_openings_by_wall, format_opening, OPENING_TYPES,
    get_openings, get_opening, update_opening, delete_opening,
)
from core.comms import (
    get_comms, format_comm, get_comm_type_label, get_comm,
    add_comm, update_comm, delete_comm, COMM_TYPES,
)
from core.room_objects import get_room_objects, format_room_object


def rooms_list_keyboard(object_id):
    rooms = get_rooms(object_id)
    buttons = []
    for r in rooms:
        mark = "🏠" if r.get('is_default') else "📦"
        buttons.append([InlineKeyboardButton(f"{mark} {r['name']}", callback_data=f"room_{r['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить комнату", callback_data=f"room_add_{object_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")])
    return InlineKeyboardMarkup(buttons)


def room_card_keyboard(room_id):
    room = get_room(room_id)
    object_id = room['object_id'] if room else 0
    walls = get_walls_ordered(room_id)
    height_ok = bool(room.get('height_bottom') and room.get('height_middle') and room.get('height_top'))
    walls_ok = len(walls) >= 4

    if not height_ok and not walls:
        start_btn = InlineKeyboardButton("🚀 Начать замер", callback_data=f"room_start_{room_id}")
    elif height_ok and walls_ok:
        start_btn = InlineKeyboardButton("✅ Замер завершён", callback_data=f"room_start_{room_id}")
    else:
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
        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"room_rename_{room_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"room_del_{room_id}")],
        [InlineKeyboardButton("⬅️ К комнатам", callback_data=f"rooms_list_obj_{object_id}")],
    ])


async def show_rooms_list(update, context, object_id):
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else '—'
    text = f"📦 *Комнаты «{obj_name}»*\n\n{format_rooms_list(object_id)}"
    kb = rooms_list_keyboard(object_id)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def show_room_card(update, context, room_id):
    room = get_room(room_id)
    if not room:
        await update.callback_query.edit_message_text("❌ Комната не найдена")
        return
    text = format_room_card(room_id)
    kb = room_card_keyboard(room_id)
    query = update.callback_query
    has_photo = bool(getattr(query.message, "photo", None))
    if has_photo:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    else:
        try:
            await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            if "message is not modified" not in str(e).lower():
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await query.message.chat.send_message(text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def handle_rooms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер всех callback'ов комнат."""
    query = update.callback_query
    await query.answer()
    data = query.data
    print(f"🔍 ROOMS: data={data!r}", flush=True)

    # obj_* — редактирование/удаление объектов
    if data.startswith("obj_del_") or data.startswith("obj_delok_") or data.startswith("obj_rename_"):
        handled = await handle_object_callback(update, context, data)
        if handled:
            return

    # room_rename_<id>
    if data.startswith("room_rename_"):
        room_id = int(data.replace("room_rename_", ""))
        context.user_data['waiting_for'] = 'room_rename'
        context.user_data['room_rename_id'] = room_id
        await query.edit_message_text(
            "✏️ *Новое имя комнаты:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
        )
        return

    # obj_<id> — открыть карточку объекта
    if data.startswith("obj_") and not (data.startswith("obj_del_") or data.startswith("obj_delok_") or data.startswith("obj_rename_")):
        try:
            object_id = int(data.replace("obj_", ""))
        except ValueError:
            return
        from modules.objects import get_object
        from handlers.commands import object_detail_keyboard
        obj = get_object(object_id)
        if not obj:
            await query.edit_message_text("❌ Объект не найден")
            return
        text = (
            f"🏗️ *{obj['name']}*\n\n"
            f"📍 {obj.get('address') or '—'}\n"
            f"📊 Статус: {obj.get('status') or '—'}"
        )
        try:
            kb = object_detail_keyboard(object_id)
        except Exception as e:
            print(f"⚠️ object_detail_keyboard: {e}", flush=True)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К объектам", callback_data="menu_objects")]])
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return

    _room_exclude = ("room_add_", "room_del_", "room_delok_",
                     "room_tasks_", "room_measures_", "room_measure_add_", "room_measure_cat_",
                     "room_comms_", "room_objects_", "room_photos_",
                     "room_conflicts_", "room_forecast_", "room_type_",
                     "room_method_", "room_height_", "room_start_", "room_progress_",
                     "comm_")
    if data.startswith("room_") and not data.startswith(_room_exclude):
        try:
            room_id = int(data.replace("room_", ""))
        except ValueError:
            return
        await show_room_card(update, context, room_id)
        return

    if data.startswith("room_add_"):
        object_id = int(data.replace("room_add_", ""))
        context.user_data['waiting_for'] = 'room_name'
        context.user_data['room_object_id'] = object_id
        await query.edit_message_text(
            f"📦 *Новая комната*\n\nНапиши название:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"rooms_list_obj_{object_id}")]
            ])
        )
        return

    if data.startswith("room_type_"):
        parts = data.replace("room_type_", "").split("_", 1)
        object_id = int(parts[0])
        room_type = parts[1]
        name = context.user_data.get('room_name_pending') or 'Комната'
        new_room_id = create_room(object_id, name, room_type=room_type)
        if new_room_id:
            context.user_data['room_name_pending'] = None
            context.user_data['waiting_for'] = None
            await show_room_card(update, context, new_room_id)
        else:
            await query.edit_message_text("❌ Не удалось создать комнату")
        return

    if data.startswith("room_height_ask_"):
        room_id = int(data.replace("room_height_ask_", ""))
        context.user_data['height_room_id'] = room_id
        await query.edit_message_text(
            f"📏 *Высота потолка*\n\nВысота одинаковая во всей комнате\nили отличается в разных точках?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Одинаковая (1 замер)", callback_data=f"room_height_same_start_{room_id}")],
                [InlineKeyboardButton("📏 Разная (3 замера)", callback_data=f"room_height_three_start_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
        )
        return

    if data.startswith("room_height_same_start_"):
        room_id = int(data.replace("room_height_same_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_mode'] = 'same'
        context.user_data['waiting_for'] = 'room_height_same'
        try:
            await query.message.delete()
        except Exception:
            pass
        import os as _os
        _base = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        _png = _os.path.join(_base, "docs", "images", "height_scheme_step1.png")
        _caption = (
            "📏 *Высота потолка*\n\n"
            "Введи ОДНУ цифру в СМ — она применится ко всем точкам:\n\n"
            "_Например: 305_"
        )
        if _os.path.exists(_png):
            try:
                with open(_png, "rb") as f:
                    await query.message.chat.send_photo(
                        photo=f, caption=_caption, parse_mode=ParseMode.MARKDOWN
                    )
                return
            except Exception:
                pass
        await query.message.chat.send_message(_caption, parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("room_height_three_start_"):
        room_id = int(data.replace("room_height_three_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        context.user_data['height_mode'] = 'three'
        await _show_height_step(query, context, room_id, step=1)
        return

    if data.startswith("room_progress_"):
        room_id = int(data.replace("room_progress_", ""))
        room = get_room(room_id)
        if not room:
            await query.edit_message_text("❌ Комната не найдена")
            return
        walls = get_walls_ordered(room_id)
        h_bottom = room.get('height_bottom')
        h_avg = room.get('height')
        height_ok = bool(h_bottom and room.get('height_middle') and room.get('height_top'))
        walls_ok = len(walls) >= 4

        from core.db import fetchone
        try:
            r = fetchone("SELECT COUNT(*) as cnt FROM openings WHERE room_id = ?", (room_id,))
            openings_count = r['cnt'] if r else 0
        except Exception:
            openings_count = 0
        try:
            r = fetchone("SELECT COUNT(*) as cnt FROM room_comms WHERE room_id = ?", (room_id,))
            comms_count = r['cnt'] if r else 0
        except Exception:
            comms_count = 0

        text = f"👁 *Что замерено в комнате «{room['name']}»*\n\n"
        if height_ok:
            text += f"📏 Высота: ✅ {int(h_avg) if h_avg == int(h_avg) else round(h_avg, 1)} см\n"
        elif h_bottom:
            text += f"📏 Высота: ⚠️ частично\n"
        else:
            text += f"📏 Высота: ❌ не замерена\n"
        if walls_ok:
            text += f"🧱 Стены: ✅ {len(walls)} шт.\n"
        elif walls:
            text += f"🧱 Стены: ⚠️ {len(walls)} из 4\n"
        else:
            text += f"🧱 Стены: ❌ не замерены\n"
        text += f"🚪 Проёмы: {'✅ ' + str(openings_count) + ' шт.' if openings_count > 0 else '❌ не замерены'}\n"
        text += f"🔧 Коммуникации: {'✅ ' + str(comms_count) + ' шт.' if comms_count > 0 else '❌ не замерены'}\n"
        text += "\n*Что дальше?*"

        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Продолжить замер", callback_data=f"room_start_{room_id}")],
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    if data.startswith("room_start_"):
        room_id = int(data.replace("room_start_", ""))
        room = get_room(room_id)
        if not room:
            await query.edit_message_text("❌ Комната не найдена")
            return
        h_bottom = room.get('height_bottom')
        h_middle = room.get('height_middle')
        h_top = room.get('height_top')
        height_ok = bool(h_bottom and h_middle and h_top)
        walls = get_walls_ordered(room_id)
        walls_ok = len(walls) >= 4

        if not height_ok:
            if h_bottom and not (h_middle and h_top):
                context.user_data['height_room_id'] = room_id
                context.user_data['height_step'] = 2 if not h_middle else 3
                context.user_data['height_bottom'] = h_bottom
                context.user_data['height_middle'] = h_middle
                context.user_data['height_top'] = h_top
                context.user_data['waiting_for'] = 'room_height_point'
                await query.edit_message_text(
                    f"🚀 *Продолжаем замер*\n\n📏 Шаг 1: Высота\n✅ Точка 1 (центр): {h_bottom} см",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Продолжить", callback_data=f"room_height_continue_{room_id}")],
                        [InlineKeyboardButton("🔄 Заново", callback_data=f"room_height_ask_{room_id}")],
                    ])
                )
                return
            else:
                context.user_data['height_room_id'] = room_id
                context.user_data['height_step'] = 1
                context.user_data['height_bottom'] = None
                context.user_data['height_middle'] = None
                context.user_data['height_top'] = None
                context.user_data['waiting_for'] = 'room_height_point'
                await query.edit_message_text(
                    f"🚀 *Мастер замеров*\n\n📏 *Шаг 1 из 3: Высота потолка*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Начать", callback_data=f"room_height_ask_{room_id}")],
                        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                    ])
                )
                return

        if not walls_ok:
            context.user_data['wall_room_id'] = room_id
            context.user_data['wall_step'] = 1
            context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
            start_walls_round(room_id)
            await _show_wall_step(query, context, room_id, 1, phase='flags')
            return

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
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("🔄 Замер заново", callback_data=f"wall_round_reset_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

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
            context.user_data['height_step'] = 2
            await _show_height_step(query, context, room_id, step=2)
        elif h_bottom and h_middle:
            context.user_data['height_step'] = 3
            await _show_height_step(query, context, room_id, step=3)
        else:
            await _show_height_step(query, context, room_id, step=1)
        return

    if data.startswith("room_method_"):
        parts = data.replace("room_method_", "").split("_", 1)
        room_id = int(parts[0])
        method = parts[1]
        update_room(room_id, measure_method=method)
        await _show_height_step(query, context, room_id, method=method, step=1)
        return

    if data.startswith("room_height_same_"):
        room_id = int(data.replace("room_height_same_", ""))
        center = context.user_data.get('height_bottom') or 0
        if not center:
            context.user_data['height_room_id'] = room_id
            context.user_data['waiting_for'] = 'room_height_same'
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(
                "📏 *Высота потолка*\n\nВведи одну цифру в СМ:",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        update_room(room_id, height=center, height_bottom=center, height_middle=center, height_top=center)
        for k in ['waiting_for', 'height_room_id', 'height_step',
                  'height_bottom', 'height_middle', 'height_top']:
            context.user_data[k] = None
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            f"✅ *Высота: {center} см*\n\n📐 Теперь обход стен.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 Начать обход", callback_data=f"wall_round_start_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    if data.startswith("room_del_"):
        room_id = int(data.replace("room_del_", ""))
        room = get_room(room_id)
        if not room:
            await query.edit_message_text("❌ Комната не найдена")
            return
        await query.edit_message_text(
            f"🗑 *Удалить «{room['name']}»?*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"room_delok_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
        )
        return

    if data.startswith("room_delok_"):
        room_id = int(data.replace("room_delok_", ""))
        room = get_room(room_id)
        if room:
            object_id = room['object_id']
            delete_room(room_id)
            await show_rooms_list(update, context, object_id)
        return

    if data.startswith("room_tasks_"):
        room_id = int(data.replace("room_tasks_", ""))
        await query.edit_message_text(
            "📋 Задачи комнаты — в разработке.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return

    if data.startswith("room_photos_"):
        room_id = int(data.replace("room_photos_", ""))
        await query.edit_message_text(
            "📸 Фото комнаты — в разработке.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return

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
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return

    if data.startswith("room_measures_"):
        room_id = int(data.replace("room_measures_", ""))
        measures = get_measures(room_id)
        if not measures:
            await query.edit_message_text(
                "📐 Размеров пока нет.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
            return
        lines = [f"📐 *Размеры комнаты* ({len(measures)}):\n"]
        for m in measures:
            lines.append(format_measure(m, show_area=True))
        areas = calculate_room_areas(room_id)
        lines.append("")
        lines.append(f"Стены: {areas['walls_net']} м²")
        lines.append(f"Пол: {areas['floor']} м²")
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
        return


    # ============ КОММУНИКАЦИИ ============
    if data.startswith("room_comms_"):
        room_id = int(data.replace("room_comms_", ""))
        comms = get_comms(room_id)
        room = get_room(room_id)
        room_name = room['name'] if room else '?'
        text = f"🔧 *Коммуникации в «{room_name}»*\n\n"
        if not comms:
            text += "_Пока ничего не добавлено._\n\nДобавь воду, канализацию, электрику, газ, вентиляцию."
        else:
            text += f"Найдено: {len(comms)}\n\n"
            for i, c in enumerate(comms, 1):
                text += f"{i}. {format_comm(c)}\n"
        buttons = []
        for c in comms:
            label = get_comm_type_label(c.get('comm_type'))
            wall = c.get('wall') or '?'
            buttons.append([InlineKeyboardButton(f"{label} ({wall})", callback_data=f"comm_show_{c['id']}")])
        buttons.append([InlineKeyboardButton("➕ Добавить", callback_data=f"comm_add_{room_id}")])
        buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("comm_add_"):
        room_id = int(data.replace("comm_add_", ""))
        buttons = []
        for code, label, _ in COMM_TYPES:
            buttons.append([InlineKeyboardButton(label, callback_data=f"comm_type_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")])
        await query.edit_message_text(
            f"🔧 *Новая коммуникация*\n\nВыбери тип:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("comm_type_"):
        parts = data.replace("comm_type_", "").split("_", 1)
        room_id = int(parts[0])
        ctype = parts[1]
        context.user_data['comm_room_id'] = room_id
        context.user_data['comm_type'] = ctype
        label = get_comm_type_label(ctype)
        buttons = [
            [InlineKeyboardButton("1. Напротив", callback_data=f"comm_wall_{room_id}_напротив")],
            [InlineKeyboardButton("2. Слева", callback_data=f"comm_wall_{room_id}_слева")],
            [InlineKeyboardButton("3. У входа", callback_data=f"comm_wall_{room_id}_у входа")],
            [InlineKeyboardButton("4. Справа", callback_data=f"comm_wall_{room_id}_справа")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
        ]
        await query.edit_message_text(
            f"🔧 *{label}*\n\nНа какой стене?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("comm_wall_"):
        parts = data.replace("comm_wall_", "").split("_", 1)
        room_id = int(parts[0])
        wall = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['comm_wall'] = wall
        context.user_data['waiting_for'] = 'comm_offset_x'
        await query.edit_message_text(
            f"📐 *Расстояние от угла* (СМ):\n\n_Например: 50_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if data.startswith("comm_show_"):
        comm_id = int(data.replace("comm_show_", ""))
        c = get_comm(comm_id)
        if not c:
            await query.edit_message_text("❌ Не найдено")
            return
        label = get_comm_type_label(c.get('comm_type'))
        text = f"🔧 *Коммуникация #{comm_id}*\n\n{label}\n"
        text += f"🧱 Стена: {c.get('wall') or '?'}\n"
        if c.get('offset_x') is not None:
            text += f"📐 От угла: {c['offset_x']} см\n"
        if c.get('offset_y') is not None:
            text += f"📏 От пола: {c['offset_y']} см\n"
        if c.get('diameter'):
            text += f"⭕ Диаметр: {c['diameter']} мм\n"
        if c.get('voltage'):
            text += f"⚡ Напряжение: {c['voltage']} В\n"
        if c.get('size'):
            text += f"📦 Размер: {c['size']} см\n"
        buttons = [
            [InlineKeyboardButton("✏️ От угла", callback_data=f"comm_edit_{comm_id}_offset_x"),
             InlineKeyboardButton("✏️ От пола", callback_data=f"comm_edit_{comm_id}_offset_y")],
        ]
        ctype = c.get('comm_type')
        if ctype == 'elec_panel':
            buttons.append([InlineKeyboardButton("✏️ Размер щита", callback_data=f"comm_edit_{comm_id}_size")])
        elif ctype in ('water_cold', 'water_hot', 'sewer', 'heating', 'gas', 'drain', 'vent'):
            buttons.append([InlineKeyboardButton("✏️ Диаметр", callback_data=f"comm_edit_{comm_id}_diameter")])
        buttons.append([InlineKeyboardButton("✏️ Стена", callback_data=f"comm_edit_{comm_id}_wall")])
        buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data=f"comm_del_{comm_id}")])
        buttons.append([InlineKeyboardButton("⬅️ К коммуникациям", callback_data=f"room_comms_{c['room_id']}")])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("comm_del_"):
        comm_id = int(data.replace("comm_del_", ""))
        c = get_comm(comm_id)
        room_id = c['room_id'] if c else None
        delete_comm(comm_id)
        if room_id:
            await query.edit_message_text(
                "✅ Удалено",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К коммуникациям", callback_data=f"room_comms_{room_id}")],
                ])
            )
        return

    if data.startswith("comm_volt_"):
        parts = data.replace("comm_volt_", "").split("_")
        volt = int(parts[0])
        room_id = int(parts[1])
        context.user_data['comm_voltage'] = volt
        context.user_data['waiting_for'] = None
        ctype = context.user_data.get('comm_type')
        wall = context.user_data.get('comm_wall')
        offset_x = context.user_data.get('comm_offset_x')
        offset_y = context.user_data.get('comm_offset_y')
        if not all([room_id, ctype, wall]):
            await query.edit_message_text("❌ Данные потерялись")
            return
        add_comm(room_id=room_id, comm_type=ctype, wall=wall,
                 offset_x=offset_x, offset_y=offset_y, voltage=volt)
        for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
                  'comm_offset_y', 'comm_diameter', 'comm_voltage', 'waiting_for']:
            context.user_data[k] = None
        label = get_comm_type_label(ctype)
        await query.edit_message_text(
            f"✅ *{label}* добавлена!\n\n🧱 Стена: {wall}\n📐 От угла: {offset_x} см\n📏 От пола: {offset_y} см\n⚡ {volt} В",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
                [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if data.startswith("comm_skip_depth_"):
        room_id = int(data.replace("comm_skip_depth_", ""))
        w = context.user_data.get('comm_size_w') or 0
        h = context.user_data.get('comm_size_h') or 0
        size = f"{w}×{h}×?"
        ctype = context.user_data.get('comm_type')
        wall = context.user_data.get('comm_wall')
        offset_x = context.user_data.get('comm_offset_x')
        offset_y = context.user_data.get('comm_offset_y')
        if not all([room_id, ctype, wall]):
            await query.edit_message_text("❌ Данные потерялись")
            return
        add_comm(room_id=room_id, comm_type=ctype, wall=wall,
                 offset_x=offset_x, offset_y=offset_y, size=size)
        for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
                  'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_size',
                  'comm_size_w', 'comm_size_h', 'comm_size_d', 'waiting_for']:
            context.user_data[k] = None
        label = get_comm_type_label(ctype)
        await query.edit_message_text(
            f"✅ *{label}* добавлена!\n\n🧱 {wall}\n📐 От угла: {offset_x} см\n📏 От пола: {offset_y} см\n📦 Размер: {size} см",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
                [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if data.startswith("comm_skip_size_"):
        room_id = int(data.replace("comm_skip_size_", ""))
        ctype = context.user_data.get('comm_type')
        wall = context.user_data.get('comm_wall')
        offset_x = context.user_data.get('comm_offset_x')
        offset_y = context.user_data.get('comm_offset_y')
        if not all([room_id, ctype, wall]):
            await query.edit_message_text("❌ Данные потерялись")
            return
        add_comm(room_id=room_id, comm_type=ctype, wall=wall,
                 offset_x=offset_x, offset_y=offset_y)
        for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
                  'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_size', 'waiting_for']:
            context.user_data[k] = None
        label = get_comm_type_label(ctype)
        await query.edit_message_text(
            f"✅ *{label}* добавлена!\n\n🧱 {wall}\n📐 От угла: {offset_x} см\n📏 От пола: {offset_y} см",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
                [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if data.startswith("comm_skip_diam_"):
        room_id = int(data.replace("comm_skip_diam_", ""))
        ctype = context.user_data.get('comm_type')
        wall = context.user_data.get('comm_wall')
        offset_x = context.user_data.get('comm_offset_x')
        offset_y = context.user_data.get('comm_offset_y')
        if not all([room_id, ctype, wall]):
            await query.edit_message_text("❌ Данные потерялись")
            return
        add_comm(room_id=room_id, comm_type=ctype, wall=wall,
                 offset_x=offset_x, offset_y=offset_y)
        for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
                  'comm_offset_y', 'comm_diameter', 'comm_voltage', 'waiting_for']:
            context.user_data[k] = None
        label = get_comm_type_label(ctype)
        await query.edit_message_text(
            f"✅ *{label}* добавлена!\n\n🧱 {wall}\n📐 От угла: {offset_x} см\n📏 От пола: {offset_y} см",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
                [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if data.startswith("comm_edit_"):
        _parts = data.replace("comm_edit_", "").split("_")
        if len(_parts) == 3 and _parts[1] == "size":
            comm_id = int(_parts[0])
            sub = _parts[2]
            context.user_data['comm_edit_id'] = comm_id
            context.user_data['comm_edit_field'] = f"size_{sub}"
            context.user_data['waiting_for'] = 'comm_edit_size_part'
            names = {'w': 'ШИРИНА', 'h': 'ВЫСОТА', 'd': 'ГЛУБИНА'}
            name = names.get(sub, sub)
            await query.edit_message_text(
                f"📦 *{name} щита* (см):\n\n_Напиши число._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"comm_show_{comm_id}")],
                ])
            )
            return

        parts = data.replace("comm_edit_", "").split("_")
        comm_id = int(parts[0])
        field = parts[1]
        if field == 'wall':
            buttons = [
                [InlineKeyboardButton("1. Напротив", callback_data=f"comm_set_{comm_id}_wall_напротив")],
                [InlineKeyboardButton("2. Слева", callback_data=f"comm_set_{comm_id}_wall_слева")],
                [InlineKeyboardButton("3. У входа", callback_data=f"comm_set_{comm_id}_wall_у входа")],
                [InlineKeyboardButton("4. Справа", callback_data=f"comm_set_{comm_id}_wall_справа")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"comm_show_{comm_id}")],
            ]
            await query.edit_message_text(
                "✏️ *Смена стены*\n\nНа какой стене?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return
        if field == 'size':
            c = get_comm(comm_id)
            size_str = c.get('size') or '?×?×?'
            sp = size_str.split('×')
            w = sp[0] if len(sp) > 0 else '?'
            h = sp[1] if len(sp) > 1 else '?'
            d = sp[2] if len(sp) > 2 else '?'
            buttons = [
                [InlineKeyboardButton(f"✏️ Ширина: {w}", callback_data=f"comm_edit_{comm_id}_size_w")],
                [InlineKeyboardButton(f"✏️ Высота: {h}", callback_data=f"comm_edit_{comm_id}_size_h")],
                [InlineKeyboardButton(f"✏️ Глубина: {d}", callback_data=f"comm_edit_{comm_id}_size_d")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"comm_show_{comm_id}")],
            ]
            await query.edit_message_text(
                f"📦 *Размер щита*\n\nЧто изменить?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            return

        context.user_data['comm_edit_id'] = comm_id
        context.user_data['comm_edit_field'] = field
        context.user_data['waiting_for'] = 'comm_edit_value'
        prompts = {
            'offset_x': '📐 *Новое расстояние от угла* (СМ):',
            'offset_y': '📏 *Новая высота от пола* (СМ):',
            'diameter': '⭕ *Новый диаметр* (мм):',
            'voltage': '⚡ *Напряжение* (220 или 380):',
        }
        prompt = prompts.get(field, '✏️ Новое значение:')
        await query.edit_message_text(
            f"{prompt}\n\n_Напиши и отправь._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"comm_show_{comm_id}")],
            ])
        )
        return

    if data.startswith("comm_set_"):
        parts = data.replace("comm_set_", "").split("_")
        comm_id = int(parts[0])
        field = parts[1]
        value = "_".join(parts[2:])
        if field == 'wall':
            update_comm(comm_id, wall=value)
        c = get_comm(comm_id)
        if c:
            label = get_comm_type_label(c.get('comm_type'))
            text = f"🔧 *Коммуникация #{comm_id}*\n\n{label}\n🧱 Стена: {c.get('wall') or '?'}"
            buttons = [
                [InlineKeyboardButton("✏️ От угла", callback_data=f"comm_edit_{comm_id}_offset_x"),
                 InlineKeyboardButton("✏️ От пола", callback_data=f"comm_edit_{comm_id}_offset_y")],
                [InlineKeyboardButton("⬅️ К коммуникации", callback_data=f"comm_show_{comm_id}")],
                [InlineKeyboardButton("⬅️ К коммуникациям", callback_data=f"room_comms_{c['room_id']}")],
            ]
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        return


    # ============ ПРОЁМЫ (отдельные, не в обходе) ============
    if data.startswith("openings_list_"):
        room_id = int(data.replace("openings_list_", ""))
        openings = get_openings(room_id)
        room = get_room(room_id)
        room_name = room['name'] if room else '?'
        text = f"🚪 *Проёмы в комнате «{room_name}»*\n\n"
        if not openings:
            text += "_Пока проёмов нет._"
        else:
            for i, o in enumerate(openings, 1):
                text += f"{i}. {format_opening(o)}\n"
        buttons = []
        for o in openings:
            label = OPENING_TYPES.get(o.get('opening_type'), '?')
            wall = o.get('wall_pos') or '?'
            buttons.append([InlineKeyboardButton(f"{label} ({wall})", callback_data=f"opening_show_{o['id']}")])
        buttons.append([InlineKeyboardButton("➕ Добавить проём", callback_data=f"opening_add_{room_id}")])
        buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("opening_add_"):
        room_id = int(data.replace("opening_add_", ""))
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

    if data.startswith("opening_type_"):
        parts = data.replace("opening_type_", "").split("_", 1)
        room_id = int(parts[0])
        otype = parts[1]
        context.user_data['opening_room_id'] = room_id
        context.user_data['opening_type'] = otype
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

    if data.startswith("opening_wall_"):
        parts = data.replace("opening_wall_", "").split("_", 1)
        room_id = int(parts[0])
        wall_pos = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['opening_wall_pos'] = wall_pos
        context.user_data['waiting_for'] = 'opening_width'
        await query.edit_message_text(
            f"📏 *Ширина проёма* (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
            ])
        )
        return

    if data.startswith("opening_show_"):
        opening_id = int(data.replace("opening_show_", ""))
        o = get_opening(opening_id)
        if not o:
            await query.edit_message_text("❌ Проём не найден")
            return
        otype = o.get('opening_type') or '?'
        label = OPENING_TYPES.get(otype, otype)
        text = f"🚪 *Проём #{opening_id}*\n\n{label}\n"
        text += f"🧱 Стена: {o.get('wall_pos') or '?'}\n"
        if o.get('width'): text += f"📏 Ширина: {o['width']} см\n"
        if o.get('height'): text += f"📏 Высота: {o['height']} см\n"
        if o.get('sill_height'): text += f"📏 Подоконник: {o['sill_height']} см\n"
        buttons = [
            [InlineKeyboardButton("✏️ Ширина", callback_data=f"opening_edit_{opening_id}_width")],
            [InlineKeyboardButton("✏️ Высота", callback_data=f"opening_edit_{opening_id}_height")],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f"opening_del_{opening_id}")],
            [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{o['room_id']}")],
        ]
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("opening_edit_"):
        parts = data.replace("opening_edit_", "").split("_")
        opening_id = int(parts[0])
        field = parts[1]
        context.user_data['opening_edit_id'] = opening_id
        context.user_data['opening_edit_field'] = field
        context.user_data['waiting_for'] = 'opening_edit_value'
        prompts = {'width': 'Ширина', 'height': 'Высота', 'sill': 'Подоконник'}
        await query.edit_message_text(
            f"✏️ *{prompts.get(field, 'Значение')}* (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_show_{opening_id}")],
            ])
        )
        return

    if data.startswith("opening_del_"):
        opening_id = int(data.replace("opening_del_", ""))
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

    # ============ ОБХОД СТЕН ============
    if data.startswith("wall_round_start_"):
        room_id = int(data.replace("wall_round_start_", ""))
        progress = get_walls_progress(room_id)
        if progress['walls_count'] >= 4:
            await query.edit_message_text(
                "✅ Все 4 стены уже замерены.",
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
        # Проверяем черновик — есть ли незавершённая стена
        context.user_data['wall_step'] = next_step
        context.user_data['wall_room_id'] = room_id
        print(f"🔍 wall_round_start_ вызван: room_id={room_id}, step={next_step}", flush=True)
        step_name = _load_wall_draft(context, room_id)
        print(f"🔍 ВОССТАНОВЛЕНИЕ: step_name={step_name!r}", flush=True)
        if step_name == 'flags':
            if not context.user_data.get('wall_flags'):
                context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
            await _show_wall_step(query, context, room_id, next_step, phase='flags')
            return
        if step_name == 'plane':
            await _show_wall_plane(query, context, room_id)
            return
        if step_name == 'plane_wavy':
            context.user_data['wall_plane'] = 'wavy'
            context.user_data['waiting_for'] = 'wall_round_plane_bottom'
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(
                "📏 *Замер СЛЕВА* (СМ):\n\nПродолжаем замер стены.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        if step_name == 'length':
            await _show_wall_length(query, context, room_id, next_step)
            return
        if step_name == 'openings':
            await _show_wall_openings(query, context, room_id, next_step)
            return
        if step_name == 'angle':
            await _show_wall_angle(query, context, room_id, next_step)
            return
        if step_name == 'angle_done':
            # Угол введён — проверяем remaining_steps
            remaining = context.user_data.get('wall_remaining_steps') or []
            if remaining:
                first = remaining[0]
                context.user_data['wall_remaining_steps'] = remaining[1:]
                await _do_wall_step(query, context, room_id, first)
                return
            await _wall_save_and_next(query, context, room_id, next_step)
            return
        if step_name in ('niche', 'niche_width'):
            context.user_data['waiting_for'] = 'wall_niche_width'
            await query.message.chat.send_message(
                "🕳 *Продолжаем нишу*\n\n📏 Ширина (СМ):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        if step_name == 'niche_depth':
            context.user_data['waiting_for'] = 'wall_niche_depth'
            await query.message.chat.send_message(
                "🕳 *Продолжаем нишу*\n\n📏 Глубина (СМ):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        if step_name == 'niche_height':
            context.user_data['waiting_for'] = 'wall_niche_height'
            await query.message.chat.send_message(
                "🕳 *Продолжаем нишу*\n\n📏 Высота (СМ):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        if step_name == 'niche_plane':
            _rid = context.user_data.get('wall_room_id')
            await query.message.chat.send_message(
                "🕳 *Ниша ровная или неровная по высоте?*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_niche_plane_rect_{_rid}")],
                    [InlineKeyboardButton("📏 Неровная", callback_data=f"wall_niche_plane_irr_{_rid}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{_rid}")],
                ])
            )
            return
        # По умолчанию — галочки
        if not context.user_data.get('wall_flags'):
            context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
        await _show_wall_step(query, context, room_id, next_step, phase='flags')
        return

    if data.startswith("wall_round_reset_"):
        room_id = int(data.replace("wall_round_reset_", ""))
        walls = get_measures(room_id, category='wall')
        for w in walls:
            delete_measure(w['id'])
        from core.db import commit
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
        _save_wall_draft(context, room_id, 'flags')
        # Сохраняем черновик
        step = context.user_data.get('wall_step') or 1
        context.user_data[f'wall_draft_{room_id}'] = {
            'step': step, 'flags': flags,
            'length': context.user_data.get('wall_length'),
        }
        step = context.user_data.get('wall_step') or 1
        wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
        pos = wall_names.get(step, '?')
        f_niche = '✅' if flags.get('niche') else '⬜'
        f_rounded = '✅' if flags.get('rounded') else '⬜'
        f_wavy = '✅' if flags.get('wavy') else '⬜'
        f_hidden = '✅' if flags.get('hidden') else '⬜'
        caption = f"🧱 *Стена {step} — {pos}*\n\n👁 Осмотри стену.\nОтметь особенности:"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{f_niche} С нишей", callback_data=f"wall_round_flag_niche_{room_id}")],
            [InlineKeyboardButton(f"{f_rounded} С закруглением", callback_data=f"wall_round_flag_rounded_{room_id}")],
            [InlineKeyboardButton(f"{f_wavy} Разная по высоте", callback_data=f"wall_round_flag_wavy_{room_id}")],
            [InlineKeyboardButton(f"{f_hidden} Скрытые коммуникации", callback_data=f"wall_round_flag_hidden_{room_id}")],
            [InlineKeyboardButton("➡️ Дальше", callback_data=f"wall_round_flags_done_{room_id}")],
            [InlineKeyboardButton("⏭ Пропустить", callback_data=f"wall_round_skip_{room_id}")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        try:
            await query.edit_message_caption(caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            pass
        return

    if data.startswith("wall_round_flags_done_"):
        room_id = int(data.replace("wall_round_flags_done_", ""))
        step = context.user_data.get('wall_step') or 1
        context.user_data['wall_room_id'] = room_id
        context.user_data['wall_step'] = step
        flags = context.user_data.get('wall_flags') or {}
        # Запоминаем особенности — обработаем ПОСЛЕ угла
        steps = []
        if flags.get('niche'): steps.append('niche')
        if flags.get('rounded'): steps.append('rounded')
        if flags.get('wavy'): steps.append('wavy')
        if flags.get('hidden'): steps.append('hidden')
        context.user_data['wall_remaining_steps'] = steps
        # Всегда сначала — плоскость
        await _show_wall_plane(query, context, room_id)
        return

    if data.startswith("wall_round_plane_"):
        parts = data.replace("wall_round_plane_", "").split("_")
        plane = parts[0]
        room_id = int(parts[1])
        step = context.user_data.get('wall_step') or 1
        if plane == 'straight':
            context.user_data['wall_plane'] = 'straight'
            _save_wall_draft(context, room_id, 'plane')
            context.user_data['wall_bottom'] = None
            context.user_data['wall_middle'] = None
            context.user_data['wall_top'] = None
            context.user_data['wall_room_id'] = room_id
            context.user_data['wall_step'] = step
            _save_wall_draft(context, room_id, 'length')
            await _show_wall_length(query, context, room_id, step)
            return
        if plane == 'wavy':
            context.user_data['wall_plane'] = 'wavy'
            context.user_data['waiting_for'] = 'wall_round_plane_bottom'
            _save_wall_draft(context, room_id, 'plane_wavy')
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(
                "📏 *Замер СЛЕВА* (СМ):\n\nОтойди к левому краю стены.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
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
            _save_wall_draft(context, room_id, 'angle_done')
            # Проверяем есть ли отложенные шаги (ниши/rounded/wavy/hidden)
            remaining = context.user_data.get('wall_remaining_steps') or []
            if remaining:
                first = remaining[0]
                context.user_data['wall_remaining_steps'] = remaining[1:]
                await _do_wall_step(query, context, room_id, first)
                return
            await _wall_save_and_next(query, context, room_id, step)
            return
        if method in ('60', '100'):
            context.user_data['waiting_for'] = 'wall_round_angle_val'
            hint = 'Идеал: 100 см' if method == '60' else 'Идеал: 141 см'
            await query.edit_message_text(
                f"📏 *Диагональ ({method})*\n_{hint}_\n\nВведи в СМ:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
            return
        if method == 'deg':
            context.user_data['waiting_for'] = 'wall_round_angle_val'
            await query.edit_message_text(
                "📐 *Угол в градусах*\n\nВведи (например 93):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
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

    # Ниши
    if data.startswith("wall_niche_count_"):
        parts = data.replace("wall_niche_count_", "").split("_", 1)
        count = int(parts[0])
        room_id = int(parts[1])
        context.user_data['wall_niche_count'] = count
        context.user_data['wall_niche_current'] = 1
        context.user_data['wall_niches'] = []
        context.user_data['waiting_for'] = 'wall_niche_width'
        _save_wall_draft(context, room_id, 'niche_width')
        import os as _os
        _base = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        _png = _os.path.join(_base, "docs", "images", "niche_width.png")
        _cap = f"🕳 *Ниша 1 из {count}*\n\n📏 *Ширина ниши* (СМ):\n\n_Например: 80_"
        _kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        try:
            await query.message.delete()
        except Exception:
            pass
        if _os.path.exists(_png):
            try:
                with open(_png, "rb") as f:
                    await query.message.chat.send_photo(photo=f, caption=_cap,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=_kb)
                return
            except Exception:
                pass
        await query.message.chat.send_message(_cap, parse_mode=ParseMode.MARKDOWN, reply_markup=_kb)
        return

    # Ниши — ровная/неровная
    if data.startswith("wall_niche_plane_rect_"):
        room_id = int(data.replace("wall_niche_plane_rect_", ""))
        temp = context.user_data.get('wall_niche_temp') or {}
        temp['width_top'] = temp.get('width')
        temp['depth_top'] = temp.get('depth')
        niches = context.user_data.get('wall_niches') or []
        niches.append(temp)
        context.user_data['wall_niches'] = niches
        context.user_data['wall_niche_temp'] = {}
        total = context.user_data.get('wall_niche_count') or 1
        current = context.user_data.get('wall_niche_current') or 1
        if current < total:
            context.user_data['wall_niche_current'] = current + 1
            context.user_data['waiting_for'] = 'wall_niche_width'
            await query.edit_message_text(
                f"✅ Ниша {current}\n\n🕳 *Ниша {current + 1}* — Ширина (СМ):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        await query.edit_message_text("✅ Все ниши записаны")
        await _show_wall_plane(query, context, room_id)
        return

    if data.startswith("wall_niche_plane_irr_"):
        room_id = int(data.replace("wall_niche_plane_irr_", ""))
        context.user_data['waiting_for'] = 'wall_niche_top_width'
        await query.edit_message_text(
            "🕳 *Ширина СВЕРХУ* (СМ):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Проёмы при обходе стены
    if data.startswith("wall_round_open_win_"):
        room_id = int(data.replace("wall_round_open_win_", ""))
        step = context.user_data.get('wall_step') or 1
        wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
        context.user_data['wall_round_opening_wall'] = wall_names.get(step, 'напротив')
        context.user_data['wall_round_opening_type'] = 'window'
        context.user_data['waiting_for'] = 'wall_round_opening_width'
        await query.edit_message_text(
            "🪟 *Окно*\n\n📏 Ширина (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"wall_round_openings_done_{room_id}")],
            ])
        )
        return

    if data.startswith("wall_round_open_door_"):
        room_id = int(data.replace("wall_round_open_door_", ""))
        step = context.user_data.get('wall_step') or 1
        wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
        context.user_data['wall_round_opening_wall'] = wall_names.get(step, 'напротив')
        context.user_data['wall_round_opening_type'] = 'door_interior'
        context.user_data['waiting_for'] = 'wall_round_opening_width'
        await query.edit_message_text(
            "🚪 *Дверь*\n\n📏 Ширина (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"wall_round_openings_done_{room_id}")],
            ])
        )
        return

    if data.startswith("wall_round_open_vent_"):
        room_id = int(data.replace("wall_round_open_vent_", ""))
        step = context.user_data.get('wall_step') or 1
        wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
        context.user_data['wall_round_opening_wall'] = wall_names.get(step, 'напротив')
        context.user_data['wall_round_opening_type'] = 'vent'
        context.user_data['waiting_for'] = 'wall_round_opening_height'
        await query.edit_message_text(
            "💨 *Вентиляция*\n\n📏 Высота от пола (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"wall_round_openings_done_{room_id}")],
            ])
        )
        return

    if data.startswith("wall_round_openings_done_"):
        room_id = int(data.replace("wall_round_openings_done_", ""))
        step = context.user_data.get('wall_step') or 1
        _save_wall_draft(context, room_id, 'angle')
        await _show_wall_angle(query, context, room_id, step)
        return

    # Назад к списку объектов
    if data.startswith("rooms_list_obj_"):
        object_id = int(data.replace("rooms_list_obj_", ""))
        await show_rooms_list(update, context, object_id)
        return


async def _send_height_scheme(update_or_query, context, room_id, step, caption, kb_extra=None):
    """Отправка PNG-схемы высоты."""
    import os
    kb_rows = []
    if kb_extra:
        kb_rows = kb_extra
    kb_rows.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")])
    kb = InlineKeyboardMarkup(kb_rows)
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    png = os.path.join(base, "docs", "images", f"height_scheme_step{step}.png")
    if hasattr(update_or_query, 'message'):
        try:
            await update_or_query.message.delete()
        except Exception:
            pass
        if os.path.exists(png):
            try:
                with open(png, "rb") as f:
                    await update_or_query.message.chat.send_photo(photo=f, caption=caption,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
                return
            except Exception:
                pass
        await update_or_query.message.chat.send_message(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        if os.path.exists(png):
            try:
                with open(png, "rb") as f:
                    await update_or_query.message.reply_photo(photo=f, caption=caption,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
                return
            except Exception:
                pass
        await update_or_query.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_height_step(query, context, room_id, method=None, step=1):
    """Экран шага высоты."""
    if step == 1:
        caption = (
            f"📏 *Высота — шаг 1*\n\n"
            f"📍 *Точка 1 — ЦЕНТР комнаты*\n\n"
            f"Встань в центре комнаты, приложи дальномер к полу, наведи на потолок.\n"
            f"Введи результат в СМ:\n\n_Например: 305_"
        )
    elif step == 2:
        caption = (
            f"📏 *Высота — шаг 2*\n\n"
            f"📍 *Точка 2 — у ЛЕВОГО угла*\n\n"
            f"Введи результат в СМ:\n\n_Например: 304_"
        )
    else:
        caption = (
            f"📏 *Высота — шаг 3*\n\n"
            f"📍 *Точка 3 — у ПРАВОГО угла*\n\n"
            f"Введи результат в СМ:\n\n_Например: 306_"
        )
    kb_extra = [
        [InlineKeyboardButton("✅ Все три одинаковые", callback_data=f"room_height_same_{room_id}")],
    ]
    context.user_data['waiting_for'] = 'room_height_point'
    context.user_data['height_room_id'] = room_id
    context.user_data['height_step'] = step
    await _send_height_scheme(query, context, room_id, step, caption, kb_extra)


async def handle_measure_input(update, context):
    """Роутер текстового ввода по waiting_for."""
    step = context.user_data.get('waiting_for')

    # --- Переименование комнаты ---
    if step == 'room_rename':
        room_id = context.user_data.get('room_rename_id')
        new_name = (update.message.text or '').strip()
        if room_id and new_name:
            from core.rooms import update_room as _upd
            try:
                _upd(room_id, name=new_name)
            except Exception:
                from core.db import commit
                commit("UPDATE rooms SET name = ? WHERE id = ?", (new_name, room_id))
            context.user_data['waiting_for'] = None
            context.user_data['room_rename_id'] = None
            await update.message.reply_text(
                f"✅ Имя комнаты изменено на «{new_name}»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        return

    # --- УНИВЕРСАЛЬНЫЙ РОУТЕР: ниши / rounded / wavy / hidden ---
    if step and (step.startswith('wall_niche_')
                 or step in ('wall_rounded_radius', 'wall_wavy_note', 'wall_hidden_note')):
        await _handle_wall_round_input(update, context, step)
        return

    # --- Коммуникации ---
    if step == 'comm_offset_x':
        room_id = context.user_data.get('comm_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        context.user_data['comm_offset_x'] = val
        context.user_data['waiting_for'] = 'comm_offset_y'
        await update.message.reply_text(
            "📏 *Высота от пола* (СМ):\n\n_Например: 30_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if step == 'comm_offset_y':
        room_id = context.user_data.get('comm_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        context.user_data['comm_offset_y'] = val
        ctype = context.user_data.get('comm_type')
        if ctype == 'elec_panel':
            context.user_data['waiting_for'] = 'comm_size_w'
            await update.message.reply_text(
                "📦 *Размер щита* — ШИРИНА (см):\n\n_Например: 45_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Пропустить размер", callback_data=f"comm_skip_size_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
                ])
            )
        elif ctype in ('water_cold', 'water_hot', 'sewer', 'heating', 'gas', 'drain', 'vent'):
            context.user_data['waiting_for'] = 'comm_diameter'
            await update.message.reply_text(
                f"⭕ *Диаметр* (мм):\n\n_Например: 20, 32, 50_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Пропустить", callback_data=f"comm_skip_diam_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
                ])
            )
        else:
            # Электроточки / слаботочка — сразу сохраняем
            wall = context.user_data.get('comm_wall')
            offset_x = context.user_data.get('comm_offset_x')
            offset_y = context.user_data.get('comm_offset_y')
            add_comm(room_id=room_id, comm_type=ctype, wall=wall,
                     offset_x=offset_x, offset_y=offset_y)
            for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
                      'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_size', 'waiting_for']:
                context.user_data[k] = None
            label = get_comm_type_label(ctype)
            await update.message.reply_text(
                f"✅ *{label}* добавлена!\n\n🧱 {wall}\n📐 От угла: {offset_x} см\n📏 От пола: {offset_y} см",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
                    [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
                ])
            )
        return

    if step == 'comm_diameter':
        room_id = context.user_data.get('comm_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        context.user_data['comm_diameter'] = val
        await _comm_save(update, context)
        return

    if step == 'comm_size_w':
        room_id = context.user_data.get('comm_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = int(float(text_val))
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        context.user_data['comm_size_w'] = val
        context.user_data['waiting_for'] = 'comm_size_h'
        await update.message.reply_text(
            "📦 *Размер щита* — ВЫСОТА (см):\n\n_Например: 60_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ Пропустить", callback_data=f"comm_skip_size_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if step == 'comm_size_h':
        room_id = context.user_data.get('comm_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = int(float(text_val))
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        context.user_data['comm_size_h'] = val
        context.user_data['waiting_for'] = 'comm_size_d'
        await update.message.reply_text(
            "📦 *Размер щита* — ГЛУБИНА (см):\n\n_Например: 12_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭ Не знаю", callback_data=f"comm_skip_depth_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if step == 'comm_size_d':
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = int(float(text_val))
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        w = context.user_data.get('comm_size_w') or 0
        h = context.user_data.get('comm_size_h') or 0
        context.user_data['comm_size'] = f"{w}×{h}×{val}"
        await _comm_save(update, context)
        return

    if step == 'comm_edit_value':
        comm_id = context.user_data.get('comm_edit_id')
        field = context.user_data.get('comm_edit_field')
        text_val = (update.message.text or '').strip().replace(',', '.')
        if not all([comm_id, field]):
            await update.message.reply_text("❌ Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        try:
            if field in ('offset_x', 'offset_y', 'diameter'):
                val = float(text_val)
            elif field == 'voltage':
                val = int(float(text_val))
            else:
                val = text_val
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        update_comm(comm_id, **{field: val})
        c = get_comm(comm_id)
        context.user_data['waiting_for'] = None
        context.user_data['comm_edit_id'] = None
        context.user_data['comm_edit_field'] = None
        if c:
            label = get_comm_type_label(c.get('comm_type'))
            await update.message.reply_text(
                f"✅ Обновлено!\n\n🔧 *{label}* #{comm_id}\n🧱 Стена: {c.get('wall')}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К коммуникации", callback_data=f"comm_show_{comm_id}")],
                    [InlineKeyboardButton("⬅️ К списку", callback_data=f"room_comms_{c['room_id']}")],
                ])
            )
        return

    if step == 'comm_edit_size_part':
        comm_id = context.user_data.get('comm_edit_id')
        field = context.user_data.get('comm_edit_field')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = int(float(text_val))
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        c = get_comm(comm_id)
        if not c:
            await update.message.reply_text("❌ Не найдено")
            context.user_data['waiting_for'] = None
            return
        size_str = c.get('size') or '?×?×?'
        parts = size_str.split('×')
        while len(parts) < 3:
            parts.append('?')
        idx = {'size_w': 0, 'size_h': 1, 'size_d': 2}.get(field, 0)
        parts[idx] = str(val)
        new_size = '×'.join(parts)
        update_comm(comm_id, size=new_size)
        context.user_data['waiting_for'] = None
        context.user_data['comm_edit_id'] = None
        context.user_data['comm_edit_field'] = None
        label = get_comm_type_label(c.get('comm_type'))
        await update.message.reply_text(
            f"✅ Обновлено!\n\n🔧 *{label}* #{comm_id}\n📦 Размер: {new_size} см",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К коммуникации", callback_data=f"comm_show_{comm_id}")],
            ])
        )
        return


    # --- Высота потолка ---
    if step == 'room_height_point':
        room_id = context.user_data.get('height_room_id')
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната")
            return
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        h_step = context.user_data.get('height_step') or 1
        if h_step == 1:
            context.user_data['height_bottom'] = val
            context.user_data['height_step'] = 2
            await _show_height_step(update, context, room_id, step=2)
        elif h_step == 2:
            context.user_data['height_middle'] = val
            context.user_data['height_step'] = 3
            await _show_height_step(update, context, room_id, step=3)
        else:
            context.user_data['height_top'] = val
            h_bottom = context.user_data.get('height_bottom')
            h_middle = context.user_data.get('height_middle')
            h_top = val
            h_avg = (h_bottom + h_middle + h_top) / 3
            update_room(room_id, height=h_avg, height_bottom=h_bottom,
                        height_middle=h_middle, height_top=h_top)
            for k in ['waiting_for', 'height_room_id', 'height_step',
                      'height_bottom', 'height_middle', 'height_top']:
                context.user_data[k] = None
            await update.message.reply_text(
                f"✅ *Высота сохранена:*\n"
                f"Центр: {h_bottom} см\nЛевый: {h_middle} см\nПравый: {h_top} см\n"
                f"Среднее: {round(h_avg, 1)} см",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        return

    if step == 'room_height_same':
        room_id = context.user_data.get('height_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        update_room(room_id, height=val, height_bottom=val, height_middle=val, height_top=val)
        for k in ['waiting_for', 'height_room_id', 'height_step']:
            context.user_data[k] = None
        await update.message.reply_text(
            f"✅ *Высота: {val} см* (везде одинаковая)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 Начать обход", callback_data=f"wall_round_start_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    # --- Обход стен ---
    if step in ('wall_round_length', 'wall_round_angle_val',
                'wall_round_plane_bottom', 'wall_round_plane_middle',
                'wall_round_plane_top', 'wall_niche_width', 'wall_niche_depth',
                'wall_niche_height', 'wall_rounded_radius', 'wall_wavy_note',
                'wall_hidden_note', 'wall_niche_top_width', 'wall_niche_top_depth'):
        await _handle_wall_round_input(update, context, step)
        return

    if step in ('wall_round_opening_width', 'wall_round_opening_height'):
        await _handle_wall_round_opening_input(update, context, step)
        return

    # --- Проёмы (отдельные) ---
    if step == 'opening_width':
        room_id = context.user_data.get('opening_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        context.user_data['opening_width'] = val
        context.user_data['waiting_for'] = 'opening_height'
        room_id = context.user_data.get('opening_room_id')
        await update.message.reply_text(
            "📏 *Высота проёма* (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
            ])
        )
        return

    if step == 'opening_height':
        room_id = context.user_data.get('opening_room_id')
        otype = context.user_data.get('opening_type')
        wall_pos = context.user_data.get('opening_wall_pos')
        width = context.user_data.get('opening_width')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        add_opening(room_id=room_id, opening_type=otype, wall_pos=wall_pos,
                    width=width, height=val,
                    created_by=update.effective_user.id if update.effective_user else None)
        for k in ['opening_room_id', 'opening_type', 'opening_wall_pos',
                  'opening_width', 'opening_height', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            f"✅ *Проём добавлен!*\n\n{OPENING_TYPES.get(otype, otype)} на стене «{wall_pos}»\n📏 {width} × {val} см",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"opening_add_{room_id}")],
                [InlineKeyboardButton("✅ К проёмам", callback_data=f"openings_list_{room_id}")],
            ])
        )
        return

    if step == 'opening_edit_value':
        opening_id = context.user_data.get('opening_edit_id')
        field = context.user_data.get('opening_edit_field')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        if field == 'width':
            update_opening(opening_id, width=val)
        elif field == 'height':
            update_opening(opening_id, height=val)
        elif field == 'sill':
            update_opening(opening_id, sill_height=val)
        context.user_data['waiting_for'] = None
        context.user_data['opening_edit_id'] = None
        context.user_data['opening_edit_field'] = None
        await update.message.reply_text(
            f"✅ Обновлено!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К проёму", callback_data=f"opening_show_{opening_id}")],
            ])
        )
        return


async def _comm_save(update, context):
    """Сохраняет коммуникацию после ввода всех полей."""
    room_id = context.user_data.get('comm_room_id')
    ctype = context.user_data.get('comm_type')
    wall = context.user_data.get('comm_wall')
    offset_x = context.user_data.get('comm_offset_x')
    offset_y = context.user_data.get('comm_offset_y')
    diameter = context.user_data.get('comm_diameter')
    voltage = context.user_data.get('comm_voltage')
    size = context.user_data.get('comm_size')

    if not all([room_id, ctype, wall]):
        await update.message.reply_text("❌ Потерялись данные")
        context.user_data['waiting_for'] = None
        return

    kwargs = {
        'room_id': room_id, 'comm_type': ctype, 'wall': wall,
        'offset_x': offset_x, 'offset_y': offset_y,
    }
    if diameter is not None:
        kwargs['diameter'] = diameter
    if voltage is not None:
        kwargs['voltage'] = voltage
    if size is not None:
        kwargs['size'] = size

    try:
        add_comm(**kwargs)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
        return

    for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
              'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_size',
              'comm_size_w', 'comm_size_h', 'comm_size_d', 'waiting_for']:
        context.user_data[k] = None

    label = get_comm_type_label(ctype)
    text = f"✅ *{label}* добавлена!\n\n🧱 Стена: {wall}\n"
    if offset_x is not None: text += f"📐 От угла: {offset_x} см\n"
    if offset_y is not None: text += f"📏 От пола: {offset_y} см\n"
    if diameter is not None: text += f"⭕ Диаметр: {diameter} мм\n"
    if voltage is not None: text += f"⚡ Напряжение: {voltage} В\n"
    if size is not None: text += f"📦 Размер: {size} см\n"

    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить ещё", callback_data=f"comm_add_{room_id}")],
            [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
        ])
    )


# ============================================================
# ОБХОД СТЕН — вспомогательные функции
# ============================================================



def _save_wall_draft(context, room_id, step_name):
    """Сохраняет черновик стены в БД."""
    import json
    from core.db import commit as _commit
    print(f"💾 _save_wall_draft: room_id={room_id}, step_name={step_name}", flush=True)
    step_num = context.user_data.get('wall_step') or 1
    flags = context.user_data.get('wall_flags') or {}
    niches = context.user_data.get('wall_niches') or []
    remaining = context.user_data.get('wall_remaining_steps') or []
    niche_temp = context.user_data.get('wall_niche_temp') or {}
    try:
        _commit(
            """INSERT OR REPLACE INTO wall_drafts
            (room_id, step_num, step_name, flags, length, plane,
             angle_value, angle_method, niches, niche_count, niche_current,
             niche_temp, remaining_steps, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (
                room_id, step_num, step_name,
                json.dumps(flags, ensure_ascii=False),
                context.user_data.get('wall_length'),
                context.user_data.get('wall_plane'),
                context.user_data.get('wall_angle_value'),
                context.user_data.get('wall_angle_method'),
                json.dumps(niches, ensure_ascii=False),
                context.user_data.get('wall_niche_count'),
                context.user_data.get('wall_niche_current'),
                json.dumps(niche_temp, ensure_ascii=False),
                json.dumps(remaining, ensure_ascii=False),
            )
        )
    except Exception as e:
        print(f"⚠️ save_wall_draft: {e}", flush=True)


def _load_wall_draft(context, room_id):
    """Загружает черновик стены из БД. Возвращает step_name или None."""
    import json
    from core.db import fetchone as _fetchone
    try:
        draft = _fetchone("SELECT * FROM wall_drafts WHERE room_id = ?", (room_id,))
    except Exception as e:
        print(f"⚠️ load_wall_draft: {e}", flush=True)
        return None
    if not draft:
        print(f"🔍 load_wall_draft: room_id={room_id} — нет черновика", flush=True)
        return None
    draft = dict(draft)
    print(f"🔍 load_wall_draft: room_id={room_id}, step_name={draft.get('step_name')!r}", flush=True)
    context.user_data['wall_step'] = draft.get('step_num') or 1
    flags_raw = draft.get('flags')
    try:
        context.user_data['wall_flags'] = json.loads(flags_raw) if flags_raw else {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
    except Exception:
        context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
    if draft.get('length'): context.user_data['wall_length'] = draft['length']
    if draft.get('plane'): context.user_data['wall_plane'] = draft['plane']
    if draft.get('angle_value'): context.user_data['wall_angle_value'] = draft['angle_value']
    if draft.get('angle_method'): context.user_data['wall_angle_method'] = draft['angle_method']
    if draft.get('niches'):
        try: context.user_data['wall_niches'] = json.loads(draft['niches'])
        except Exception: pass
    if draft.get('niche_count'): context.user_data['wall_niche_count'] = draft['niche_count']
    if draft.get('niche_current'): context.user_data['wall_niche_current'] = draft['niche_current']
    if draft.get('niche_temp'):
        try: context.user_data['wall_niche_temp'] = json.loads(draft['niche_temp'])
        except Exception: pass
    if draft.get('remaining_steps'):
        try: context.user_data['wall_remaining_steps'] = json.loads(draft['remaining_steps'])
        except Exception: pass
    return draft.get('step_name')


async def _show_wall_step(query, context, room_id, step, phase='flags'):
    """Экран галочек стены."""
    wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
    pos = wall_names.get(step, '?')
    flags = context.user_data.get('wall_flags') or {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
    f_niche = '✅' if flags.get('niche') else '⬜'
    f_rounded = '✅' if flags.get('rounded') else '⬜'
    f_wavy = '✅' if flags.get('wavy') else '⬜'
    f_hidden = '✅' if flags.get('hidden') else '⬜'
    caption = f"🧱 *Стена {step} — {pos}*\n\n👁 Осмотри стену.\nОтметь особенности:"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{f_niche} С нишей", callback_data=f"wall_round_flag_niche_{room_id}")],
        [InlineKeyboardButton(f"{f_rounded} С закруглением", callback_data=f"wall_round_flag_rounded_{room_id}")],
        [InlineKeyboardButton(f"{f_wavy} Разная по высоте", callback_data=f"wall_round_flag_wavy_{room_id}")],
        [InlineKeyboardButton(f"{f_hidden} Скрытые коммуникации", callback_data=f"wall_round_flag_hidden_{room_id}")],
        [InlineKeyboardButton("➡️ Дальше", callback_data=f"wall_round_flags_done_{room_id}")],
        [InlineKeyboardButton("⏭ Пропустить", callback_data=f"wall_round_skip_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    png = os.path.join(base, "docs", "images", f"wall_scheme_s{step}_flags.png")
    if os.path.exists(png):
        try:
            try:
                await query.message.delete()
            except Exception as e:
                print(f'⚠️ PNG send error: {e}', flush=True)
            with open(png, "rb") as f:
                await query.message.chat.send_photo(photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            return
        except Exception:
            pass
    try:
        await query.edit_message_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_wall_plane(target, context, room_id):
    """Экран плоскости стены."""
    step = context.user_data.get('wall_step') or 1
    # Проверяем — если галочка "Разная по высоте" уже стоит — пропускаем вопрос
    flags = context.user_data.get('wall_flags') or {}
    if flags.get('wavy'):
        # Сразу — ввод 3 точек
        context.user_data['wall_plane'] = 'wavy'
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        text = (
            f"🧱 *Стена {step}*\n\n"
            f"📏 *Замер в 3 точках:*\n\n"
            f"Введи НИЗ стены (СМ):"
        )
        if hasattr(target, 'message'):
            try:
                await target.message.delete()
            except Exception:
                pass
            await target.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await target.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    text = (
        f"🧱 *Стена {step}*\n\n"
        f"📐 *Плоскость стены:*\n\n"
        f"Стена ровная или кривая по высоте?\n\n"
        f"_Если стена «горбатая» — нужно замерить в 3 точках._"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_round_plane_straight_{room_id}")],
        [InlineKeyboardButton("📏 Разная (3 точки)", callback_data=f"wall_round_plane_wavy_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    png = os.path.join(base, "docs", "images", f"wall_scheme_s{step}_plane.png")
    if hasattr(target, 'message'):
        try:
            await target.message.delete()
        except Exception:
            pass
        if os.path.exists(png):
            try:
                with open(png, "rb") as f:
                    await target.message.chat.send_photo(photo=f, caption=text,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
                return
            except Exception:
                pass
        await target.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        if os.path.exists(png):
            try:
                with open(png, "rb") as f:
                    await target.message.reply_photo(photo=f, caption=text,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
                return
            except Exception:
                pass
        await target.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_wall_length(query, context, room_id, step):
    """Экран длины стены."""
    context.user_data['waiting_for'] = 'wall_round_length'
    context.user_data['wall_room_id'] = room_id
    context.user_data['wall_step'] = step
    wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
    pos = wall_names.get(step, '?')
    text = (
        f"🧱 *Стена {step} — {pos}*\n\n"
        f"📏 *Длина стены* (СМ):\n\n"
        f"⚠️ *ВАЖНО:* дальномер в режиме «от ЗАДНЕЙ СТЕНКИ».\n\n"
        f"Напиши число и отправь."
    )
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    png = os.path.join(base, "docs", "images", f"wall_scheme_s{step}_length.png")
    if os.path.exists(png):
        try:
            try:
                await query.message.delete()
            except Exception:
                pass
            with open(png, "rb") as f:
                await query.message.chat.send_photo(photo=f, caption=text,
                    parse_mode=ParseMode.MARKDOWN)
            return
        except Exception:
            pass
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN)


async def _show_wall_angle(query, context, room_id, step):
    """Экран угла."""
    context.user_data['waiting_for'] = None
    length_cm = context.user_data.get('wall_length') or 0
    text = (
        f"✅ Длина: *{length_cm} см*\n\n"
        f"📐 *Угол между этой стеной и следующей:*\n\n"
        f"Обычно 90° — прямой угол."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 90° (прямой)", callback_data=f"wall_round_angle_90_{room_id}")],
        [InlineKeyboardButton("📏 60-80-100", callback_data=f"wall_round_angle_60_{room_id}")],
        [InlineKeyboardButton("📏 100-100", callback_data=f"wall_round_angle_100_{room_id}")],
        [InlineKeyboardButton("✏️ Угол в °", callback_data=f"wall_round_angle_deg_{room_id}")],
        [InlineKeyboardButton("⬅️ В комнату", callback_data=f"room_{room_id}")],
    ])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _wall_save_and_next(query, context, room_id, step):
    """Сохраняет стену и идёт к следующей."""
    wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
    pos = wall_names.get(step, '?')
    length = context.user_data.get('wall_length') or 0
    angle = context.user_data.get('wall_angle_value') or 90
    angle_method = context.user_data.get('wall_angle_method') or '90'
    plane = context.user_data.get('wall_plane') or 'straight'
    flags = context.user_data.get('wall_flags') or {}

    note_parts = []
    if flags.get('rounded'): note_parts.append('Закругление')
    if flags.get('wavy'): note_parts.append('Разная по высоте')
    if flags.get('hidden'): note_parts.append('Скрытые коммуникации')
    note = '; '.join(note_parts) if note_parts else None

    kwargs = {
        'label': f'Стена {pos}', 'wall_pos': pos, 'length': length,
        'unit': 'см', 'order_num': step,
        'angle_value': angle, 'angle_method': angle_method,
    }
    if flags.get('rounded'): kwargs['has_rounded'] = 1
    if flags.get('hidden'):
        kwargs['has_hidden'] = 1
        kwargs['hidden_note'] = note
    if note: kwargs['note'] = note

    measure_id = add_measure(room_id, 'wall', **kwargs)

    niches = context.user_data.get('wall_niches') or []
    if niches and measure_id:
        for n in niches:
            try:
                add_niche(measure_id=measure_id, room_id=room_id,
                          width_bottom=n.get('width'), width_top=n.get('width'),
                          height=n.get('height'),
                          depth_bottom=n.get('depth'), depth_top=n.get('depth'))
            except Exception as e:
                print(f"⚠️ add_niche: {e}", flush=True)

    for k in ['wall_length', 'wall_angle_value', 'wall_angle_method',
              'wall_plane', 'wall_niches', 'wall_niche_count',
              'wall_niche_current', 'wall_niche_temp', 'wall_flags']:
        context.user_data[k] = None
    # Чистим черновик этой комнаты в БД
    try:
        from core.db import commit as _commit
        _commit("DELETE FROM wall_drafts WHERE room_id = ?", (room_id,))
    except Exception:
        pass

    summary = f"✅ *Стена {step} ({pos}) сохранена!*\n\n📏 Длина: {length} см\n📐 Угол: {angle}°"
    if niches:
        summary += f"\n🕳 Нишей: {len(niches)}"

    if step >= 4:
        complete_walls_round(room_id)
        await _wall_finish(query, context, room_id, summary)
        return

    next_step = step + 1
    context.user_data['wall_step'] = next_step
    context.user_data['wall_flags'] = {'niche': False, 'rounded': False, 'wavy': False, 'hidden': False}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"➡️ Стена {next_step}", callback_data=f"wall_round_start_{room_id}")],
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
    ])
    try:
        await query.edit_message_text(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _wall_finish(query, context, room_id, summary_prefix=''):
    walls = get_walls_ordered(room_id)
    areas = calculate_room_areas(room_id)
    text = summary_prefix + "\n\n🎉 *Все 4 стены замерены!*\n\n"
    if areas.get('walls_net') is not None:
        text += f"📊 Площадь стен: {areas['walls_net']} м²\n"
    if areas.get('floor'):
        text += f"📊 Площадь пола: {areas['floor']} м²\n"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
        [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
    ])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _do_wall_step(query, context, room_id, step):
    """Обработка одного шага (ниша/rounded/wavy/hidden)."""
    if step == 'niche':
        context.user_data['waiting_for'] = 'wall_niche_count'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "🕳 *Сколько нишей на этой стене?*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("1", callback_data=f"wall_niche_count_1_{room_id}")],
                [InlineKeyboardButton("2", callback_data=f"wall_niche_count_2_{room_id}")],
                [InlineKeyboardButton("3", callback_data=f"wall_niche_count_3_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
        )
        return
    if step == 'rounded':
        context.user_data['waiting_for'] = 'wall_rounded_radius'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "🔄 *Закругление*\n\n📏 Радиус (СМ):",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if step == 'wavy':
        context.user_data['waiting_for'] = 'wall_wavy_note'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "📐 *Разная по высоте*\n\nНапиши комментарий:",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    if step == 'hidden':
        context.user_data['waiting_for'] = 'wall_hidden_note'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "🔧 *Скрытые коммуникации*\n\nОпиши что и где:",
            parse_mode=ParseMode.MARKDOWN
        )
        return


async def _handle_wall_round_input(update, context, step):
    """Ввод при обходе стен."""
    room_id = context.user_data.get('wall_room_id')
    text_val = (update.message.text or '').strip().replace(',', '.')

    if step == 'wall_round_length':
        try:
            length_cm = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        if length_cm <= 0 or length_cm > 5000:
            await update.message.reply_text("❌ Длина от 1 до 5000 см")
            return
        context.user_data['wall_length'] = length_cm
        context.user_data['waiting_for'] = None
        step_num = context.user_data.get('wall_step') or 1
        _save_wall_draft(context, room_id, 'openings')
        wall_names = {1: 'напротив', 2: 'слева', 3: 'у входа', 4: 'справа'}
        pos = wall_names.get(step_num, '?')
        length_cm = context.user_data.get('wall_length') or 0
        openings = get_openings_by_wall(room_id, pos)
        text = f"🧱 *Стена {step_num} — {pos}*\n📏 Длина: *{length_cm} см*\n\n"
        if openings:
            text += f"🚪 *Проёмы ({len(openings)}):*\n"
            for o in openings:
                text += f"  • {format_opening(o)}\n"
        else:
            text += "🚪 *Есть ли на этой стене проёмы?*"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🪟 Окно", callback_data=f"wall_round_open_win_{room_id}"),
             InlineKeyboardButton("🚪 Дверь", callback_data=f"wall_round_open_door_{room_id}")],
            [InlineKeyboardButton("💨 Вентиляция", callback_data=f"wall_round_open_vent_{room_id}")],
            [InlineKeyboardButton("✅ Готово", callback_data=f"wall_round_openings_done_{room_id}")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return

    if step == 'wall_round_angle_val':
        method = context.user_data.get('wall_angle_method') or '60'
        try:
            val = float(text_val)
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
        step_num = context.user_data.get('wall_step') or 1
        remaining = context.user_data.get('wall_remaining_steps') or []
        if remaining:
            first = remaining[0]
            context.user_data['wall_remaining_steps'] = remaining[1:]
            # Для update-версии — вызываем плоскость/нишу через send_message
            if first == 'niche':
                context.user_data['waiting_for'] = 'wall_niche_count'
                await update.message.reply_text(
                    "🕳 *Сколько нишей на этой стене?*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("1", callback_data=f"wall_niche_count_1_{room_id}")],
                        [InlineKeyboardButton("2", callback_data=f"wall_niche_count_2_{room_id}")],
                        [InlineKeyboardButton("3", callback_data=f"wall_niche_count_3_{room_id}")],
                        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                    ])
                )
                return
            elif first == 'rounded':
                context.user_data['waiting_for'] = 'wall_rounded_radius'
                await update.message.reply_text("🔄 *Закругление*\n\n📏 Радиус (СМ):", parse_mode=ParseMode.MARKDOWN)
                return
            elif first == 'wavy':
                context.user_data['waiting_for'] = 'wall_wavy_note'
                await update.message.reply_text("📐 *Разная по высоте*\n\nКомментарий:", parse_mode=ParseMode.MARKDOWN)
                return
            elif first == 'hidden':
                context.user_data['waiting_for'] = 'wall_hidden_note'
                await update.message.reply_text("🔧 *Скрытые коммуникации*\n\nОпиши что и где:", parse_mode=ParseMode.MARKDOWN)
                return
        await _wall_save_and_next(update, context, room_id, step_num)
        return

    if step == 'wall_niche_width':
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        context.user_data['wall_niche_temp'] = {'width': round(val, 2)}
        context.user_data['waiting_for'] = 'wall_niche_depth'
        _save_wall_draft(context, room_id, 'niche_depth')
        room_id = context.user_data.get('wall_room_id')
        import os as _os
        _base = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        _png = _os.path.join(_base, "docs", "images", "niche_depth.png")
        _cap = "🕳 *Ниша — ГЛУБИНА* (СМ):\n\n_Сколько вглубь стены. Например: 40_"
        _kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        if _os.path.exists(_png):
            try:
                with open(_png, "rb") as f:
                    await update.message.reply_photo(photo=f, caption=_cap,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=_kb)
                return
            except Exception:
                pass
        await update.message.reply_text(_cap, parse_mode=ParseMode.MARKDOWN, reply_markup=_kb)
        return

    if step == 'wall_niche_depth':
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        temp = context.user_data.get('wall_niche_temp') or {}
        temp['depth'] = round(val, 2)
        context.user_data['wall_niche_temp'] = temp
        context.user_data['waiting_for'] = 'wall_niche_height'
        room_id = context.user_data.get('wall_room_id')
        import os as _os
        _base = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        _png = _os.path.join(_base, "docs", "images", "niche_height.png")
        _cap = "🕳 *Ниша — ВЫСОТА* (СМ):\n\n_Например: 200_"
        _kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        if _os.path.exists(_png):
            try:
                with open(_png, "rb") as f:
                    await update.message.reply_photo(photo=f, caption=_cap,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=_kb)
                return
            except Exception:
                pass
        await update.message.reply_text(_cap, parse_mode=ParseMode.MARKDOWN, reply_markup=_kb)
        return

    if step == 'wall_niche_height':
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        temp = context.user_data.get('wall_niche_temp') or {}
        temp['height'] = round(val, 2)
        # Спрашиваем — ровная или неровная
        context.user_data['wall_niche_temp'] = temp
        context.user_data['waiting_for'] = 'wall_niche_plane'
        room_id = context.user_data.get('wall_room_id')
        await update.message.reply_text(
            "🕳 *Ниша ровная или неровная по высоте?*\n\n"
            "Если верх шире низа — неровная.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_niche_plane_rect_{room_id}")],
                [InlineKeyboardButton("📏 Неровная", callback_data=f"wall_niche_plane_irr_{room_id}")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
            ])
        )
        return

    if step == 'wall_niche_top_width':
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        temp = context.user_data.get('wall_niche_temp') or {}
        temp['width_top'] = round(val, 2)
        context.user_data['wall_niche_temp'] = temp
        context.user_data['waiting_for'] = 'wall_niche_top_depth'
        await update.message.reply_text("🕳 *Глубина сверху* (СМ):", parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'wall_niche_top_depth':
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        temp = context.user_data.get('wall_niche_temp') or {}
        temp['depth_top'] = round(val, 2)
        # Сохраняем нишу
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
                f"✅ Ниша {current}\n\n🕳 *Ниша {current + 1}* — Ширина (СМ):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        await update.message.reply_text("✅ Все ниши записаны")
        await _show_wall_plane(update, context, room_id)
        return

    if step == 'wall_niche_height_old_unused':
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        temp = context.user_data.get('wall_niche_temp') or {}
        temp['height'] = round(val, 2)
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
                f"✅ Ниша {current}\n\n🕳 *Ниша {current + 1}* — Ширина (СМ):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        await update.message.reply_text("✅ Все ниши записаны")
        await _show_wall_plane(update, context, room_id)
        return

    if step == 'wall_rounded_radius':
        context.user_data['wall_flags'] = context.user_data.get('wall_flags') or {}
        context.user_data['wall_flags']['rounded'] = True
        await _show_wall_plane(update, context, room_id)
        return

    if step == 'wall_wavy_note':
        context.user_data['wall_flags'] = context.user_data.get('wall_flags') or {}
        context.user_data['wall_flags']['wavy'] = True
        await _show_wall_plane(update, context, room_id)
        return

    if step == 'wall_hidden_note':
        context.user_data['wall_flags'] = context.user_data.get('wall_flags') or {}
        context.user_data['wall_flags']['hidden'] = True
        await _show_wall_plane(update, context, room_id)
        return

    if step in ('wall_round_plane_bottom', 'wall_round_plane_middle', 'wall_round_plane_top'):
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        if step == 'wall_round_plane_bottom':
            context.user_data['wall_bottom'] = val
            context.user_data['waiting_for'] = 'wall_round_plane_middle'
            await update.message.reply_text("📏 *Середина стены* (СМ):", parse_mode=ParseMode.MARKDOWN)
        elif step == 'wall_round_plane_middle':
            context.user_data['wall_middle'] = val
            context.user_data['waiting_for'] = 'wall_round_plane_top'
            await update.message.reply_text("📏 *Верх стены* (СМ):", parse_mode=ParseMode.MARKDOWN)
        else:
            context.user_data['wall_top'] = val
            context.user_data['wall_plane'] = 'wavy'
            context.user_data['waiting_for'] = 'wall_round_length'
            await update.message.reply_text("📏 *Длина стены* (СМ):", parse_mode=ParseMode.MARKDOWN)
        return


async def _handle_wall_round_opening_input(update, context, step):
    """Ввод размеров проёма при обходе."""
    room_id = context.user_data.get('wall_room_id')
    otype = context.user_data.get('wall_round_opening_type') or 'window'
    wall_pos = context.user_data.get('wall_round_opening_wall') or 'напротив'
    text_val = (update.message.text or '').strip().replace(',', '.')
    try:
        val = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Нужно число")
        return

    if step == 'wall_round_opening_width':
        context.user_data['wall_round_opening_width'] = val
        context.user_data['waiting_for'] = 'wall_round_opening_height'
        await update.message.reply_text("📏 *Высота проёма* (СМ):", parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'wall_round_opening_height':
        if otype == 'vent':
            final_width = 100
            final_height = 100
            final_sill = val
        else:
            final_width = context.user_data.get('wall_round_opening_width') or 0
            final_height = val
            final_sill = None
        add_opening(room_id=room_id, opening_type=otype, wall_pos=wall_pos,
                    width=final_width, height=final_height, sill_height=final_sill,
                    created_by=update.effective_user.id if update.effective_user else None)
        for k in ['wall_round_opening_type', 'wall_round_opening_width', 'wall_round_opening_height']:
            context.user_data[k] = None
        step_num = context.user_data.get('wall_step') or 1
        openings = get_openings_by_wall(room_id, wall_pos)
        length_cm = context.user_data.get('wall_length') or 0
        text = f"✅ *Проём добавлен!*\n\n🧱 Стена {step_num}\n📏 Длина: {length_cm} см\n\n🚪 *Проёмы ({len(openings)}):*\n"
        for o in openings:
            text += f"  • {format_opening(o)}\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🪟 Окно", callback_data=f"wall_round_open_win_{room_id}"),
             InlineKeyboardButton("🚪 Дверь", callback_data=f"wall_round_open_door_{room_id}")],
            [InlineKeyboardButton("💨 Вентиляция", callback_data=f"wall_round_open_vent_{room_id}")],
            [InlineKeyboardButton("✅ Готово", callback_data=f"wall_round_openings_done_{room_id}")],
        ])
        context.user_data['waiting_for'] = None
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return


# ============================================================
# ОБЪЕКТЫ — редактирование/удаление
# ============================================================

async def handle_object_callback(update, context, data):
    """Обработчик obj_* — вызывается из commands.py или добавь pattern в bot.py."""
    from modules.objects import get_object, delete_object, update_object

    if data.startswith("obj_del_"):
        object_id = int(data.replace("obj_del_", ""))
        obj = get_object(object_id)
        name = obj['name'] if obj else '?'
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"obj_delok_{object_id}")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"obj_{object_id}")],
        ])
        await update.callback_query.edit_message_text(
            f"🗑 *Удалить объект «{name}»?*\n\n"
            f"Будут удалены: комнаты, замеры, проёмы, коммуникации.\n"
            f"Задачи и финансы — отвязаны (не удалены).",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb
        )
        return True

    if data.startswith("obj_delok_"):
        object_id = int(data.replace("obj_delok_", ""))
        delete_object(object_id)
        await update.callback_query.edit_message_text(
            "✅ Объект удалён",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    if data.startswith("obj_rename_"):
        object_id = int(data.replace("obj_rename_", ""))
        context.user_data['waiting_for'] = 'obj_rename'
        context.user_data['obj_rename_id'] = object_id
        # (уже есть)
        await update.callback_query.edit_message_text(
            "✏️ *Новое имя объекта:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"obj_{object_id}")],
            ])
        )
        return True

    return False
