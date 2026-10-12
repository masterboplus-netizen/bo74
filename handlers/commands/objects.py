"""Объекты: команды, клавиатуры, выбор объекта."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from modules.objects import get_all_objects, get_object, create_object


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
    await update.message.reply_text(
        f"🏗️ **Объекты ({len(objs)}):**\n\nНажми на объект:",
        reply_markup=objects_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )




def objects_keyboard():
    objs = get_all_objects()
    # Сортировка: active сверху, остальные внизу
    priority = {'active': 0, 'paused': 1, 'waiting': 2, 'completed': 3, 'closed': 4}
    objs_sorted = sorted(objs, key=lambda o: priority.get(o['status'], 9))

    buttons = []
    for obj in objs_sorted:
        icon = "🟢" if obj['status'] == 'active' else "⚪"
        buttons.append([InlineKeyboardButton(
            f"{icon} {obj['name']}",
            callback_data=f"obj_{obj['id']}"
        )])
    try:
        from modules.objects import get_archived_objects
        _arch = get_archived_objects()
        if _arch:
            buttons.append([InlineKeyboardButton("📦 Архив (" + str(len(_arch)) + ")", callback_data="obj_archive_list")])
    except Exception:
        pass
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(buttons)




def object_detail_keyboard(object_id):
    try:
        _obj_data = get_object(object_id)
        _status = (_obj_data or {}).get("status") or "active"
    except Exception:
        _status = "active"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Помещения", callback_data=f"obj_floors_{object_id}")],
        [InlineKeyboardButton("⚡ Щиты объекта", callback_data=f"panels_list_{object_id}")],
        [InlineKeyboardButton("⚡ ЭОМ объекта", callback_data=f"obj_elec_{object_id}")],
        [InlineKeyboardButton("💰 Смета ЭОМ", callback_data=f"obj_elec_cost_{object_id}")],
        [InlineKeyboardButton("👷 Работы (часы)", callback_data=f"obj_elec_labor_{object_id}")],
        [InlineKeyboardButton("📊 Смета ЭОМ (CSV)", callback_data=f"obj_est_csv_{object_id}")],
        [InlineKeyboardButton("📄 Спецификация ЭОМ", callback_data=f"obj_spec_{object_id}")],
        [InlineKeyboardButton("📄 PDF-смета ЭОМ", callback_data=f"obj_elec_pdf_{object_id}")],
        [InlineKeyboardButton("🔧 Сантехника", callback_data=f"plumb_list_{object_id}")],
            [InlineKeyboardButton("📄 PDF-смета сантехники", callback_data=f"plumb_pdf_obj_{object_id}")],
        [InlineKeyboardButton("🔨 Работы", callback_data=f"works_list_{object_id}")],
        [InlineKeyboardButton("💱 Импорт цен", callback_data=f"prices_import_{object_id}")],
        [InlineKeyboardButton("📋 Задачи объекта", callback_data=f"objtasks_{object_id}")],
        [InlineKeyboardButton("💰 Финансы", callback_data=f"objfin_{object_id}")],
        [InlineKeyboardButton("📸 Фото объекта", callback_data=f"objphotos_{object_id}")],
        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"obj_rename_{object_id}")],
        [InlineKeyboardButton(("📤 Из архива" if _status == "archived" else "📦 В архив"), callback_data=(f"obj_unarchive_{object_id}" if _status == "archived" else f"obj_archive_{object_id}"))],
        [InlineKeyboardButton("🗑 Удалить объект", callback_data=f"obj_del_{object_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=("obj_archive_list" if _status == "archived" else "menu_objects"))],
    ])




def choose_object_for_task_keyboard():
    """Клавиатура выбора объекта для задачи"""
    objs = get_all_objects()
    buttons = []
    for o in objs:
        buttons.append([InlineKeyboardButton(
            f"🏗️ {o['name']}",
            callback_data=f"newtask_obj_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_add")])
    return InlineKeyboardMarkup(buttons)




def choose_object_for_expense_keyboard():
    """Клавиатура выбора объекта для расхода"""
    objs = get_all_objects()
    buttons = []
    for o in objs:
        buttons.append([InlineKeyboardButton(
            f"🏗️ {o['name']}",
            callback_data=f"newexp_obj_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_add")])
    return InlineKeyboardMarkup(buttons)




# === ЛИЧНЫЕ РАСХОДЫ ===

def choose_object_for_expense_keyboard_amount(amount):
    """Клавиатура выбора объекта для расхода с суммой (только объект, без категории)"""
    objs = get_all_objects()
    buttons = []
    for o in objs:
        buttons.append([InlineKeyboardButton(
            f"🏗️ {o['name']}",
            callback_data=f"objexp_obj_{amount}_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(buttons)


# === OCR: распознавание чеков ===

