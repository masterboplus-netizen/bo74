"""interfaces/telegram/rooms_openings.py — проёмы."""
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room
from core.openings import (add_opening, get_opening, get_openings, get_openings_by_wall, update_opening, delete_opening, format_opening, OPENING_TYPES)
from core.db import fetchone, fetchall, commit as db_commit
from core import spec as core_spec

async def handle_openings_callback(query, context, data):
    """Обработчик callback'ов проёмов."""
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
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass
        return True

    if data.startswith("opening_add_"):
        room_id = int(data.replace("opening_add_", ""))
        buttons = []
        for code, label in OPENING_TYPES.items():
            buttons.append([InlineKeyboardButton(label, callback_data=f"opening_type_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")])
        try:
            await query.edit_message_text(
                "🚪 *Новый проём*\n\nВыбери тип:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_type_"):
        parts = data.replace("opening_type_", "").split("_", 1)
        room_id = int(parts[0])
        otype = parts[1] if len(parts) > 1 else 'window'
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
        try:
            await query.edit_message_text(
                f"🚪 *{label}*\n\nНа какой стене?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_wall_"):
        parts = data.replace("opening_wall_", "").split("_", 1)
        room_id = int(parts[0])
        wall_pos = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['opening_wall_pos'] = wall_pos
        context.user_data['waiting_for'] = 'opening_width'
        try:
            await query.edit_message_text(
                "📏 *Ширина проёма* (СМ):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_show_"):
        opening_id = int(data.replace("opening_show_", ""))
        o = get_opening(opening_id)
        if not o:
            try:
                await query.edit_message_text("❌ Проём не найден")
            except Exception:
                pass
            return True
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
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass
        return True

    if data.startswith("opening_edit_"):
        parts = data.replace("opening_edit_", "").split("_")
        opening_id = int(parts[0])
        field = parts[1] if len(parts) > 1 else 'width'
        context.user_data['opening_edit_id'] = opening_id
        context.user_data['opening_edit_field'] = field
        context.user_data['waiting_for'] = 'opening_edit_value'
        prompts = {'width': 'Ширина', 'height': 'Высота', 'sill': 'Подоконник'}
        try:
            await query.edit_message_text(
                f"✏️ *{prompts.get(field, 'Значение')}* (СМ):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_show_{opening_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_del_"):
        opening_id = int(data.replace("opening_del_", ""))
        o = get_opening(opening_id)
        room_id = o['room_id'] if o else None
        delete_opening(opening_id)
        if room_id:
            try:
                await query.edit_message_text(
                    "✅ Проём удалён",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{room_id}")],
                    ])
                )
            except Exception:
                pass
        return True

    return False


# ============================================================
# ПЛАН КОМНАТЫ (PNG)
# ============================================================


async def _handle_opening_input(update, context, step):
    """Ввод проёмов (отдельных)."""
    text_val = (update.message.text or '').strip().replace(',', '.')
    try:
        val = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Введи число")
        return

    if step == 'opening_width':
        room_id = context.user_data.get('opening_room_id')
        context.user_data['opening_width'] = val
        context.user_data['waiting_for'] = 'opening_height'
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
        try:
            session_id = ensure_session(room_id)
        except Exception:
            session_id = None
        add_opening(room_id=room_id, opening_type=otype, wall_pos=wall_pos,
                    width=width, height=val, session_id=session_id,
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
            "✅ Обновлено!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К проёму", callback_data=f"opening_show_{opening_id}")],
            ])
        )
        return


# ============================================================
# ОБЪЕКТЫ — РЕДАКТИРОВАНИЕ
# ============================================================

