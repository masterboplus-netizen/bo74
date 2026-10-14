"""Callback-хендлеры домена «разное» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_callback).
Блоки: personal_cat_, menu_dashboard, menu_help.

Роутер try_handle(data, query, context) -> bool.
True = обработано, вызывающий делает return.

Замечание: personal_cat_ временно здесь — до создания callbacks/personal.py
(вместе с personal_all, personal_add, exp_type_personal_).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from modules.personal import add_personal_expense
from modules.dashboard_link import get_dashboard_url
from handlers.commands.start import _help_text


async def try_handle(data: str, query, context) -> bool:
    """Обрабатывает misc-callback-и. True = обработано."""

    if data.startswith("personal_cat_"):
        parts = data.replace("personal_cat_", "").split("_", 1)
        amount = int(parts[0])
        category = parts[1]
        add_personal_expense(amount, category)
        context.user_data['pending_personal_expense'] = None
        context.user_data['waiting_for'] = None
        await query.edit_message_text(
            f"✅ Личный расход {amount} ₽ ({category}) записан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 К личным", callback_data="menu_personal")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    if data == "menu_dashboard":
        url = get_dashboard_url()
        await query.edit_message_text(
            f"🌐 Дашборд Бо 7.7\n\n"
            f"Нажми кнопку ниже, чтобы открыть:\n\n"
            f"📱 Совет: добавь на главный экран телефона",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Открыть дашборд", url=url)],
                [InlineKeyboardButton("⬅️Назад", callback_data="menu_back")]
            ])
        )
        return True

    if data == "menu_help":
        await query.edit_message_text(
            _help_text(),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️Назад", callback_data="menu_back")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return True

    return False
