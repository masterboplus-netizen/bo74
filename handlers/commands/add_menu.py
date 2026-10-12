"""Меню ➕ Добавить (новый объект / задача / расход)."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from modules.objects import get_object, get_all_objects
from handlers.commands.objects import (
    choose_object_for_task_keyboard, choose_object_for_expense_keyboard
)


async def handle_add_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка меню «➕ Добавить»"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_add":
        await query.edit_message_text(
            "➕ Что добавить?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ Новый объект", callback_data="add_object")],
                [InlineKeyboardButton("📋 Новая задача", callback_data="add_task")],
                [InlineKeyboardButton("💰 Расход", callback_data="add_expense")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
            ])
        )
        return

    if data == "add_object":
        context.user_data['waiting_for'] = 'new_object'
        await query.edit_message_text(
            "🏗️ Напиши название объекта:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_add")]
            ])
        )
        return

    if data == "add_task":
        context.user_data['waiting_for'] = 'new_task'
        await query.edit_message_text(
            "📋 Выбери объект:",
            reply_markup=choose_object_for_task_keyboard()
        )
        return

    if data == "add_expense":
        context.user_data['waiting_for'] = 'new_expense'
        await query.edit_message_text(
            "💰 Выбери объект:",
            reply_markup=choose_object_for_expense_keyboard()
        )
        return

    if data.startswith("newtask_obj_"):
        object_id = int(data.replace("newtask_obj_", ""))
        obj = get_object(object_id)
        context.user_data['pending_task_object'] = obj
        context.user_data['waiting_for'] = 'new_task_text'
        await query.edit_message_text(
            f"📋 Новая задача в «{obj['name']}»\n\nНапиши задачу:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="add_task")]
            ])
        )
        return

    if data.startswith("newexp_obj_"):
        object_id = int(data.replace("newexp_obj_", ""))
        obj = get_object(object_id)
        context.user_data['pending_expense_object'] = obj
        context.user_data['waiting_for'] = 'new_expense_text'
        await query.edit_message_text(
            f"💰 Новый расход в «{obj['name']}»\n\nНапиши сумму и что купил:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="add_expense")]
            ])
        )
        return

