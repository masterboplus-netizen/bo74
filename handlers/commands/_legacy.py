"""Команды Telegram-бота БО 7.7"""
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
from handlers.commands.start import _help_text, help_command
from handlers.commands.personal import personal_command, format_personal_summary, personal_keyboard
from handlers.commands.receipt import (
    handle_recognize_receipt, handle_receipt_save, handle_receipt_object,
    handle_receipt_category, handle_receipt_show
)
from handlers.commands.photos import (
    photos_command, _show_photos_batch, handle_photo_filter, handle_photo_page,
    handle_photo, handle_photo_stage, handle_photo_task, handle_photo_save
)
from handlers.commands.crm import (
    clients_command, deals_command, handle_crm_menu, _finalize_new_client
)
from handlers.commands.finance import (
    finance_command, add_expense_command, finance_keyboard,
    format_finance_summary, show_finance_summary, format_money
)
from handlers.commands.objects import (
    add_object_command, objects_command, objects_keyboard, object_detail_keyboard,
    choose_object_for_task_keyboard, choose_object_for_expense_keyboard,
    choose_object_for_expense_keyboard_amount
)
from handlers.commands.tasks import (
    add_task_command, format_tasks_block, tasks_command, done_command,
    handle_skip_photo, tasks_keyboard, tasks_keyboard_by_object,
    task_card_keyboard, task_date_keyboard, task_priority_keyboard,
    show_task_card, handle_task_action, build_calendar,
    auto_confirm_date, handle_confirm_date
)
from handlers.commands.choose_expense import (
    handle_choose_object, make_choose_keyboard,
    expense_category_keyboard, handle_category
)
from handlers.commands.document import handle_document
from handlers.commands.keyboards import main_menu_keyboard
from handlers.commands.add_menu import handle_add_menu
from handlers.commands.utils import parse_date


_est_extra_pending = None



