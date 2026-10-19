"""interfaces/telegram/rooms_core.py — каркас: комнаты, карточки, высота."""
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room, create_room, delete_room, update_room
from core.rooms_ui import format_room_card, format_rooms_list
from core.measures import get_measures, get_walls_ordered
from core.db import fetchone, fetchall, commit as db_commit
from core import spec as core_spec

def _image_path(filename):
    """Путь к PNG-схеме."""
    if not filename:
        return None
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "docs", "images", filename)


from core.room_objects import get_room_objects, format_room_object

def rooms_list_keyboard(object_id):
    """Клавиатура списка комнат объекта."""
    rooms = get_rooms(object_id)
    buttons = []
    for r in rooms:
        mark = "🏠" if r.get('is_default') else "📦"
        buttons.append([InlineKeyboardButton(f"{mark} {r['name']}", callback_data=f"room_{r['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить комнату", callback_data=f"room_add_{object_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")])
    return InlineKeyboardMarkup(buttons)



def room_card_keyboard(room_id):
    """Клавиатура карточки комнаты."""
    room = get_room(room_id)
    object_id = room['object_id'] if room else 0
    walls = get_walls_ordered(room_id)
    height_ok = bool(room.get('height_bottom') and room.get('height_middle') and room.get('height_top'))
    walls_ok = len(walls) >= core_spec.get_total_walls()

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
        [InlineKeyboardButton("💰 Смета комнаты", callback_data=f"room_estimate_{room_id}")],
        [InlineKeyboardButton("📊 Отчёты", callback_data=f"room_reports_{room_id}"),
         InlineKeyboardButton("📤 Экспорт", callback_data=f"room_export_{room_id}")],
        [InlineKeyboardButton("⚡ Группы ЭОМ", callback_data=f"room_groups_{room_id}")],
        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"room_rename_{room_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"room_del_{room_id}")],
        [InlineKeyboardButton("⬅️ К комнатам", callback_data=f"rooms_list_obj_{object_id}")],
    ])


# ============================================================
# ПОКАЗ КОМНАТ
# ============================================================


