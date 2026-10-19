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

