"""Команды Telegram-бота БО 7.5"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from db import get_connection
from modules.objects import create_object, get_all_objects, get_object_by_name, get_object
from modules.tasks import create_task, get_active_tasks, close_task, get_tasks_by_object
from modules.finance import add_expense, get_finance_summary
from modules.parser import parse_message, parse_amount
from modules.personal import add_personal_expense
from config import ADMIN_IDS
from handlers.onboarding import ask_role, role_menu_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт: онбординг при первом входе, иначе — меню по роли."""
    user = update.effective_user

    # === ГЛАВНЫЙ АДМИН — сразу меню, без онбординга ===
    from handlers.onboarding import MAIN_ADMIN_TG_ID
    if user.id == MAIN_ADMIN_TG_ID:
        # Сохраняем юзера
        try:
            from modules.users import save_user, set_role, mark_onboarded
            save_user(user.id, user.first_name or "", user.username or "", role="admin")
            set_role(user.id, "admin")
            try:
                mark_onboarded(user.id)
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️ admin save: {e}")

        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я *Бо 7.5* — твой помощник по стройке.\n"
            f"Ты вошёл как *админ*.",
            reply_markup=role_menu_keyboard("admin"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # === ОБЫЧНЫЕ ЮЗЕРЫ ===
    # Сохраняем/обновляем юзера
    try:
        from modules.users import save_user, get_user
        save_user(user.id, user.first_name or "", user.username or "")
    except Exception as e:
        print(f"⚠️ save_user: {e}")

    # Определяем роль и онбординг
    role = "guest"
    onboarded = False
    try:
        from modules.users import get_user, is_onboarded
        u = get_user(user.id)
        if u:
            role = (u.get("role") if isinstance(u, dict) else u[3]) or "guest"
        onboarded = is_onboarded(user.id)
    except Exception as e:
        print(f"⚠️ get_user: {e}")

    # Первый вход → онбординг
    if not onboarded:
        await ask_role(update, context)
        return

    # Иначе — меню по роли
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я *Бо 7.5* — твой помощник по стройке.\n"
        f"Твоя роль: *{role}*",
        reply_markup=role_menu_keyboard(role),
        parse_mode=ParseMode.MARKDOWN,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 **Бо 7.5 — команды и возможности**\n\n"
        "🏗️ **Объекты**\n"
        "/objects — список объектов кнопками\n"
        "/add_object <название> — создать объект\n\n"
        "📋 **Задачи**\n"
        "/tasks — активные задачи кнопками\n"
        "/add <объект> <задача> — быстро добавить\n"
        "/add — меню добавления (объект/задача/расход)\n"
        "/done <id> — закрыть задачу\n\n"
        "💰 **Финансы**\n"
        "/finance — общая сводка кнопками\n"
        "/finance <объект> — по объекту\n"
        "/add_expense <объект> <сумма> [категория]\n\n"
        "💸 **Личные расходы** — через меню «💸 Личные»\n\n"
        "📊 **Отчёты** — через меню «📊 Отчёты»\n\n"
        "📝 **Свободный ввод** (пиши текстом):\n"
        "• «потратил 5000 на материалы Переделкино-2»\n"
        "• «добавь в Арбат положить паркет»\n"
        "• «500» — спросит личный/объект\n"
        "• «задачи» / «объекты»\n\n"
        "⏰ **Автоматика**\n"
        "• Дайджест 9:00 МСК\n"
        "• Опрос 18:00 МСК\n"
        "• Автобэкап 23:00 МСК",
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
    await update.message.reply_text(
        f"🏗️ **Объекты ({len(objs)}):**\n\nНажми на объект:",
        reply_markup=objects_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


async def add_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        # Без аргументов — открываем интерактивное меню добавления
        await update.message.reply_text(
            "➕ Что добавить?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ Новый объект", callback_data="add_object")],
                [InlineKeyboardButton("📋 Новая задача", callback_data="add_task")],
                [InlineKeyboardButton("💰 Расход", callback_data="add_expense")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
            ])
        )
        return
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
    """Задачи по датам с кнопками — как в меню."""
    from datetime import datetime, date, timedelta
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.title, t.deadline, o.name as object_name
        FROM tasks t
        LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.status IN ('open', 'in_progress')
        ORDER BY t.deadline IS NULL, t.deadline ASC
    """)
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Нет активных задач")
        return

    today = date.today()
    tomorrow = today + timedelta(days=1)

    today_tasks = [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() == today]
    tomorrow_tasks = [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() == tomorrow]
    later_tasks = sorted(
        [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() > tomorrow],
        key=lambda x: x['deadline']
    )
    no_deadline = [r for r in rows if not r['deadline']]

    def format_block(title, items):
        lines = [f"**{title}:**"]
        for r in items:
            d = ""
            if r['deadline']:
                try:
                    d = " (" + datetime.strptime(r['deadline'], '%Y-%m-%d').strftime('%d.%m') + ")"
                except Exception:
                    pass
            obj = r['object_name'] or "без объекта"
            lines.append(f"#{r['id']} {r['title']}{d} — {obj}")
        return "\n".join(lines)

    sections = []
    if today_tasks:
        sections.append(format_block(f"СЕГОДНЯ — {today.strftime('%d.%m.%Y')}", today_tasks))
    if tomorrow_tasks:
        sections.append(format_block(f"ЗАВТРА — {tomorrow.strftime('%d.%m.%Y')}", tomorrow_tasks))
    if later_tasks:
        sections.append(format_block("ПОЗЖЕ", later_tasks))
    if no_deadline:
        sections.append(format_block("БЕЗ СРОКА", no_deadline))

    text = "📋 ЗАДАЧИ\n\n" + "\n".join(sections)
    if len(text) > 4000:
        text = text[:3900] + "\n\n..."

    buttons = []
    task_order = today_tasks + tomorrow_tasks + later_tasks + no_deadline
    for i, r in enumerate(task_order[:20], start=1):
        buttons.append([InlineKeyboardButton(
            f"{i}. {r['title'][:40]}",
            callback_data=f"task_{r['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])

    await update.message.reply_text(
        text + "\n\nВыбери задачу:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

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


# === ОБРАБОТКА КНОПОК ===

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
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(buttons)


def object_detail_keyboard(object_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Задачи объекта", callback_data=f"objtasks_{object_id}")],
        [InlineKeyboardButton("💰 Финансы", callback_data=f"objfin_{object_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_objects")],
    ])


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏗️ Объекты", callback_data="menu_objects")],
        [InlineKeyboardButton("📋 Задачи", callback_data="menu_tasks")],
        [InlineKeyboardButton("💰 Финансы", callback_data="menu_finance")],
        [InlineKeyboardButton("📊 Отчёты", callback_data="menu_reports")],
        [InlineKeyboardButton("💸 Личные", callback_data="menu_personal")],
        [InlineKeyboardButton("🌐 Дашборд", callback_data="menu_dashboard")],
        [InlineKeyboardButton("➕ Добавить", callback_data="menu_add")],
        [InlineKeyboardButton("⚙️ Помощь", callback_data="menu_help")],
    ])


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu_back":
        await query.edit_message_text(
            "🏠 **Главное меню**",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "menu_objects":
        objs = get_all_objects()
        if not objs:
            await query.edit_message_text("🏗️ Объектов пока нет")
            return
        await query.edit_message_text(
            f"🏗️ **Объекты ({len(objs)}):**\n\nНажми на объект:",
            reply_markup=objects_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "menu_tasks":
        from datetime import datetime, date, timedelta
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT t.id, t.title, t.deadline, o.name as object_name
            FROM tasks t
            LEFT JOIN objects o ON t.object_id = o.id
            WHERE t.status IN ('open', 'in_progress')
            ORDER BY t.deadline IS NULL, t.deadline ASC
        """)
        rows = c.fetchall()
        conn.close()

        if not rows:
            await query.edit_message_text("Нет активных задач")
            return

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Группируем по датам
        sections = []
        today_tasks = [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() == today]
        tomorrow_tasks = [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() == tomorrow]
        later_tasks = sorted(
            [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() > tomorrow],
            key=lambda x: x['deadline']
        )
        no_deadline = [r for r in rows if not r['deadline']]

        def format_block(title, items):
            lines = [f"**{title}:**"]
            for r in items:
                d = ""
                if r['deadline']:
                    try:
                        d = " (" + datetime.strptime(r['deadline'], '%Y-%m-%d').strftime('%d.%m') + ")"
                    except Exception:
                        pass
                obj = r['object_name'] or "без объекта"
                lines.append(f"#{r['id']} {r['title']}{d} — {obj}")
            return "\n".join(lines)

        if today_tasks:
            sections.append(format_block(f"СЕГОДНЯ — {today.strftime('%d.%m.%Y')}", today_tasks))
        if tomorrow_tasks:
            sections.append(format_block(f"ЗАВТРА — {tomorrow.strftime('%d.%m.%Y')}", tomorrow_tasks))
        if later_tasks:
            sections.append(format_block("ПОЗЖЕ", later_tasks))
        if no_deadline:
            sections.append(format_block("БЕЗ СРОКА", no_deadline))

        text = "📋 ЗАДАЧИ\n\n" + "\n".join(sections)
        if len(text) > 4000:
            text = text[:3900] + "\n\n..."

        # Кнопки задач (макс 20), по порядку важности
        buttons = []
        task_order = today_tasks + tomorrow_tasks + later_tasks + no_deadline
        for i, r in enumerate(task_order[:20], start=1):
            buttons.append([InlineKeyboardButton(
                f"{i}. {r['title'][:40]}",
                callback_data=f"task_{r['id']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])

        await query.edit_message_text(
            text + "\n\nВыбери задачу:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    if data == "menu_finance":
        await query.edit_message_text(
            format_finance_summary(),
            reply_markup=finance_keyboard()
        )
        return

    if data.startswith("finobj_"):
        object_id = int(data.split("_")[1])
        obj = get_object(object_id)
        if not obj:
            await query.edit_message_text("❌ Объект не найден")
            return
        f = get_finance_summary(object_id)
        await query.edit_message_text(
            f"💰 **{obj['name']}**\n\n"
            f"Доход: {format_money(f['income'])} ₽\n"
            f"Расход: {format_money(f['expense'])} ₽\n"
            f"Баланс: {format_money(f['balance'])} ₽",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К финансам", callback_data="menu_finance")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "menu_personal":
        await query.edit_message_text(
            format_personal_summary('month'),
            reply_markup=personal_keyboard()
        )
        return

    if data == "personal_today":
        await query.edit_message_text(
            format_personal_summary('today'),
            reply_markup=personal_keyboard()
        )
        return

    if data == "personal_week":
        await query.edit_message_text(
            format_personal_summary('week'),
            reply_markup=personal_keyboard()
        )
        return

    if data == "personal_month":
        await query.edit_message_text(
            format_personal_summary('month'),
            reply_markup=personal_keyboard()
        )
        return

    if data == "personal_all":
        await query.edit_message_text(
            format_personal_summary('all'),
            reply_markup=personal_keyboard()
        )
        return

    if data == "personal_add":
        context.user_data['waiting_for'] = 'personal_expense_text'
        await query.edit_message_text(
            "💸 Новый личный расход\n\nНапиши сумму и категорию. Например:\n"
            "«300 еда»\n«1500 инструмент»\n«200 такси»",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_personal")]
            ])
        )
        return

    # === ВЫБОР: ЛИЧНЫЙ ИЛИ ПО ОБЪЕКТУ ===
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
        return

    if data.startswith("exp_type_object_"):
        amount = int(data.replace("exp_type_object_", ""))
        context.user_data['pending_object_expense_amount'] = amount
        await query.edit_message_text(
            f"🏗️ Расход {amount} ₽\n\nВыбери объект:",
            reply_markup=choose_object_for_expense_keyboard_amount(amount)
        )
        return

    if data.startswith("personal_cat_"):
        parts = data.replace("personal_cat_", "").split("_", 1)
        amount = int(parts[0])
        category = parts[1]
        add_personal_expense(amount, category)
        context.user_data['pending_personal_expense'] = None
        context.user_data['waiting_for'] = None
        await query.edit_message_text(
            f"✅ Личный расход {amount} ₽ ({category}) записан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 К личным", callback_data="menu_personal")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

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
        return

    if data.startswith("objexp_cat_"):
        # objexp_cat_<amount>_<obj_id>_<category>
        parts = data.replace("objexp_cat_", "").split("_")
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
        return

    # === ОТЧЁТЫ ===
    if data == "menu_reports":
        await query.edit_message_text(
            "📊 ОТЧЁТЫ\n\nВыбери тип:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📈 Сводный за месяц", callback_data="report_summary_month")],
                [InlineKeyboardButton("📈 Сводный за неделю", callback_data="report_summary_week")],
                [InlineKeyboardButton("📈 Сводный за всё время", callback_data="report_summary_all")],
                [InlineKeyboardButton("🏗️ По объекту", callback_data="report_choose_object")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
            ])
        )
        return

    if data.startswith("report_summary_"):
        period = data.replace("report_summary_", "")
        from modules.reports import get_summary_report, format_summary_report
        report = get_summary_report(period)
        text = format_summary_report(report)
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К отчётам", callback_data="menu_reports")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    if data == "report_choose_object":
        objs = get_all_objects()
        buttons = []
        for o in objs:
            buttons.append([InlineKeyboardButton(
                f"🏗️ {o['name']}",
                callback_data=f"report_obj_{o['id']}_month"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_reports")])
        await query.edit_message_text(
            "📊 Выбери объект для отчёта (за месяц):",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("report_obj_"):
        # report_obj_<obj_id>_<period>
        parts = data.replace("report_obj_", "").split("_")
        obj_id = int(parts[0])
        period = parts[1] if len(parts) > 1 else 'month'
        from modules.reports import get_object_report, format_object_report
        report = get_object_report(obj_id, period)
        text = format_object_report(report)
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 За неделю", callback_data=f"report_obj_{obj_id}_week")],
                [InlineKeyboardButton("📅 За месяц", callback_data=f"report_obj_{obj_id}_month")],
                [InlineKeyboardButton("📅 За всё время", callback_data=f"report_obj_{obj_id}_all")],
                [InlineKeyboardButton("⬅️ К отчётам", callback_data="menu_reports")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    if data == "menu_dashboard":
        from modules.dashboard_link import get_dashboard_url
        url = get_dashboard_url()
        await query.edit_message_text(
            f"🌐 Дашборд Бо 7.5\n\n"
            f"Нажми кнопку ниже, чтобы открыть:\n\n"
            f"📱 Совет: добавь на главный экран телефона",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Открыть дашборд", url=url)],
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")]
            ])
        )
        return

    if data == "menu_help":
        await query.edit_message_text(
            "📋 **Помощь**\n\n"
            "🏗️ **Объекты** — список, карточки\n"
            "📋 **Задачи** — активные, по объектам\n"
            "💰 **Финансы** — доходы, расходы\n\n"
            "Свободный ввод: пиши текстом\n"
            "«Потратил 5к переделкино»",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("objtasks_"):
        object_id = int(data.split("_")[1])
        tasks = get_tasks_by_object(object_id)
        if not tasks:
            await query.edit_message_text("📋 Задач нет", reply_markup=object_detail_keyboard(object_id))
            return
        text = "📋 **Задачи объекта:**\n\n"
        for t in tasks[:20]:
            icon = "✅" if t['status'] == 'done' else "🔵"
            text += f"{icon} #{t['id']} {t['title']}\n"
        await query.edit_message_text(text, reply_markup=object_detail_keyboard(object_id), parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("objfin_"):
        object_id = int(data.split("_")[1])
        f = get_finance_summary(object_id)
        await query.edit_message_text(
            f"💰 **Финансы**\n\nДоход: {f['income']} ₽\nРасход: {f['expense']} ₽\nБаланс: {f['balance']} ₽",
            reply_markup=object_detail_keyboard(object_id),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("obj_"):
        object_id = int(data.split("_")[1])
        obj = get_object(object_id)
        if not obj:
            await query.edit_message_text("❌ Объект не найден")
            return
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
        return

    if data.startswith("task_"):
        task_id = int(data.split("_")[1])
        await query.edit_message_text(
            f"📋 **Задача #{task_id}**\n\nЗакрыть? Напиши: `/done {task_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return



async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text or text.startswith('/'):
        return

    # Обработка создания новой задачи
    if context.user_data.get('waiting_for') == 'new_task_text':
        obj = context.user_data.get('pending_task_object')
        if obj:
            tid = create_task(obj['id'], text)
            context.user_data['waiting_for'] = None
            context.user_data['pending_task_object'] = None
            await update.message.reply_text(
                f"✅ Задача «{text}» добавлена в «{obj['name']}»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 К задаче", callback_data=f"task_{tid}")],
                    [InlineKeyboardButton("📋 К задачам", callback_data="menu_tasks")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
            return

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
            return
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
                    return
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
                    return
            else:
                await update.message.reply_text(
                    "\u274c Не понял сумму. Попробуй: \u00ab500\u00bb"
                )
                return

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
                return
        add_personal_expense(amount, category)
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"✅ Личный расход {amount} ₽ ({category}) записан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 К личным", callback_data="menu_personal")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    # Обработка создания нового объекта
    if context.user_data.get('waiting_for') == 'new_object':
        object_id = create_object(text, user_id=update.effective_user.id)
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"✅ Объект «{text}» создан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ К объекту", callback_data=f"obj_{object_id}")],
                [InlineKeyboardButton("🏗️ К объектам", callback_data="menu_objects")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    # Обработка ввода даты для задачи
    setdate_task = context.user_data.get('setdate_task')
    if setdate_task:
        d = parse_date(text)
        if d:
            # Сохраняем во временное хранилище, ждём подтверждения
            context.user_data['confirm_date'] = {
                'task_id': setdate_task,
                'date': d.strftime('%Y-%m-%d'),
                'date_str': d.strftime('%d.%m.%Y')
            }
            context.user_data['setdate_task'] = None
            # Получаем задачу
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT t.title, o.name as obj FROM tasks t LEFT JOIN objects o ON t.object_id = o.id WHERE t.id = ?", (setdate_task,))
            row = c.fetchone()
            conn.close()
            title = row['title'] if row else '?'
            obj = row['obj'] if row and row['obj'] else 'Без объекта'
            await update.message.reply_text(
                f"📋 {title}\n{obj}\n\n📅 Дата: {d.strftime('%d.%m.%Y')}\n\nПодтверди:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да", callback_data=f"confirmdate_yes_{setdate_task}_{d.strftime('%Y-%m-%d')}")],
                    [InlineKeyboardButton("❌ Нет", callback_data=f"confirmdate_no_{setdate_task}")],
                ])
            )
            # Автоподтверждение через 30 секунд
            context.job_queue.run_once(
                auto_confirm_date,
                30,
                data={
                    'chat_id': update.effective_chat.id,
                    'task_id': setdate_task,
                    'date': d.strftime('%Y-%m-%d'),
                    'date_str': d.strftime('%d.%m.%Y')
                },
                name=f"confirm_{setdate_task}"
            )
            return
        else:
            await update.message.reply_text(
                "❌ Не понял дату. Попробуй: «завтра», «20.09», «пн», «+3»"
            )
            return

    # Обработка переименования задачи
    rename_task = context.user_data.get('rename_task')
    if rename_task:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE tasks SET title = ? WHERE id = ?", (text, rename_task))
        conn.commit()
        conn.close()
        context.user_data['rename_task'] = None
        await update.message.reply_text(f"✅ Задача переименована: «{text}»")
        return

    result = parse_message(text)
    action = result.get('action')

    if action == 'ask_expense_type':
        amount = result['amount']
        context.user_data['ask_expense_amount'] = amount
        await update.message.reply_text(
            f"💰 {amount} ₽ — куда записать?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Личный расход", callback_data=f"exp_type_personal_{amount}")],
                [InlineKeyboardButton("🏗️ Расход по объекту", callback_data=f"exp_type_object_{amount}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_back")],
            ])
        )
        return

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
            return
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
        return

    if action == 'add_task':
        obj = result['object']
        title = result['title']
        tid = create_task(obj['id'], title)
        await update.message.reply_text(
            f"✅ Задача «{title}» добавлена в «{obj['name']}». ID: {tid}"
        )
        return

    if action == 'done_task':
        obj = result['object']
        task = result['task']
        close_task(task['id'], user_id=update.effective_user.id)
        await update.message.reply_text(
            f"✅ Задача «{task['title']}» в «{obj['name']}» выполнена!"
        )
        return

    if action == 'done_task_not_found':
        obj = result['object']
        await update.message.reply_text(
            f"❌ В «{obj['name']}» не нашёл задачу с «{result['query']}». Посмотри /tasks"
        )
        return

    if action == 'finance':
        obj = result['object']
        f = get_finance_summary(obj['id'])
        await update.message.reply_text(
            f"💰 {obj['name']}\n\nДоход: {f['income']} ₽\nРасход: {f['expense']} ₽\nБаланс: {f['balance']} ₽"
        )
        return

    if action == 'list_tasks':
        tasks = get_active_tasks()
        if not tasks:
            await update.message.reply_text("✅ Нет активных задач")
            return
        text_out = f"📋 Активные задачи ({len(tasks)}):\n\n"
        for t in tasks[:15]:
            text_out += f"• #{t['id']} {t['title']}\n"
        await update.message.reply_text(text_out)
        return

    if action == 'list_objects':
        objs = get_all_objects()
        text_out = f"🏗️ Объекты ({len(objs)}):\n\n"
        for o in objs:
            text_out += f"• {o['name']}\n"
        await update.message.reply_text(text_out)
        return

    if action == 'choose_object':
        objects = result['objects']
        intent = result.get('intent', 'expense')
        amount = result.get('amount')
        category = result.get('category', 'прочее')
        if intent == 'add_task':
            context.user_data['pending_task_title'] = result.get('original_text', '')
        await update.message.reply_text(
            f"🤔 Нашёл несколько объектов. Какой именно?",
            reply_markup=make_choose_keyboard(objects, intent, amount, category)
        )
        return

    await update.message.reply_text(
        "🤔 Не понял. Попробуй так:\n\n"
        "• «потратил 5000 на материалы Переделкино-2»\n"
        "• «добавь в Арбат положить паркет»\n"
        "• «в Острове покрасил стены»\n"
        "• «сколько потратил на Бамбино»\n"
        "• «задачи» / «объекты»"
    )


