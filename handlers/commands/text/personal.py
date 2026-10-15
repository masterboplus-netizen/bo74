"""Text-хендлеры домена «личные расходы» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_text).
Блоки: personal_expense_text.

Роутер try_handle(update, context, text) -> bool.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import get_connection
from modules.parser import parse_amount
from modules.personal import add_personal_expense


async def try_handle(update, context, text: str) -> bool:
    """Обрабатывает text-команды личных расходов. True = обработано."""

    # Обработка личного расхода
    if context.user_data.get('waiting_for') == 'personal_expense_text':
        # Разбираем: "300 еда" или "1500 инструмент"
        parts = text.strip().split(maxsplit=1)
        amount_str = parts[0] if parts else ''
        category = parts[1].strip() if len(parts) > 1 else 'прочее'
        # Убираем лишние символы
        amount_str = amount_str.replace('₽', '').replace('р', '').replace('руб', '').strip()
        try:
            amount = int(amount_str)
        except ValueError:
            amount = parse_amount(text)
            if not amount:
                await update.message.reply_text(
                    "❌ Не понял сумму. Попробуй: «300 еда»"
                )
                print(f"⚠️ RETURN на строке 2736", flush=True)
                return True
        add_personal_expense(amount, category)
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"✅ Личный расход {amount} ₽ ({category}) записан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 К личным", callback_data="menu_personal")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        print(f"⚠️ RETURN на строке 2746", flush=True)
        return True

    return False
