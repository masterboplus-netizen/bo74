"""text/parse.py — старая логика parse_message, вынесенная из _legacy.py."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from modules.parser import parse_message, parse_amount
from modules.objects import get_all_objects, create_object, get_object_by_name, get_object
from modules.tasks import create_task, get_active_tasks, close_task, get_tasks_by_object
from modules.finance import add_expense, add_income, get_finance_summary

from handlers.commands.choose_expense import (
    handle_choose_object, make_choose_keyboard,
    expense_category_keyboard, handle_category,
)
from handlers.commands.utils import parse_date


async def try_handle(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    result = parse_message(text)
    action = result.get('action')

    if action == 'ask_expense_type':
        amount = result['amount']
        context.user_data['ask_expense_amount'] = amount
        await update.message.reply_text(
            f"💰 {amount} ₽ — куда записать?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Личный расход", callback_data=f"exp_type_personal_{amount}")],
                [InlineKeyboardButton("🏗 Расход по объекту", callback_data=f"exp_type_object_{amount}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_back")],
            ])
        )
        return True

    if action == 'income':
        obj = result['object']
        amount = result['amount']
        category = result.get('category', 'доход')
        add_income(obj['id'], amount, category)
        await update.message.reply_text(f"✅ Доход {amount} ₽ записан")
        return True

    if action == 'expense':
        obj = result['object']
        amount = result['amount']
        category = result['category']
        # Известные категории
        known_categories = ['материалы', 'еда', 'транспорт', 'инструмент', 'сантехника', 'электрика', 'покраска']
        # Если категория явно из списка — записываем сразу
        if category and category in known_categories:
            add_expense(obj['id'], amount, category)
            await update.message.reply_text(
                f"✅ Расход {amount} ₽ ({category}) добавлен в «{obj['name']}»"
            )
            return True
        # Иначе — спрашиваем категорию
        context.user_data['pending_expense'] = {
            'object_id': obj['id'],
            'object_name': obj['name'],
            'amount': amount
        }
        await update.message.reply_text(
            f"💰 Расход {amount} ₽ в «{obj['name']}»\n\nЗа что?",
            reply_markup=expense_category_keyboard()
        )
        return True

    if action == 'add_task':
        obj = result['object']
        title = result['title']
        tid = create_task(obj['id'], title)
        await update.message.reply_text(
            f"✅ Задача «{title}» добавлена в «{obj['name']}». ID: {tid}"
        )
        return True

    # TODO: остальные actions (expense, add_task, done_task, done_task_not_found,
    #       finance, list_tasks, list_objects, choose_object) — перенести из _legacy.py (393–474)

    if action == 'done_task':
        obj = result['object']
        task = result['task']
        close_task(task['id'], user_id=update.effective_user.id)
        await update.message.reply_text(
            f"✅ Задача «{task['title']}» в «{obj['name']}» выполнена!"
        )
        return True

    if action == 'done_task_not_found':
        obj = result['object']
        await update.message.reply_text(
            f"❌ В «{obj['name']}» не нашёл задачу с «{result['query']}». Посмотри /tasks"
        )
        return True

    if action == 'finance':
        obj = result['object']
        f = get_finance_summary(obj['id'])
        await update.message.reply_text(
            f"💰 {obj['name']}\n\nДоход: {f['income']} ₽\nРасход: {f['expense']} ₽\nБаланс: {f['balance']} ₽"
        )
        return True

    if action == 'list_tasks':
        tasks = get_active_tasks()
        if not tasks:
            await update.message.reply_text("✅ Нет активных задач")
            return True
        text_out = f"📋 Активные задачи ({len(tasks)}):\n\n"
        for t in tasks[:15]:
            text_out += f"• #{t['id']} {t['title']}\n"
        await update.message.reply_text(text_out)
        return True

    if action == 'list_objects':
        objs = get_all_objects()
        text_out = f"🏗️ Объекты ({len(objs)}):\n\n"
        for o in objs:
            text_out += f"• {o['name']}\n"
        await update.message.reply_text(text_out)
        return True

    if action == 'choose_object':
        objects = result['objects']
        intent = result.get('intent', 'expense')
        amount = result.get('amount')
        category = result.get('category', 'прочее')
        if intent == 'add_task':
            context.user_data['pending_task_title'] = result.get('title') or result.get('original_text', '')
        await update.message.reply_text(
            f"🤔 Нашёл несколько объектов. Какой именно?",
            reply_markup=make_choose_keyboard(objects, intent, amount, category)
        )
        return True

    return False
