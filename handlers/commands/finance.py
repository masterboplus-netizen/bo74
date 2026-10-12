"""Финансы объекта: сводка, расходы, клавиатура."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from db import get_connection
from modules.objects import get_object, get_object_by_name
from modules.finance import add_expense, get_finance_summary, get_all_finance_summary


async def finance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если объект не указан — общая сводка с кнопками
    if not context.args:
        await update.message.reply_text(
            format_finance_summary(),
            reply_markup=finance_keyboard()
        )
        return

    obj = get_object_by_name(' '.join(context.args))
    if not obj:
        await update.message.reply_text("❌ Объект не найден")
        return
    f = get_finance_summary(obj['id'])
    await update.message.reply_text(
        f"💰 **{obj['name']}**\n"
        f"Доход: {f['income']} ₽\n"
        f"Расход: {f['expense']} ₽\n"
        f"Баланс: {f['balance']} ₽",
        parse_mode=ParseMode.MARKDOWN
    )


async def add_expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /add_expense <объект> <сумма> [категория]")
        return
    obj = get_object_by_name(context.args[0])
    if not obj:
        await update.message.reply_text(f"❌ Объект «{context.args[0]}» не найден")
        return
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Сумма должна быть числом")
        return
    category = context.args[2] if len(context.args) > 2 else 'прочее'
    add_expense(obj['id'], amount, category)
    await update.message.reply_text(f"✅ Расход {amount} ₽ ({category}) добавлен в «{obj['name']}»")




def format_money(amount):
    """Форматирует число с разделителями"""
    return f"{amount:,}".replace(",", " ")


def finance_keyboard():
    """Клавиатура для сводки финансов"""
    data = get_all_finance_summary()
    buttons = []
    # Кнопки по объектам, у которых есть финансы
    for o in data['objects']:
        if o['income'] > 0 or o['expense'] > 0:
            icon = "🟢" if o['balance'] >= 0 else "🔴"
            buttons.append([InlineKeyboardButton(
                f"{icon} {o['name']}: {o['balance']:+} ₽",
                callback_data=f"finobj_{o['id']}"
            )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(buttons)


def format_finance_summary():
    """Формирует текст общей сводки"""
    data = get_all_finance_summary()
    text = "💰 ФИНАНСЫ\n\n"
    text += "📊 ОБЩАЯ СВОДКА\n"
    text += f"Доход: {format_money(data['total_income'])} ₽\n"
    text += f"Расход: {format_money(data['total_expense'])} ₽\n"
    text += f"Баланс: {format_money(data['total_balance'])} ₽\n\n"
    text += "🏗️ ПО ОБЪЕКТАМ (нажми для деталей):"
    return text


async def show_finance_summary(update, context):
    """Показывает сводку финансов с кнопками"""
    await update.message.reply_text(
        format_finance_summary(),
        reply_markup=finance_keyboard()
    )