async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # === Домен: tasks (вынесено в callbacks/tasks.py, сессия 16) ===
    from handlers.commands.callbacks.tasks import try_handle as _try_tasks_cb
    if await _try_tasks_cb(data, query, context):
        return
    
    # === Домен: estimates (est_csv_*, est_period_*, est_per_*, est_rules_*, est_kpi_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_pdf_*, est_export_*, est_extra_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_prices_*, est_price_edit_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_sched_*, est_where_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_buy_*, est_status_*, est_setstatus_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_allwork_*, est_allmat_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_object_floors_*, est_object_rooms_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_room_per_*, est_room_sess_*, est_room_mat_*, est_room_work_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (menu_estimates — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_compare, est_cmp_a_, est_cmp_b_ — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    if data == "est_bykind":
        objs = get_all_objects()
        groups = {}
        for o in objs:
            k = (o.get("object_kind") or o.get("status") or "прочее").lower()
            groups.setdefault(k, []).append(o)
        lines = ["🏷 Объекты по типу:", ""]
        for kind, items in groups.items():
            lines.append(f"   ▸ {kind}: {len(items)} шт.")
        lines.append("")
        lines.append("Выбери тип:")
        kb_rows = []
        for kind, items in list(groups.items())[:8]:
            kb_rows.append([InlineKeyboardButton(
                "🏷 " + str(kind)[:30] + " (" + str(len(items)) + ")",
                callback_data="est_kind_" + kind[:30]
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_bykind: " + str(e), flush=True)
        return

    if data.startswith("est_kind_"):
        kind = data.replace("est_kind_", "")
        objs = get_all_objects()
        matched = [o for o in objs if ((o.get("object_kind") or o.get("status") or "прочее").lower()[:30] == kind)]
        kb_rows = []
        for o in matched[:20]:
            kb_rows.append([InlineKeyboardButton(
                "🏗️ " + str(o.get("name"))[:40],
                callback_data="est_object_" + str(o["id"])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="est_bykind")])
        try:
            await query.edit_message_text(
                "🏷 " + kind + " (" + str(len(matched)) + "):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_kind: " + str(e), flush=True)
        return

    if data == "est_import":
        from core.marketplaces import generate_csv_template
        try:
            path = generate_csv_template("/tmp/prices_template.csv")
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename="prices_template.csv",
                    caption=(
                        "📥 Шаблон прайса (CSV)" + chr(10) + chr(10) +
                        "Заполни и пришли обратно файл — импортирую цены." + chr(10) + chr(10) +
                        "Формат: component_type;rating;poles;brand;price;currency;market_url;market_sku"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
                    ])
                )
        except Exception as e:
            print("est_import: " + str(e), flush=True)
        return

    # === Домен: estimates (est_kpi_* вынесено в callbacks/estimates.py, сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_export_all, est_dash, est_all, est_search — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
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

        if today_tasks:
            sections.append(format_tasks_block(f"СЕГОДНЯ — {today.strftime('%d.%m.%Y')}", today_tasks, '🔥'))
        if tomorrow_tasks:
            sections.append(format_tasks_block(f"ЗАВТРА — {tomorrow.strftime('%d.%m.%Y')}", tomorrow_tasks, '📅'))
        if later_tasks:
            sections.append(format_tasks_block("ПОЗЖЕ", later_tasks, '🗓'))
        if no_deadline:
            sections.append(format_tasks_block("БЕЗ СРОКА", no_deadline, '📋'))

        text = "📋 ЗАДАЧИ\n\n" + "\n\n".join(sections)
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
        buttons.append([InlineKeyboardButton("👤 Мои задачи", callback_data="my_tasks"),
                        InlineKeyboardButton("👥 По исполнителям", callback_data="by_assignee")])
        try:
            from modules import tasks as _t_arch
            _arch_n = len(_t_arch.get_archived_tasks())
        except Exception:
            _arch_n = 0
        if _arch_n:
            buttons.append([InlineKeyboardButton("🗑 Архив (" + str(_arch_n) + ")", callback_data="tasks_archive_list")])
        buttons.append([InlineKeyboardButton("🏗️ По объектам", callback_data="tasks_byobj")])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
        await query.edit_message_text(
            text + "\n\nВыбери задачу:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # === Домен: tasks (my_tasks, by_assignee, byassigned_* — сессия 16) ===
    from handlers.commands.callbacks.tasks import try_handle as _try_tasks_cb
    if await _try_tasks_cb(data, query, context):
        return
    
    # === Домен: KPI (menu_kpi, kpi_masters, kpi_objects, kpi_red — сессия 16) ===
    from handlers.commands.callbacks.kpi import try_handle as _try_kpi_cb
    if await _try_kpi_cb(data, query, context):
        return
    
    # === Домен: Финансы (menu_finance, finobj_* — сессия 16) ===
    from handlers.commands.callbacks.finance import try_handle as _try_finance_cb
    if await _try_finance_cb(data, query, context):
        return
    
    # === Домен: personal (menu_personal, personal_*, exp_type_personal_) — вынесено в callbacks/personal.py ===
    from handlers.commands.callbacks.personal import try_handle as _try_personal_cb
    if await _try_personal_cb(data, query, context):
        return

    # === Домен: misc (personal_cat_ — временно, до personal.py) — вынесено в callbacks/misc.py ===
    from handlers.commands.callbacks.misc import try_handle as _try_misc_cb
    if await _try_misc_cb(data, query, context):
        return


    # === Домен: objects (objexp_*) — вынесено в callbacks/objects.py ===
    from handlers.commands.callbacks.objects import try_handle as _try_objects_cb
    if await _try_objects_cb(data, query, context):
        return


    # === Домен: reports (report_summary_*, report_closed_*, report_open, report_choose_object, report_obj_*) — вынесено в callbacks/reports.py ===
    from handlers.commands.callbacks.reports import try_handle as _try_reports_cb
    if await _try_reports_cb(data, query, context):
        return


    # === Домен: misc (menu_dashboard, menu_help) — вынесено в callbacks/misc.py ===
    from handlers.commands.callbacks.misc import try_handle as _try_misc_cb
    if await _try_misc_cb(data, query, context):
        return


    # === Домен: objects (objtasks_none, objtasks_*, objfin_*, objphotos_*, obj_*) — вынесено в callbacks/objects.py ===
    from handlers.commands.callbacks.objects import try_handle as _try_objects_cb
    if await _try_objects_cb(data, query, context):
        return





async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # --- ПОИСК ПО СМЕТАМ ---
    if getattr(__import__('handlers.commands', fromlist=['_est_search_pending']), '_est_search_pending', False):
        import handlers.commands as _cmd
        _cmd._est_search_pending = False
        q = text.strip().lower()
        if not q:
            await update.message.reply_text("❌ Пустой запрос")
            return
        objs = get_all_objects()
        matched = [o for o in objs if q in (o.get('name') or '').lower()]
        if not matched:
            await update.message.reply_text(
                "🔍 Не найдено: " + text.strip(),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
                ])
            )
            return
        kb_rows = []
        for o in matched[:10]:
            kb_rows.append([InlineKeyboardButton(
                "🏗️ " + str(o.get('name'))[:40],
                callback_data="est_object_" + str(o['id'])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")])
        await update.message.reply_text(
            "🔍 Найдено: " + str(len(matched)),
            reply_markup=InlineKeyboardMarkup(kb_rows)
        )
        return

    # --- ОТДЕЛЬНЫЕ РАБОТЫ ---
    _pend = getattr(__import__('handlers.commands', fromlist=['_est_extra_pending']), '_est_extra_pending', None)
    if _pend and isinstance(_pend, dict):
        step = _pend.get('step')
        object_id = _pend.get('object_id')
        if step == 'title':
            _pend['title'] = text.strip()
            _pend['step'] = 'qty'
            await update.message.reply_text(
                "🔨 " + text.strip() + "\n\nКоличество (число):"
            )
            return
        elif step == 'qty':
            try:
                q = float(text.replace(',', '.'))
            except ValueError:
                await update.message.reply_text("❌ Нужно число")
                return
            _pend['qty'] = q
            _pend['step'] = 'price'
            await update.message.reply_text(
                "🔨 " + _pend['title'] + "\nКол-во: " + str(q) + "\n\nЦена за единицу (₽):"
            )
            return
        elif step == 'price':
            try:
                p = float(text.replace(',', '.'))
            except ValueError:
                await update.message.reply_text("❌ Нужно число")
                return
            from core.extra_works import add_extra_work
            wid = add_extra_work(
                object_id=object_id,
                title=_pend['title'],
                qty=_pend['qty'],
                price=p,
                unit='шт',
            )
            import handlers.commands as _cmd
            _cmd._est_extra_pending = None
            await update.message.reply_text(
                "✅ Работа добавлена!\n\n🔨 " + _pend['title'] + "\nКол-во: " + str(_pend['qty']) + " × " + str(p) + " ₽",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К работам", callback_data="est_extra_" + str(object_id))],
                ])
            )
            return
    # DEBUG: печатаем всё, что приходит
    try:
        with open('/tmp/handle_text.log', 'a') as _f:
            _f.write(f"HANDLE_TEXT: text={text!r}, waiting_for={context.user_data.get('waiting_for')!r}\n")
    except Exception:
        pass
    print(f"🔵 HANDLE_TEXT: text={text!r}, waiting_for={context.user_data.get('waiting_for')!r}", flush=True)
    if not text or text.startswith('/'):
        return

    # Размеры комнаты
    # room_rename — переименование комнаты
    # === Домен: misc (room_rename, obj_rename, panel_comp_rating, task_progress) — вынесено в text/misc.py ===
    from handlers.commands.text.misc import try_handle as _try_misc_text
    if await _try_misc_text(update, context, text):
        return


    if context.user_data.get('waiting_for') in ('floor_new_name', 'panel_new_name', 'child_panel_name', 'component_price', 'route_length', 'plumb_new_name', 'plumb_route_length', 'work_new_qty', 'work_edit_value', 'task_progress_hours', 'task_progress_desc', 'group_load_watt', 'measure_first_dim', 'measure_second_dim', 'wall_angle_value', 'wall_niche_width', 'wall_niche_depth', 'wall_niche_height', 'room_height_point', 'room_height_same', 'wall_round_length', 'wall_round_angle_val', 'wall_round_plane_bottom', 'wall_round_plane_middle', 'wall_round_plane_top', 'opening_width', 'opening_height', 'opening_sill', 'opening_offset', 'opening_edit_value', 'comm_offset_x', 'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_edit_value', 'comm_size', 'comm_size_w', 'comm_size_h', 'comm_size_d', 'comm_edit_size_part', 'wall_round_opening_width', 'wall_round_opening_height', 'comm_offset_x', 'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_edit_value',
                                                  'wall_round_length', 'wall_round_angle_val', 'wall_round_plane_bottom', 'wall_round_plane_middle', 'wall_round_plane_top'):
        from interfaces.telegram.rooms import handle_measure_input
        await handle_measure_input(update, context)
        return

    # Новая комната — просим тип (черновая/чистовая/промежуточная)
    # === Домен: rooms (room_name, wall_question) — вынесено в text/rooms.py ===
    from handlers.commands.text.rooms import try_handle as _try_rooms_text
    if await _try_rooms_text(update, context, text):
        return


    # === Домен: CRM (crm_*, activity_*) — вынесено в text/crm.py ===
    from handlers.commands.text.crm import try_handle as _try_crm_text
    if await _try_crm_text(update, context, text):
        return


    # === ДАЛЬШЕ — СТАРАЯ ЛОГИКА (новые задачи, расходы и т.д.) ===


    # === Домен: tasks (new_task_text) — вынесено в text/tasks.py ===
    from handlers.commands.text.tasks import try_handle as _try_tasks_text
    if await _try_tasks_text(update, context, text):
        return

    # === Домен: finances (new_expense_text) — вынесено в text/finances.py ===
    from handlers.commands.text.finances import try_handle as _try_fin_text
    if await _try_fin_text(update, context, text):
        return

    # === Домен: personal (personal_expense_text) — вынесено в text/personal.py ===
    from handlers.commands.text.personal import try_handle as _try_pers_text
    if await _try_pers_text(update, context, text):
        return


    # === Домен: objects (new_object) — вынесено в text/objects.py ===
    from handlers.commands.text.objects import try_handle as _try_objects_text
    if await _try_objects_text(update, context, text):
        return

    # === Домен: tasks (setdate_task, rename_task) — вынесено в text/tasks.py ===
    from handlers.commands.text.tasks import try_handle as _try_tasks_text
    if await _try_tasks_text(update, context, text):
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

    if action == 'income':
        obj = result['object']
        amount = result['amount']
        category = result.get('category', 'доход')
        add_income(obj['id'], amount, category)
        await update.message.reply_text(
            f"💰 Доход {amount} ₽ ({category}) добавлен в «{obj['name']}»"
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
            context.user_data['pending_task_title'] = result.get('title') or result.get('original_text', '')
        await update.message.reply_text(
            f"🤔 Нашёл несколько объектов. Какой именно?",
            reply_markup=make_choose_keyboard(objects, intent, amount, category)
        )
        return

    # === CRM: ожидаем бюджет сделки ===

    # === УМНЫЙ FALLBACK: сразу ищем похожие объекты ===
    context.user_data['unknown_text'] = text

    # Ищем похожие объекты через rapidfuzz
    print(f"🔍 UNKNOWN: text={text!r}", flush=True)
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
    all_objs = get_all_objects()
    print(f"🔍 UNKNOWN: all_objs={len(all_objs)}", flush=True)
    text_lower = text.strip().lower()
    exact_match = None
    similar = []
    for o in all_objs:
        if (o.get('name') or '').lower() == text_lower:
            exact_match = o
            break
    if not exact_match and all_objs:
        names = [o.get('name') or '' for o in all_objs]
        matches = rf_process.extract(text, names, scorer=rf_fuzz.WRatio, limit=5)
        for name, score, idx in matches:
            if score >= 55:
                similar.append((all_objs[idx], score))

    if exact_match:
        context.user_data['unknown_text'] = None
        await update.message.reply_text(
            f"✅ *Нашёл объект!*\n\n"
            f"🏗️ {exact_match['name']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ Открыть объект", callback_data=f"obj_{exact_match['id']}")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    buttons = []
    if similar:
        for o, score in similar:
            buttons.append([InlineKeyboardButton(
                f"🏗️ {o['name']} ({int(score)}%)",
                callback_data=f"obj_{o['id']}"
            )])
    buttons.append([InlineKeyboardButton(f"➕ Создать новый объект «{text[:40]}»", callback_data="unknown_as_object")])
    buttons.append([InlineKeyboardButton("👤 Это клиент", callback_data="unknown_as_client"),
                    InlineKeyboardButton("📋 Это задача", callback_data="unknown_as_task")])
    buttons.append([InlineKeyboardButton("💰 Расход на объект", callback_data="unknown_as_expense"),
                    InlineKeyboardButton("💸 Личный расход", callback_data="unknown_as_personal")])
    buttons.append([InlineKeyboardButton("❌ Ничего", callback_data="unknown_cancel")])

    header = f"🤔 Не распознал: «{text[:80]}»\n\n"
    if similar:
        header += f"🔍 Нашёл {len(similar)} похожих объектов.\nВыбери:"
    else:
        header += "Что с этим сделать?"

    await update.message.reply_text(
        header,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# === УТОЧНЕНИЕ ОБЪЕКТА ===
