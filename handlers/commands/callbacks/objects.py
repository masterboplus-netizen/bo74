"""Callback-хендлеры домена «объекты» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_callback).
Блоки: objexp_obj_, objexp_cat_, objtasks_none, objtasks_, objfin_,
objphotos_, obj_.

Роутер try_handle(data, query, context) -> bool.
True = обработано, вызывающий делает return.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from db import get_connection
from modules.objects import get_object
from modules.tasks import get_tasks_by_object
from modules.finance import get_finance_summary, add_expense
from handlers.commands.objects import object_detail_keyboard, choose_object_for_expense_keyboard_amount
from handlers.commands.tasks import tasks_keyboard_by_object


async def try_handle(data: str, query, context) -> bool:
    """Обрабатывает объектные callback-и. True = обработано."""

    if data.startswith("exp_type_object_"):
        amount = int(data.replace("exp_type_object_", ""))
        context.user_data['pending_object_expense_amount'] = amount
        await query.edit_message_text(
            f"🏗️ Расход {amount} ₽\n\nВыбери объект:",
            reply_markup=choose_object_for_expense_keyboard_amount(amount)
        )
        return True

    if data.startswith("objexp_obj_"):
        # objexp_obj_<amount>_<obj_id>
        parts = data.replace("objexp_obj_", "").split("_")
        amount = int(parts[0])
        obj_id = int(parts[1])
        obj = get_object(obj_id)
        context.user_data['pending_obj_expense'] = {'amount': amount, 'obj_id': obj_id, 'obj_name': obj['name']}
        await query.edit_message_text(
            f"💰 {amount} ₽ в «{obj['name']}»\n\nЗа что?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧱 Материалы", callback_data=f"objexp_cat_{amount}_{obj_id}_материалы")],
                [InlineKeyboardButton("🔧 Инструмент", callback_data=f"objexp_cat_{amount}_{obj_id}_инструмент")],
                [InlineKeyboardButton("🚕 Транспорт", callback_data=f"objexp_cat_{amount}_{obj_id}_транспорт")],
                [InlineKeyboardButton("🍔 Еда", callback_data=f"objexp_cat_{amount}_{obj_id}_еда")],
                [InlineKeyboardButton("📦 Прочее", callback_data=f"objexp_cat_{amount}_{obj_id}_прочее")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_back")],
            ])
        )
        return True

    if data.startswith("objexp_cat_"):
        # objexp_cat_<amount>_<obj_id>_<category>
        parts = data.replace("objexp_cat_", "").split("_", 2)
        amount = int(parts[0])
        obj_id = int(parts[1])
        category = parts[2] if len(parts) > 2 else 'прочее'
        obj = get_object(obj_id)
        add_expense(obj_id, amount, category)
        context.user_data['pending_object_expense_amount'] = None
        await query.edit_message_text(
            f"✅ Расход {amount} ₽ ({category}) в «{obj['name']}»",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ К объекту", callback_data=f"obj_{obj_id}")],
                [InlineKeyboardButton("💰 К финансам", callback_data="menu_finance")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    if data == "objtasks_none":
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, title, status FROM tasks WHERE object_id IS NULL AND status != 'done'")
        _no_obj_tasks = c.fetchall()
        conn.close()
        if not _no_obj_tasks:
            await query.edit_message_text("📋 Задач без объекта нет", reply_markup=tasks_keyboard_by_object())
            return True
        text = "🚫 **Задачи без объекта:**\n\n"
        for t in _no_obj_tasks[:20]:
            icon = "✅" if t['status'] == 'done' else "🔵"
            text += f"{icon} {t['id']}. {t['title']}\n"
        await query.edit_message_text(text, reply_markup=tasks_keyboard_by_object())
        return True

    if data.startswith("objtasks_"):
        object_id = int(data.split("_")[1])
        tasks = get_tasks_by_object(object_id)
        if not tasks:
            await query.edit_message_text("📋 Задач нет", reply_markup=object_detail_keyboard(object_id))
            return True
        text = "📋 **Задачи объекта:**\n\n"
        for t in tasks[:20]:
            icon = "✅" if t['status'] == 'done' else "🔵"
            text += f"{icon} {t['id']}. {t['title']}\n"
        await query.edit_message_text(text, reply_markup=object_detail_keyboard(object_id), parse_mode=ParseMode.MARKDOWN)
        return True

    if data.startswith("objfin_"):
        object_id = int(data.split("_")[1])
        f = get_finance_summary(object_id)
        await query.edit_message_text(
            f"💰 **Финансы**\n\nДоход: {f['income']} ₽\nРасход: {f['expense']} ₽\nБаланс: {f['balance']} ₽",
            reply_markup=object_detail_keyboard(object_id),
            parse_mode=ParseMode.MARKDOWN
        )
        return True

    if data.startswith("objphotos_"):
        object_id = int(data.split("_")[1])
        obj = get_object(object_id)
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM photos WHERE object_id = ?", (object_id,))
        total = c.fetchone()[0] or 0
        conn.close()
        if total == 0:
            await query.edit_message_text(
                f"📷 Фото объекта «{obj['name']}»\n\nПока нет фото.\n\n"
                f"Отправь боту фото, чтобы добавить.",
                reply_markup=object_detail_keyboard(object_id)
            )
            return True
        await query.edit_message_text(
            f"📷 *Фото «{obj['name']}»*\n"
            f"Всего: {total}\n\n"
            f"Выбери фильтр:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆕 Последние (3 задачи)", callback_data=f"photofilt_last_{object_id}_0")],
                [InlineKeyboardButton("📋 По задачам", callback_data=f"photofilt_tasks_{object_id}")],
                [InlineKeyboardButton("📅 По датам", callback_data=f"photofilt_dates_{object_id}")],
                [InlineKeyboardButton("👤 Кто загрузил", callback_data=f"photofilt_uploaders_{object_id}")],
                [InlineKeyboardButton("🛠Кто делал задачу", callback_data=f"photofilt_assignees_{object_id}")],
                [InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")],
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return True

    if data.startswith("obj_"):
        object_id = int(data.split("_")[1])
        obj = get_object(object_id)
        if not obj:
            await query.edit_message_text("❌ Объект не найден")
            return True
        tasks = get_tasks_by_object(object_id)
        open_tasks = len([t for t in tasks if t['status'] == 'open'])
        f = get_finance_summary(object_id)
        text = (
            f"🏗️ **{obj['name']}**\n\n"
            f"**Статус:** {obj['status']}\n"
            f"**Бюджет:** {obj['budget']} ₽\n"
            f"**Задачи:** {open_tasks} открытых\n"
            f"**Доход:** {f['income']} ₽\n"
            f"**Расход:** {f['expense']} ₽\n"
            f"**Баланс:** {f['balance']} ₽"
        )
        await query.edit_message_text(text, reply_markup=object_detail_keyboard(object_id), parse_mode=ParseMode.MARKDOWN)
        return True

    return False