# === УТОЧНЕНИЕ ОБЪЕКТА ===

async def handle_choose_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает кнопки выбора объекта"""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Формат: choose_obj_<intent>_<object_id>_<amount>_<category>
    parts = data.split('_')
    intent = parts[2]
    object_id = int(parts[3])
    amount = int(parts[4]) if len(parts) > 4 and parts[4] != 'none' else None
    category = parts[5] if len(parts) > 5 else 'прочее'

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

from modules.finance import get_all_finance_summary


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


def tasks_keyboard():
    """Клавиатура активных задач"""
    from modules.tasks import get_active_tasks
    tasks = get_active_tasks()
    buttons = []
    for t in tasks[:20]:
        buttons.append([InlineKeyboardButton(
            f"#{t['id']} {t['title'][:40]}",
            callback_data=f"task_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(buttons)


def tasks_keyboard_by_object():
    """Клавиатура задач по объектам"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT o.id, o.name, COUNT(t.id) as cnt
        FROM objects o
        JOIN tasks t ON t.object_id = o.id
        WHERE t.status IN ('open', 'in_progress') AND o.status IN ('active', 'paused', 'waiting')
        GROUP BY o.id, o.name
        ORDER BY o.name
    """)
    rows = c.fetchall()
    conn.close()

    buttons = []
    for r in rows:
        buttons.append([InlineKeyboardButton(
            f"🏗️ {r['name']} ({r['cnt']})",
            callback_data=f"objtasks_{r['id']}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
    return InlineKeyboardMarkup(buttons)


# === КАРТОЧКА ЗАДАЧИ ===

def task_card_keyboard(task_id, deadline=None):
    """Клавиатура карточки задачи"""
    buttons = [
        [InlineKeyboardButton("📅 Срок", callback_data=f"taskdate_{task_id}")],
    ]
    if deadline:
        buttons.append([InlineKeyboardButton("🚫 Убрать срок", callback_data=f"tasknodate_{task_id}")])
    buttons += [
        [InlineKeyboardButton("🔴 Приоритет", callback_data=f"taskprio_{task_id}")],
        [InlineKeyboardButton("✏️ Название", callback_data=f"taskrename_{task_id}")],
        [InlineKeyboardButton("✅ Выполнить", callback_data=f"taskdone_{task_id}")],
        [InlineKeyboardButton("❌ Удалить", callback_data=f"taskdel_{task_id}")],
        [InlineKeyboardButton("⬅ К задачам", callback_data="menu_tasks")],
    ]
    return InlineKeyboardMarkup(buttons)
def task_date_keyboard(task_id):
    """Клавиатура выбора срока"""
    from datetime import date, timedelta
    today = date.today()
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Сегодня ({today.strftime('%d.%m')})", callback_data=f"setdate_{task_id}_today")],
        [InlineKeyboardButton(f"Завтра ({(today+timedelta(days=1)).strftime('%d.%m')})", callback_data=f"setdate_{task_id}_tomorrow")],
        [InlineKeyboardButton(f"Послезавтра ({(today+timedelta(days=2)).strftime('%d.%m')})", callback_data=f"setdate_{task_id}_dayafter")],
        [InlineKeyboardButton(f"Через 3 дня ({(today+timedelta(days=3)).strftime('%d.%m')})", callback_data=f"setdate_{task_id}_3days")],
        [InlineKeyboardButton(f"Через неделю ({(today+timedelta(days=7)).strftime('%d.%m')})", callback_data=f"setdate_{task_id}_week")],
        [InlineKeyboardButton("✏️ Ввести дату вручную", callback_data=f"taskdate_manual_{task_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"task_{task_id}")],
    ])


def task_priority_keyboard(task_id):
    """Клавиатура приоритета"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 Высокий", callback_data=f"setprio_{task_id}_high")],
        [InlineKeyboardButton("🟡 Средний", callback_data=f"setprio_{task_id}_medium")],
        [InlineKeyboardButton("🟢 Низкий", callback_data=f"setprio_{task_id}_low")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"task_{task_id}")],
    ])