async def show_rooms_list(update, context, object_id):
    """Показ списка комнат объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else '—'
    text = f"📦 *Комнаты «{obj_name}»*\n\n{format_rooms_list(object_id)}"
    kb = rooms_list_keyboard(object_id)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            try:
                await update.callback_query.message.delete()
            except Exception:
                pass
            await update.callback_query.message.chat.send_message(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )



async def show_room_card(update, context, room_id):
    """Показ карточки комнаты."""
    room = get_room(room_id)
    if not room:
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Комната не найдена")
        else:
            await update.message.reply_text("❌ Комната не найдена")
        return
    text = format_room_card(room_id)
    kb = room_card_keyboard(room_id)

    if update.callback_query:
        query = update.callback_query
        has_photo = bool(getattr(query.message, "photo", None))
        if has_photo:
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
                if "message is not modified" in str(e).lower():
                    return
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await query.message.chat.send_message(
                    text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
                )
    else:
        await update.message.reply_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )


# ============================================================
# МАСТЕР ВЫСОТЫ (3 точки)
# ============================================================


async def _send_height_scheme(message, context, room_id, step, caption, kb_extra=None):
    """Отправка PNG-схемы высоты."""
    kb_rows = list(kb_extra or [])
    kb_rows.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")])
    kb = InlineKeyboardMarkup(kb_rows)
    png = _image_path(f"height_scheme_step{step}.png")
    if png and os.path.exists(png):
        try:
            with open(png, "rb") as f:
                await message.reply_photo(
                    photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            return
        except Exception as e:
            print(f"⚠️ height scheme: {e}", flush=True)
    await message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)



async def _show_height_step(target, context, room_id, method=None, step=1):
    """Экран шага высоты.

    target — Update или CallbackQuery. Если CallbackQuery — сначала
    пытаемся edit, при неудаче — новое сообщение.
    """
    captions = {
        1: (
            "📏 *Высота — шаг 1*\n\n"
            "📍 *Точка 1 — ЦЕНТР комнаты*\n\n"
            "Встань в центре комнаты, приложи дальномер к полу, наведи на потолок.\n\n"
            "Введи результат в СМ:\n\n_Например: 305_"
        ),
        2: (
            "📏 *Высота — шаг 2*\n\n"
            "📍 *Точка 2 — у ЛЕВОГО угла*\n\n"
            "Введи результат в СМ:\n\n_Например: 304_"
        ),
        3: (
            "📏 *Высота — шаг 3*\n\n"
            "📍 *Точка 3 — у ПРАВОГО угла*\n\n"
            "Введи результат в СМ:\n\n_Например: 306_"
        ),
    }
    caption = captions.get(step, captions[1])
    kb_extra = [
        [InlineKeyboardButton("✅ Все три одинаковые", callback_data=f"room_height_same_{room_id}")],
    ]
    context.user_data['waiting_for'] = 'room_height_point'
    context.user_data['height_room_id'] = room_id
    context.user_data['height_step'] = step

    # target — callback (query) или Update
    if hasattr(target, 'message') and hasattr(target, 'edit_message_text'):
        # Это CallbackQuery
        try:
            await target.message.delete()
        except Exception:
            pass
        await _send_height_scheme(target.message, context, room_id, step, caption, kb_extra)
    elif hasattr(target, 'message'):
        # Это Update
        await _send_height_scheme(target.message, context, room_id, step, caption, kb_extra)


# ============================================================
# ОБХОД СТЕН: ПОКАЗ ЭКРАНОВ
# ============================================================



# === Дополнительные функции каркаса ===

async def _handle_height_callback(query, context, data):
    """Обработка callback'ов высоты."""
    if data.startswith("room_height_ask_"):
        room_id = int(data.replace("room_height_ask_", ""))
        context.user_data['height_room_id'] = room_id
        try:
            await query.edit_message_text(
                "📏 *Высота потолка*\n\nВысота одинаковая во всей комнате\nили отличается в разных точках?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Одинаковая (1 замер)", callback_data=f"room_height_same_start_{room_id}")],
                    [InlineKeyboardButton("📏 Разная (3 замера)", callback_data=f"room_height_three_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("room_height_same_start_"):
        room_id = int(data.replace("room_height_same_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_mode'] = 'same'
        context.user_data['waiting_for'] = 'room_height_same'
        try:
            await query.message.delete()
        except Exception:
            pass
        caption = (
            "📏 *Высота потолка*\n\n"
            "Введи ОДНУ цифру в СМ — она применится ко всем точкам:\n\n"
            "_Например: 305_"
        )
        png = _image_path("height_scheme_step1.png")
        if png and os.path.exists(png):
            try:
                with open(png, "rb") as f:
                    await query.message.chat.send_photo(
                        photo=f, caption=caption, parse_mode=ParseMode.MARKDOWN
                    )
                return True
            except Exception:
                pass
        await query.message.chat.send_message(caption, parse_mode=ParseMode.MARKDOWN)
        return True

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
        return True

    if data.startswith("room_height_same_"):
        # Старое — уже обрабатывается вводом
        return True

    return False


# ============================================================
# ОБРАБОТЧИК ВВОДА (главный)
# ============================================================



# === Дополнительные функции каркаса ===

async def _show_room_progress(query, context, room_id):
    room = get_room(room_id)
    if not room:
        return
    walls = get_walls_ordered(room_id)
    h_bottom = room.get('height_bottom')
    h_avg = room.get('height')
    height_ok = bool(h_bottom and room.get('height_middle') and room.get('height_top'))
    walls_ok = len(walls) >= core_spec.get_total_walls()
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
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Продолжить замер", callback_data=f"room_start_{room_id}")],
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
    except Exception:
        pass



async def _show_room_measures(query, context, room_id):
    measures = get_measures(room_id)
    if not measures:
        try:
            await query.edit_message_text(
                "📐 Размеров пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return
    lines = [f"📐 *Размеры комнаты* ({len(measures)}):\n"]
    for m in measures:
        lines.append(format_measure(m, show_area=True))
    areas = calculate_room_areas(room_id)
    lines.append("")
    if areas.get('walls_net') is not None:
        lines.append(f"Стены: {areas['walls_net']} м²")
    lines.append(f"Пол: {areas['floor']} м²")
    try:
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
    except Exception:
        pass



async def _show_room_objects(query, context, room_id):
    objects = get_room_objects(room_id)
    if not objects:
        try:
            await query.edit_message_text(
                "🪑 Мебели/техники пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return
    lines = [f"🪑 *Мебель/техника* ({len(objects)}):\n"]
    for o in objects:
        lines.append(format_room_object(o))
    try:
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
    except Exception:
        pass


# ============================================================
# ROOM_START И ВЫСОТА
# ============================================================



# === Старт замера ===

async def _handle_room_start(query, context, room_id):
    """Начало/продолжение замера комнаты."""
    print(f"🟣 _handle_room_start: room_id={room_id}", flush=True)
    room = get_room(room_id)
    if not room:
        try:
            await query.edit_message_text("❌ Комната не найдена")
        except Exception:
            pass
        return

    h_bottom = room.get('height_bottom')
    h_middle = room.get('height_middle')
    h_top = room.get('height_top')
    height_ok = bool(h_bottom and h_middle and h_top)
    walls = get_walls_ordered(room_id)
    walls_ok = len(walls) >= core_spec.get_total_walls()

    # === ПРОВЕРКА: Сколько стен? ===
    if height_ok and not walls_ok and not context.user_data.get('total_walls_asked'):
        context.user_data['total_walls_asked'] = True
        context.user_data['wall_room_id'] = room_id
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("3", callback_data=f"room_total_walls_{room_id}_3"),
             InlineKeyboardButton("4", callback_data=f"room_total_walls_{room_id}_4")],
            [InlineKeyboardButton("5", callback_data=f"room_total_walls_{room_id}_5"),
             InlineKeyboardButton("6", callback_data=f"room_total_walls_{room_id}_6")],
            [InlineKeyboardButton("7", callback_data=f"room_total_walls_{room_id}_7"),
             InlineKeyboardButton("8", callback_data=f"room_total_walls_{room_id}_8")],
            [InlineKeyboardButton("✏️ Другое", callback_data=f"room_total_walls_{room_id}_other")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        try:
            await query.edit_message_text("📐 *Сколько стен в комнате?*\n\n_Например: 4_", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            pass
        return

    # === ЭТАП ВЫСОТЫ ===
    if not height_ok:
        if h_bottom and not (h_middle and h_top):
            context.user_data['height_room_id'] = room_id
            context.user_data['height_step'] = 2 if not h_middle else 3
            context.user_data['height_bottom'] = h_bottom
            context.user_data['height_middle'] = h_middle
            context.user_data['height_top'] = h_top
            context.user_data['waiting_for'] = 'room_height_point'
            try:
                await query.edit_message_text(
                    f"🚀 *Продолжаем замер*\n\n📏 Шаг 1: Высота\n✅ Точка 1 (центр): {h_bottom} см",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Продолжить", callback_data=f"room_height_three_start_{room_id}")],
                        [InlineKeyboardButton("🔄 Заново", callback_data=f"room_height_ask_{room_id}")],
                    ])
                )
            except Exception:
                pass
            return
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        try:
            await query.edit_message_text(
                f"🚀 *Мастер замеров*\n\n📏 *Шаг 1 из 3: Высота потолка*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Начать", callback_data=f"room_height_ask_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    # === ЭТАП ОБХОДА СТЕН ===
    if not walls_ok:
        # Спросить количество стен (если ещё не задано в этом сеансе)
        if not context.user_data.get('total_walls_asked'):
            context.user_data['total_walls_asked'] = True
            context.user_data['waiting_for'] = 'total_walls'
            try:
                await query.edit_message_text(
                    "📐 Сколько стен в комнате?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("3", callback_data=f"room_total_walls_{room_id}_3")],
                        [InlineKeyboardButton("4", callback_data=f"room_total_walls_{room_id}_4")],
                        [InlineKeyboardButton("5", callback_data=f"room_total_walls_{room_id}_5")],
                        [InlineKeyboardButton("6", callback_data=f"room_total_walls_{room_id}_6")],
                        [InlineKeyboardButton("Другое", callback_data=f"room_total_walls_{room_id}_other")],
                        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                    ])
                )
            except Exception as e:
                print("total_walls ask: " + str(e), flush=True)
            return
        # ⬇⬇⬇ ГЛАВНЫЙ ФИКС ⬇⬇⬇
        # Проверяем черновик — если есть незавершённая стена, восстанавливаем её
        try:
            draft = fetchone("SELECT step_name, step_num FROM wall_drafts WHERE room_id = ?", (room_id,))
        except Exception as e:
            print(f"⚠️ чтение wall_drafts: {e}", flush=True)
            draft = None

        # sqlite3.Row не поддерживает .get() — конвертируем в dict
        if draft:
            try:
                draft = dict(draft)
            except Exception:
                pass

        if draft and draft.get('step_name'):
            print(f"🟢 _handle_room_start: НАЙДЕН ЧЕРНОВИК step_name={draft['step_name']!r}, step_num={draft['step_num']!r} — восстанавливаем", flush=True)
            context.user_data['wall_room_id'] = room_id
            start_walls_round(room_id)
            await _wall_round_start(query, context, room_id)
            return

        # Черновика нет — начинаем с начала
        print(f"🟠 _handle_room_start: черновика нет, начинаем с галочек стены 1", flush=True)
        _reset_wall_state(context, keep_step_num=1)
        state = _get_wall_state(context)
        state['step_num'] = 1
        state['step_name'] = 'flags'
        context.user_data['wall_room_id'] = room_id
        start_walls_round(room_id)
        await _show_wall_step(query, context, room_id, 1, phase='flags', use_photo=True)
        return

    # === ФИНИШ (все стены) ===
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
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
    except Exception:
        pass



