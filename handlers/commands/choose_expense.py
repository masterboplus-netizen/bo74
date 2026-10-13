"""Выбор объекта для расхода + категории расхода."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from modules.objects import get_object, get_all_objects, get_object_by_name
from modules.finance import add_expense
from modules.tasks import create_task


async def handle_choose_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает кнопки выбора объекта"""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Формат: choose_obj_<intent>_<object_id>_<amount>_<category>
    # Для intent='add_task' формат: choose_obj_add_task_<object_id>_<amount>_<category>
    parts = data.split('_')
    # Определяем intent (учитываем 'add_task' с подчёркиванием)
    if len(parts) > 3 and parts[2] == 'add' and parts[3] == 'task':
        intent = 'add_task'
        shift = 2
    else:
        intent = parts[2]
        shift = 1
    object_id_str = parts[2 + shift]
    amount_str = parts[3 + shift] if len(parts) > 3 + shift else 'none'
    category = parts[4 + shift] if len(parts) > 4 + shift else 'прочее'
    
    # Задача без объекта
    if intent == 'add_task' and object_id_str == 'none':
        title = context.user_data.get('pending_task_title', '')
        tid = create_task(None, title)
        context.user_data.pop('pending_task_title', None)
        await query.edit_message_text(f"✅ Задача «{title}» добавлена без объекта. ID: {tid}")
        return
    
    object_id = int(object_id_str)
    amount = int(amount_str) if amount_str != 'none' else None

    obj = get_object(object_id)
    if not obj:
        await query.edit_message_text("❌ Объект не найден")
        return

    if intent == 'expense' and amount:
        # Сохраняем в user_data и спрашиваем категорию
        context.user_data['pending_expense'] = {
            'object_id': obj['id'],
            'object_name': obj['name'],
            'amount': amount
        }
        await query.edit_message_text(
            f"💰 Расход {amount} ₽ в «{obj['name']}»\n\nЗа что?",
            reply_markup=expense_category_keyboard()
        )
        return

    if intent == 'add_task':
        title = context.user_data.get('pending_task_title', '')
        tid = create_task(obj['id'], title)
        await query.edit_message_text(
            f"✅ Задача «{title}» добавлена в «{obj['name']}». ID: {tid}"
        )
        return

    if intent == 'done_task':
        tasks = get_tasks_by_object(obj['id'])
        for t in tasks:
            if t['status'] != 'done':
                close_task(t['id'], user_id=update.effective_user.id)
                await query.edit_message_text(
                    f"✅ Задача «{t['title']}» в «{obj['name']}» выполнена!"
                )
                return
        await query.edit_message_text(f"❌ В «{obj['name']}» нет открытых задач")
        return


def make_choose_keyboard(objects, intent, amount=None, category=None):
    """Создаёт клавиатуру выбора объекта"""
    buttons = []
    for o in objects:
        if amount:
            cb = f"choose_obj_{intent}_{o['id']}_{amount}_{category}"
        else:
            cb = f"choose_obj_{intent}_{o['id']}_none_none"
        buttons.append([InlineKeyboardButton(f"🏗️ {o['name']}", callback_data=cb)])
    # Кнопка 'Без объекта' — только для задач
    if intent == 'add_task':
        buttons.append([InlineKeyboardButton("🚫 Без объекта", callback_data="choose_obj_add_task_none_none_none")])
    
    return InlineKeyboardMarkup(buttons)


# === ВЫБОР КАТЕГОРИИ РАСХОДА ===

def expense_category_keyboard():
    """Клавиатура категорий расходов"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧱 Материалы", callback_data="cat_материалы")],
        [InlineKeyboardButton("🍔 Еда", callback_data="cat_еда")],
        [InlineKeyboardButton("🚕 Транспорт", callback_data="cat_транспорт")],
        [InlineKeyboardButton("🔧 Инструмент", callback_data="cat_инструмент")],
        [InlineKeyboardButton("📦 Прочее", callback_data="cat_прочее")],
    ])


async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора категории"""
    query = update.callback_query
    await query.answer()

    pending = context.user_data.get('pending_expense')
    if not pending:
        await query.edit_message_text("❌ Данные о расходе потеряны")
        return

    category = query.data.replace("cat_", "")
    add_expense(pending['object_id'], pending['amount'], category)
    await query.edit_message_text(
        f"✅ Расход {pending['amount']} ₽ ({category}) добавлен в «{pending['object_name']}»"
    )
    context.user_data['pending_expense'] = None


# === ФИНАНСЫ: СВОДКА + КНОПКИ ===