async def show_task_card(query, task_id, message=None):
    """Показывает карточку задачи"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.title, t.status, t.priority, t.deadline, o.name as object_name
        FROM tasks t
        LEFT JOIN objects o ON t.object_id = o.id
        WHERE t.id = ?
    """, (task_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        await query.edit_message_text("Задача не найдена")
        return

    priority_map = {'high': 'Высокий', 'medium': 'Средний', 'low': 'Низкий'}
    deadline_str = 'не указан'
    if row['deadline']:
        try:
            from datetime import datetime
            d = datetime.strptime(row['deadline'], '%Y-%m-%d').date()
            deadline_str = d.strftime('%d.%m.%Y')
        except:
            deadline_str = row['deadline']

    text = f"📋 {row['title']}\n\n"
    text += f"Объект: {row['object_name'] or 'Без объекта'}\n"
    text += f"Срок: {deadline_str}\n"
    text += f"Приоритет: {priority_map.get(row['priority'], row['priority'])}\n"

    await query.edit_message_text(text, reply_markup=task_card_keyboard(task_id, row['deadline']))



async def handle_task_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий с задачей"""
    query = update.callback_query
    await query.answer()
    data = query.data
    from datetime import date, timedelta

    # Выполнить
    if data.startswith("taskdone_"):
        task_id = int(data.split("_")[1])
        close_task(task_id, user_id=update.effective_user.id)
        await query.edit_message_text(
            "✅ Задача выполнена!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К задачам", callback_data="menu_tasks")]
            ])
        )
        return

    # Удалить
    if data.startswith("taskdel_"):
        task_id = int(data.split("_")[1])
        conn = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(
            "❌ Задача удалена",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К задачам", callback_data="menu_tasks")]
            ])
        )
        return

    # Показать карточку
    if data.startswith("task_") and not any(data.startswith(p) for p in ["taskdate_", "taskdone_", "taskdel_", "taskprio_", "taskrename_"]):
        try:
            task_id = int(data.split("_")[1])
            await show_task_card(query, task_id)
        except:
            pass
        return

    # Выбор срока
    if data.startswith("taskdate_"):
        parts = data.split("_")
        # taskdate_manual_<id> — ручной ввод
        if len(parts) >= 2 and parts[1] == "manual":
            task_id = int(parts[2])
            context.user_data['setdate_task'] = task_id
            # Показываем задачу
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT t.title, o.name as obj FROM tasks t LEFT JOIN objects o ON t.object_id = o.id WHERE t.id = ?", (task_id,))
            row = c.fetchone()
            conn.close()
            title = row['title'] if row else '?'
            obj = row['obj'] if row and row['obj'] else 'Без объекта'
            await query.edit_message_text(
                f"📋 {title}\n{obj}\n\nНапиши дату:"
            )
            return
        # taskdate_<id> — обычный выбор
        task_id = int(parts[1])
        await query.edit_message_text(
            "📅 Выбери срок:",
            reply_markup=task_date_keyboard(task_id)
        )
        return


    # Убрать срок
    if data.startswith("tasknodate_"):
        task_id = int(data.replace("tasknodate_", ""))
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE tasks SET deadline = NULL WHERE id = ?", (task_id,))
        conn.commit()
        c.execute("SELECT t.title, o.name as obj FROM tasks t LEFT JOIN objects o ON t.object_id = o.id WHERE t.id = ?", (task_id,))
        row = c.fetchone()
        conn.close()
        title = row['title'] if row else '?'
        obj = row['obj'] if row and row['obj'] else 'Без объекта'
        await query.edit_message_text(
            f"🚫 Срок убран у задачи «{title}» ({obj})"
        )
        return
    # Установка срока
    if data.startswith("setdate_"):
        parts = data.split("_")
        task_id = int(parts[1])
        mode = parts[2]
        today = date.today()
        if mode == "today":
            new_date = today
        elif mode == "tomorrow":
            new_date = today + timedelta(days=1)
        elif mode == "dayafter":
            new_date = today + timedelta(days=2)
        elif mode == "3days":
            new_date = today + timedelta(days=3)
        elif mode == "week":
            new_date = today + timedelta(days=7)
        else:
            new_date = today
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE tasks SET deadline = ? WHERE id = ?", (new_date.strftime('%Y-%m-%d'), task_id))
        conn.commit()
        conn.close()
        await show_task_card(query, task_id)
        return

    # Выбор приоритета
    if data.startswith("taskprio_"):
        task_id = int(data.split("_")[1])
        await query.edit_message_text(
            "🔴 Выбери приоритет:",
            reply_markup=task_priority_keyboard(task_id)
        )
        return

    # Установка приоритета
    if data.startswith("setprio_"):
        parts = data.split("_")
        task_id = int(parts[1])
        prio = parts[2]
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE tasks SET priority = ? WHERE id = ?", (prio, task_id))
        conn.commit()
        conn.close()
        await show_task_card(query, task_id)
        return

    # Переименовать
    if data.startswith("taskrename_"):
        task_id = int(data.split("_")[1])
        context.user_data['rename_task'] = task_id
        await query.edit_message_text("✏️ Напиши новое название задачи:")
        return




def parse_date(text):
    """Парсит дату из текста. Возвращает date или None"""
    from datetime import datetime, date, timedelta
    import re

    text = text.strip().lower()
    today = date.today()

    if text in ['сегодня', 'today']:
        return today
    if text in ['завтра', 'tomorrow']:
        return today + timedelta(days=1)
    if text in ['послезавтра']:
        return today + timedelta(days=2)
    if text in ['через неделю', 'неделя']:
        return today + timedelta(days=7)

    m = re.search(r'через\s+(\d+)\s*дн', text)
    if m:
        return today + timedelta(days=int(m.group(1)))

    m = re.match(r'^\+(\d+)д?$', text)
    if m:
        return today + timedelta(days=int(m.group(1)))

    weekdays = {
        'понедельник': 0, 'пн': 0,
        'вторник': 1, 'вт': 1,
        'среда': 2, 'ср': 2,
        'четверг': 3, 'чт': 3,
        'пятница': 4, 'пт': 4,
        'суббота': 5, 'сб': 5,
        'воскресенье': 6, 'вс': 6,
    }
    for name, num in weekdays.items():
        if text.startswith(name):
            days_ahead = (num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)

    months = {
        'января': 1, 'январь': 1, 'янв': 1,
        'февраля': 2, 'февраль': 2, 'фев': 2,
        'марта': 3, 'март': 3, 'мар': 3,
        'апреля': 4, 'апрель': 4, 'апр': 4,
        'мая': 5, 'май': 5,
        'июня': 6, 'июнь': 6, 'июн': 6,
        'июля': 7, 'июль': 7, 'июл': 7,
        'августа': 8, 'август': 8, 'авг': 8,
        'сентября': 9, 'сентябрь': 9, 'сен': 9, 'сент': 9,
        'октября': 10, 'октябрь': 10, 'окт': 10,
        'ноября': 11, 'ноябрь': 11, 'ноя': 11,
        'декабря': 12, 'декабрь': 12, 'дек': 12,
    }
    m = re.search(r'(\d{1,2})\s+([а-яё]+)(?:\s+(\d{4}))?', text)
    if m:
        day = int(m.group(1))
        month_name = m.group(2)
        year = int(m.group(3)) if m.group(3) else today.year
        for name, num in months.items():
            if month_name.startswith(name) or name.startswith(month_name):
                try:
                    result = date(year, num, day)
                    if result < today and not m.group(3):
                        result = date(year + 1, num, day)
                    return result
                except:
                    pass

    m = re.search(r'(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?', text)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_str = m.group(3)
        if year_str:
            year = int(year_str)
            if year < 100:
                year += 2000
        else:
            year = today.year
        try:
            result = date(year, month, day)
            if result < today and not year_str:
                result = date(year + 1, month, day)
            return result
        except:
            pass

    m = re.match(r'^(\d{1,2})$', text)
    if m:
        day = int(m.group(1))
        if 1 <= day <= 31:
            try:
                result = date(today.year, today.month, day)
                if result < today:
                    if today.month == 12:
                        result = date(today.year + 1, 1, day)
                    else:
                        result = date(today.year, today.month + 1, day)
                return result
            except:
                pass

        # "6дек" — день + месяц слитно
    m = re.match(r'^(\d{1,2})([а-яё]{3,})(?:\s*(\d{4}))?$', text)
    if m:
        day = int(m.group(1))
        month_name = m.group(2)
        year_str = m.group(3)
        months = {
            'января': 1, 'январь': 1, 'янв': 1,
            'февраля': 2, 'февраль': 2, 'фев': 2,
            'марта': 3, 'март': 3, 'мар': 3,
            'апреля': 4, 'апрель': 4, 'апр': 4,
            'мая': 5, 'май': 5,
            'июня': 6, 'июнь': 6, 'июн': 6,
            'июля': 7, 'июль': 7, 'июл': 7,
            'августа': 8, 'август': 8, 'авг': 8,
            'сентября': 9, 'сентябрь': 9, 'сен': 9, 'сент': 9,
            'октября': 10, 'октябрь': 10, 'окт': 10,
            'ноября': 11, 'ноябрь': 11, 'ноя': 11,
            'декабря': 12, 'декабрь': 12, 'дек': 12,
        }
        for name, num in months.items():
            if month_name.startswith(name) or name.startswith(month_name):
                year = int(year_str) if year_str else today.year
                try:
                    result = date(year, num, day)
                    if result < today and not year_str:
                        result = date(year + 1, num, day)
                    return result
                except:
                    pass

    # "20 9" — день месяц через пробел
    m = re.match(r'^(\d{1,2})\s+(\d{1,2})(?:\s+(\d{4}))?$', text)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_str = m.group(3)
        if year_str:
            year = int(year_str)
        else:
            year = today.year
        try:
            result = date(year, month, day)
            if result < today and not year_str:
                result = date(year + 1, month, day)
            return result
        except:
            pass

    return None


async def auto_confirm_date(context: ContextTypes.DEFAULT_TYPE):
    """Автоподтверждение даты через 30 секунд"""
    job = context.job
    task_id = job.data['task_id']
    date = job.data['date']
    date_str = job.data['date_str']
    chat_id = job.data['chat_id']

    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE tasks SET deadline = ? WHERE id = ?", (date, task_id))
    conn.commit()
    # Получаем задачу
    c.execute("SELECT t.title, o.name as obj FROM tasks t LEFT JOIN objects o ON t.object_id = o.id WHERE t.id = ?", (task_id,))
    row = c.fetchone()
    conn.close()
    title = row['title'] if row else '?'
    obj = row['obj'] if row and row['obj'] else 'Без объекта'

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ {title}\n{obj}\nСрок: {date_str}"
    )


async def handle_confirm_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения даты"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("confirmdate_yes_"):
        parts = data.split("_")
        task_id = int(parts[2])
        date = parts[3]
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE tasks SET deadline = ? WHERE id = ?", (date, task_id))
        conn.commit()
        conn.close()
        # Убиваем job, если был
        try:
            jobs = context.job_queue.get_jobs_by_name(f"confirm_{task_id}")
            for j in jobs:
                j.schedule_removal()
        except:
            pass
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT t.title, o.name as obj FROM tasks t LEFT JOIN objects o ON t.object_id = o.id WHERE t.id = ?", (task_id,))
        row = c.fetchone()
        conn.close()
        title = row['title'] if row else '?'
        obj = row['obj'] if row and row['obj'] else 'Без объекта'
        await query.edit_message_text(f"✅ {title}\n{obj}\nСрок: {date}")
        return

    if data.startswith("confirmdate_no_"):
        parts = data.split("_")
        task_id = int(parts[2])
        # Убиваем job
        try:
            jobs = context.job_queue.get_jobs_by_name(f"confirm_{task_id}")
            for j in jobs:
                j.schedule_removal()
        except:
            pass
        await query.edit_message_text("❌ Отменено")
        return


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

def format_personal_summary(period='month'):
    """Формирует текст сводки личных расходов"""
    from modules.personal import get_personal_summary
    data = get_personal_summary(period)
    period_names = {
        'today': 'сегодня',
        'week': 'за 7 дней',
        'month': 'за месяц',
        'all': 'за всё время'
    }
    text = f"💸 ЛИЧНЫЕ РАСХОДЫ ({period_names.get(period, period)})\n\n"
    text += f"Потрачено: {data['total']} ₽\n"
    text += f"Записей: {data['count']}\n\n"
    if data['by_category']:
        text += "📊 По категориям:\n"
        for item in data['by_category'][:10]:
            text += f"• {item['category']}: {item['amount']} ₽\n"
    else:
        text += "Пока нет записей за этот период."
    return text


def personal_keyboard():
    """Клавиатура для экрана личных расходов"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить расход", callback_data="personal_add")],
        [InlineKeyboardButton("📅 За сегодня", callback_data="personal_today"),
         InlineKeyboardButton("📅 За неделю", callback_data="personal_week")],
        [InlineKeyboardButton("📅 За месяц", callback_data="personal_month"),
         InlineKeyboardButton("📅 За всё время", callback_data="personal_all")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
    ])


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
