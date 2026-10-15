"""Text-хендлеры домена «финансы» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_text).
Блоки: new_expense_text.

Роутер try_handle(update, context, text) -> bool.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import get_connection
from modules.parser import parse_amount
from modules.finance import add_expense


async def try_handle(update, context, text: str) -> bool:
    """Обрабатывает text-команды финансов. True = обработано."""

    # Обработка создания нового расхода
    if context.user_data.get('waiting_for') == 'new_expense_text':
        obj = context.user_data.get('pending_expense_object')
        if not obj:
            context.user_data['waiting_for'] = None
            await update.message.reply_text(
                "❌ Объект потерялся. Начни заново: «➕ Добавить» → «💰 Расход»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить", callback_data="menu_add")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
            print(f"⚠️ RETURN на строке 2674", flush=True)
            return True
        if obj:
            amount = parse_amount(text)
            if amount:
                category = None
                _tl = text.lower()
                for _c in ["материалы", "еда", "транспорт", "инструмент"]:
                    if _c in _tl:
                        category = _c
                        break
                if category:
                    add_expense(obj['id'], amount, category)
                    context.user_data['waiting_for'] = None
                    context.user_data['pending_expense_object'] = None
                    await update.message.reply_text(
                        f"\u2705 Расход {amount} \u20bd ({category}) добавлен в \u00ab{obj['name']}\u00bb",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("\U0001F4B0 К финансам", callback_data="menu_finance")],
                            [InlineKeyboardButton("\U0001F3E0 Меню", callback_data="menu_back")],
                        ])
                    )
                    print(f"⚠️ RETURN на строке 2695", flush=True)
                    return True
                else:
                    context.user_data['pending_expense'] = {
                        'object_id': obj['id'],
                        'object_name': obj['name'],
                        'amount': amount
                    }
                    context.user_data['waiting_for'] = 'new_expense_category'
                    await update.message.reply_text(
                        f"\U0001F4B0 {amount} \u20bd в \u00ab{obj['name']}\u00bb. За что?",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("\U0001F9F1 Материалы", callback_data="cat_материалы")],
                            [InlineKeyboardButton("\U0001F354 Еда", callback_data="cat_еда")],
                            [InlineKeyboardButton("\U0001F697 Транспорт", callback_data="cat_транспорт")],
                            [InlineKeyboardButton("\U0001F527 Инструмент", callback_data="cat_инструмент")],
                            [InlineKeyboardButton("\U0001F4E6 Прочее", callback_data="cat_прочее")],
                        ])
                    )
                    print(f"⚠️ RETURN на строке 2713", flush=True)
                    return True
            else:
                await update.message.reply_text(
                    "\u274c Не понял сумму. Попробуй: \u00ab500\u00bb"
                )
                print(f"⚠️ RETURN на строке 2718", flush=True)
                return True


    return False
