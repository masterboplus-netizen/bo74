"""Callbacks домена Финансы — вынесено из _legacy.py (сессия 16)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from modules.objects import get_object
from modules.finance import get_finance_summary
from handlers.commands.finance import format_finance_summary, finance_keyboard, format_money


async def try_handle(data: str, query, context) -> bool:
    """Обработка callback'ов Финансы."""

    # === menu_finance : меню финансов ===
    if data == "menu_finance":
        try:
            await query.edit_message_text(
                format_finance_summary(),
                reply_markup=finance_keyboard()
            )
        except Exception:
            pass
        return True

    # === finobj_* : финансы объекта ===
    if data.startswith("finobj_"):
        object_id = int(data.split("_")[1])
        obj = get_object(object_id)
        if not obj:
            try:
                await query.edit_message_text("❌ Объект не найден")
            except Exception:
                pass
            return True
        f = get_finance_summary(object_id)
        try:
            await query.edit_message_text(
                f"💰 **{obj['name']}**\n\n"
                f"Доход: {format_money(f['income'])} ₽\n"
                f"Расход: {format_money(f['expense'])} ₽\n"
                f"Баланс: {format_money(f['balance'])} ₽",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К финансам", callback_data="menu_finance")],
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            pass
        return True

    return False
