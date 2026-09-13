"""Команды Telegram-бота БО 7.2"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from modules.objects import create_object, get_all_objects, get_object_by_name
from modules.tasks import create_task, get_active_tasks, close_task
from modules.finance import add_expense, get_finance_summary
from config import ADMIN_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🏗️ Объекты", callback_data="menu_objects")],
        [InlineKeyboardButton("📋 Задачи", callback_data="menu_tasks")],
        [InlineKeyboardButton("💰 Финансы", callback_data="menu_finance")],
    ]
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\nЯ БО 7.2 — твой помощник по стройке.\n\n/help — список команд",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 **Команды БО 7.2:**\n\n"
        "/add_object <название> — создать объект\n"
        "/objects — список объектов\n"
        "/add <объект> <задача> — добавить задачу\n"
        "/tasks — активные задачи\n"
        "/done <id> — закрыть задачу\n"
        "/finance <объект> — финансы объекта\n"
        "/add_expense <объект> <сумма> [категория] — добавить расход\n"
        "/help — эта справка",
        parse_mode=ParseMode.MARKDOWN
    )


async def add_object_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Использование: /add_object <название>")
        return
    name = ' '.join(context.args)
    object_id = create_object(name, user_id=update.effective_user.id)
    await update.message.reply_text(f"✅ Объект «{name}» создан. ID: {object_id}")


async def objects_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    objs = get_all_objects()
    if not objs:
        await update.message.reply_text("🏗️ Объектов пока нет")
        return
    lines = ["🏗️ **Объекты:**\n"]
    for o in objs:
        lines.append(f"• {o['name']} ({o['status']}) — ID: {o['id']}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def add_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /add <объект> <задача>")
        return
    obj = get_object_by_name(context.args[0])
    if not obj:
        await update.message.reply_text(f"❌ Объект «{context.args[0]}» не найден")
        return
    title = ' '.join(context.args[1:])
    task_id = create_task(obj['id'], title)
    await update.message.reply_text(f"✅ Задача «{title}» добавлена в «{obj['name']}». ID: {task_id}")


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = get_active_tasks()
    if not tasks:
        await update.message.reply_text("✅ Нет активных задач")
        return
    lines = ["📋 **Активные задачи:**\n"]
    for t in tasks[:15]:
        lines.append(f"• #{t['id']} {t['title']}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Использование: /done <id>")
        return
    try:
        task_id = int(context.args[0])
        close_task(task_id, user_id=update.effective_user.id)
        await update.message.reply_text(f"✅ Задача #{task_id} выполнена!")
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом")


async def finance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Использование: /finance <объект>")
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
