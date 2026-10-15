"""Text-хендлеры домена «rooms» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_text).
Блоки: room_name, wall_question.

Роутер try_handle(update, context, text) -> bool.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode


async def try_handle(update, context, text: str) -> bool:
    """Обрабатывает text-команды rooms. True = обработано."""

    if context.user_data.get('waiting_for') == 'room_name':
        name = text.strip()
        object_id = context.user_data.get('room_object_id')
        context.user_data['room_name_pending'] = name
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"📦 *Новая комната «{name}»*\n\nКакой тип помещения?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧱 Черновая", callback_data=f"room_type_{object_id}_rough")],
                [InlineKeyboardButton("✨ Чистовая", callback_data=f"room_type_{object_id}_finish")],
                [InlineKeyboardButton("🔶 Промежуточная", callback_data=f"room_type_{object_id}_mid")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"rooms_list_obj_{object_id}")],
            ])
        )
        return True

    # Стена выбрана, но ровная/закругление не нажато → показать кнопки заново
    if context.user_data.get('wall_pos') and context.user_data.get('wall_rounded') is None:
        from interfaces.telegram.rooms import reask_wall_question
        shown = await reask_wall_question(update, context)
        if shown:
            return True

    return False
