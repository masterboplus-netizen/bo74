"""Text-хендлеры домена «объекты» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_text).
Блоки: new_object.

Роутер try_handle(update, context, text) -> bool.
True = обработано, вызывающий делает return.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from modules.objects import create_object


async def try_handle(update, context, text: str) -> bool:
    """Обрабатывает text-команды объектов. True = обработано."""

    if context.user_data.get('waiting_for') == 'new_object':
        object_id = create_object(text, user_id=update.effective_user.id)
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"✅ Объект «{text}» создан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ К объекту", callback_data=f"obj_{object_id}")],
                [InlineKeyboardButton("🏗️ К объектам", callback_data="menu_objects")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    return False
