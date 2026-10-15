"""Callback-хендлеры домена «личные расходы» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_callback).
Блоки: menu_personal, personal_today, personal_week, personal_month,
personal_all, personal_add, exp_type_personal_.

Роутер try_handle(data, query, context) -> bool.
True = обработано, вызывающий делает return.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from handlers.commands.personal import format_personal_summary, personal_keyboard


async def try_handle(data: str, query, context) -> bool:
    """Обрабатывает personal-callback-и. True = обработано."""

    if data == "menu_personal":
        await query.edit_message_text(
            format_personal_summary('month'),
            reply_markup=personal_keyboard()
        )
        return True

    if data == "personal_today":
        try:
            await query.edit_message_text(
                format_personal_summary('today'),
                reply_markup=personal_keyboard()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"personal_today: {_e}", flush=True)
        return True

    if data == "personal_week":
        try:
            await query.edit_message_text(
                format_personal_summary('week'),
                reply_markup=personal_keyboard()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"personal_week: {_e}", flush=True)
        return True

    if data == "personal_month":
        try:
            await query.edit_message_text(
                format_personal_summary('month'),
                reply_markup=personal_keyboard()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"personal_month: {_e}", flush=True)
        return True

    if data == "personal_all":
        try:
            await query.edit_message_text(
                format_personal_summary('all'),
                reply_markup=personal_keyboard()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"personal_all: {_e}", flush=True)
        return True

    if data == "personal_add":
        context.user_data['waiting_for'] = 'personal_expense_text'
        await query.edit_message_text(
            "💸 Новый личный расход\n\nНапиши сумму и категорию. Например:\n"
            "«300 еда»\n«1500 инструмент»\n«200 такси»",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_personal")]
            ])
        )
        return True

    if data.startswith("exp_type_personal_"):
        amount = int(data.replace("exp_type_personal_", ""))
        context.user_data['pending_personal_expense'] = amount
        context.user_data['waiting_for'] = 'personal_expense_category'
        await query.edit_message_text(
            f"💸 Личный расход {amount} ₽\n\nЗа что?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🍔 Еда", callback_data=f"personal_cat_{amount}_еда")],
                [InlineKeyboardButton("🚕 Транспорт", callback_data=f"personal_cat_{amount}_транспорт")],
                [InlineKeyboardButton("🏠 Жильё", callback_data=f"personal_cat_{amount}_жильё")],
                [InlineKeyboardButton("💊 Медицина", callback_data=f"personal_cat_{amount}_медицина")],
                [InlineKeyboardButton("👕 Одежда", callback_data=f"personal_cat_{amount}_одежда")],
                [InlineKeyboardButton("📱 Связь", callback_data=f"personal_cat_{amount}_связь")],
                [InlineKeyboardButton("📦 Прочее", callback_data=f"personal_cat_{amount}_прочее")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_back")],
            ])
        )
        return True

    return False
