"""Text-хендлеры домена «CRM» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_text).
Блоки: crm_client_*, crm_deal_*, activity_*.

Роутер try_handle(update, context, text) -> bool.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import get_connection
from modules.phone_utils import parse_phone, get_country_label
from modules.parser import parse_amount
from handlers.commands.utils import parse_date
from handlers.commands.crm import _finalize_new_client


async def try_handle(update, context, text: str) -> bool:
    """Обрабатывает text-команды CRM. True = обработано."""

    # === ВСЕ CRM-ОЖИДАНИЯ — В САМОМ НАЧАЛЕ, ДО ПАРСЕРА ===

    # CRM: ждём имя нового клиента (для сделки)
    if context.user_data.get('waiting_for') == 'crm_deal_new_client_name':
        name = text.strip()
        context.user_data['crm_new_client_name'] = name
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"👤 Создать клиента «{name}»?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Создать и продолжить сделку", callback_data="crm_new_client_for_deal")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_crm")],
            ])
        )
        print(f"⚠️ RETURN на строке 2330", flush=True)
        return True

    # CRM: ждём имя клиента (обычный сценарий)
    if context.user_data.get('waiting_for') == 'crm_client_name':
        context.user_data['crm_new_client_name'] = text.strip()
        context.user_data['waiting_for'] = 'crm_client_phone'
        await update.message.reply_text(
            f"👤 Имя: «{text.strip()}»\n\n📞 Теперь телефон (или Пропустить):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_phone")],
            ])
        )
        print(f"⚠️ RETURN на строке 2342", flush=True)
        return True

    if context.user_data.get('waiting_for') == 'crm_client_phone':
        from modules.phone_utils import parse_phone, get_country_label
        raw = text.strip()
        result = parse_phone(raw)
        status = result.get('status')

        if status == 'ok':
            normalized = result['phone']
            country = get_country_label(normalized)
            context.user_data['crm_new_client_phone'] = normalized
            context.user_data['waiting_for'] = 'crm_client_address'
            await update.message.reply_text(
                f"✅ Телефон распознан: {normalized}\n"
                f"{country}\n\n"
                f"📍 Теперь адрес (или Пропустить):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Изменить телефон", callback_data="crm_phone_edit")],
                    [InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_address")],
                ])
            )
            print(f"⚠️ RETURN на строке 2364", flush=True)
            return True

        if status == 'suggest':
            variants = result.get('variants', [])
            context.user_data['phone_variants'] = variants
            buttons = []
            for v in variants:
                label = f"📞 {v}"
                buttons.append([InlineKeyboardButton(label, callback_data=f"crm_phone_pick_{v}")])
            buttons.append([InlineKeyboardButton("✏️ Ввести заново", callback_data="crm_phone_edit")])
            buttons.append([InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_phone")])
            await update.message.reply_text(
                f"🤔 Номер «{raw}» нестандартный.\n\n"
                f"Выбери подходящий вариант:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            print(f"⚠️ RETURN на строке 2380", flush=True)
            return True

        # invalid
        await update.message.reply_text(
            f"❌ Номер «{raw}» слишком короткий или не распознан.\n\n"
            f"Введи в формате:\n"
            f"• +79991234567 (Россия)\n"
            f"• 89991234567 (Россия)\n"
            f"• 9991234567 (Россия, 10 цифр)\n"
            f"• +491234567890 (Европа)\n\n"
            f"Или нажми «Пропустить».",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Ввести заново", callback_data="crm_phone_edit")],
                [InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_phone")],
            ])
        )
        print(f"⚠️ RETURN на строке 2396", flush=True)
        return True

    if context.user_data.get('waiting_for') == 'crm_client_address':
        context.user_data['crm_new_client_address'] = text.strip()
        context.user_data['waiting_for'] = 'crm_client_source'
        phone = context.user_data.get('crm_new_client_phone')
        phone_line = f"📞 Телефон: {phone}\n" if phone else "📞 Телефон: —\n"
        await update.message.reply_text(
            f"📍 Адрес: {text.strip()}\n\n"
            f"{phone_line}\n"
            f"🔗 Откуда узнал? Или Пропустить:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Изменить телефон", callback_data="crm_phone_edit")],
                [InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_source")],
            ])
        )
        print(f"⚠️ RETURN на строке 2412", flush=True)
        return True

    if context.user_data.get('waiting_for') == 'crm_client_source':
        context.user_data['crm_new_client_source'] = text.strip()
        await _finalize_new_client(update, context)
        print(f"⚠️ RETURN на строке 2417", flush=True)
        return True

    # CRM: ждём бюджет сделки — ВАЖНО до парсера
    if context.user_data.get('waiting_for') == 'crm_deal_budget':
        try:
            budget = parse_amount(text) or 0
        except Exception:
            budget = 0
        client_id = context.user_data.get('crm_deal_client_id')
        if not client_id:
            await update.message.reply_text("❌ Клиент потерялся. Начни заново.")
            context.user_data['waiting_for'] = None
            print(f"⚠️ RETURN на строке 2430", flush=True)
            return True
        from modules.crm import add_deal, get_client
        deal_id = add_deal(client_id=client_id, object_id=None, status='new', budget=budget)
        c = get_client(client_id)
        context.user_data['waiting_for'] = None
        context.user_data['crm_deal_client_id'] = None
        await update.message.reply_text(
            f"✅ Сделка #{deal_id} создана!\n\n"
            f"👤 Клиент: {c['name'] if c else '—'}\n"
            f"💼 Бюджет: {budget} ₽\n"
            f"📊 Статус: 🆕 Новая",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 К клиентам", callback_data="crm_clients")],
                [InlineKeyboardButton("💼 К сделкам", callback_data="crm_deals")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        print(f"⚠️ RETURN на строке 2447", flush=True)
        return True

    # CRM: пользователь ввёл имя в режиме выбора клиента
    if context.user_data.get('waiting_for') == 'crm_deal_pick_client':
        name = text.strip()
        from modules.crm import get_clients
        clients = get_clients()
        found = None
        for c in clients:
            if c['name'].lower().strip() == name.lower():
                found = c
                break
        if found:
            context.user_data['crm_deal_client_id'] = found['id']
            context.user_data['waiting_for'] = 'crm_deal_budget'
            await update.message.reply_text(
                f"💼 Клиент: «{found['name']}»\n\nНапиши сумму бюджета сделки (₽):"
            )
            print(f"⚠️ RETURN на строке 2465", flush=True)
            return True
        else:
            context.user_data['crm_new_client_name'] = name
            context.user_data['waiting_for'] = None
            await update.message.reply_text(
                f"👤 Клиента «{name}» нет в списке.\n\nСоздать нового и продолжить сделку?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Создать и продолжить", callback_data="crm_new_client_for_deal")],
                    [InlineKeyboardButton("⬅️ К списку", callback_data="crm_deal_add")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="menu_crm")],
                ])
            )
            print(f"⚠️ RETURN на строке 2477", flush=True)
            return True

    # === ЗАПЛАНИРОВАННЫЙ ЗВОНОК ===
    if context.user_data.get('waiting_for') == 'activity_plan_datetime':
        from modules.crm import add_activity, get_client
        client_id = context.user_data.get('activity_client_id')
        if not client_id:
            context.user_data['waiting_for'] = None
            await update.message.reply_text('❌ Клиент потерялся.')
            print(f"⚠️ RETURN на строке 2487", flush=True)
            return True
        # Парсим дату и время из текста
        parsed = parse_date(text)
        due_str = None
        if parsed:
            due_str = parsed.strftime('%Y-%m-%d')
        add_activity(
            client_id=client_id,
            user_id=update.effective_user.id,
            type_='call',
            description=text.strip(),
            due_date=due_str
        )
        cl = get_client(client_id)
        context.user_data['waiting_for'] = None
        context.user_data['activity_client_id'] = None
        context.user_data['activity_type'] = None
        due_display = parsed.strftime('%d.%m.%Y') if parsed else 'без даты'
        await update.message.reply_text(
            f'✅ Звонок запланирован: {due_display}\n👤 {cl["name"] if cl else "—"}',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('👤 К клиенту', callback_data=f'client_{client_id}')],
                [InlineKeyboardButton('📋 Активности', callback_data=f'activity_list_{client_id}')],
            ])
        )
        print(f"⚠️ RETURN на строке 2512", flush=True)
        return True

    # === ДИАПАЗОН СРОКА (обработка ввода) ===
    if context.user_data.get('range_step') == 'start':
        d = parse_date(text)
        if not d:
            await update.message.reply_text('❌ Не понял дату начала. Попробуй: «завтра», «1.10», «пн», «10.10.2025»')
            print(f"⚠️ RETURN на строке 2519", flush=True)
            return True
        context.user_data['range_start'] = d.strftime('%Y-%m-%d')
        context.user_data['range_step'] = 'end'
        await update.message.reply_text(
            f"📆 Старт: {d.strftime('%d.%m.%Y')}\n\n"
            f"Теперь дата конца:"
        )
        print(f"⚠️ RETURN на строке 2526", flush=True)
        return True

    if context.user_data.get('range_step') == 'end':
        d_end = parse_date(text)
        if not d_end:
            await update.message.reply_text('❌ Не понял дату конца. Попробуй: «8.10», «+5», «пятница»')
            print(f"⚠️ RETURN на строке 2532", flush=True)
            return True
        task_id = context.user_data.get('range_task')
        start = context.user_data.get('range_start')
        from modules.tasks import set_task_range
        from datetime import datetime as _dt
        d_start = _dt.strptime(start, '%Y-%m-%d').date()
        if d_end < d_start:
            await update.message.reply_text('❌ Конец раньше старта. Введи ещё раз.')
            print(f"⚠️ RETURN на строке 2540", flush=True)
            return True
        set_task_range(task_id, start, d_end.strftime('%Y-%m-%d'))
        days = (d_end - d_start).days + 1
        context.user_data['range_step'] = None
        context.user_data['range_task'] = None
        context.user_data['range_start'] = None
        await update.message.reply_text(
            f"✅ Срок: {d_start.strftime('%d.%m.%Y')} — {d_end.strftime('%d.%m.%Y')} ({days} дн.)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('📋 К задаче', callback_data=f'task_{task_id}')],
                [InlineKeyboardButton('🏠 Меню', callback_data='menu_back')],
            ])
        )
        print(f"⚠️ RETURN на строке 2553", flush=True)
        return True

    # === ДЛИТЕЛЬНОСТЬ (обработка ввода) ===
    if context.user_data.get('duration_step') == 'start':
        d = parse_date(text)
        if not d:
            await update.message.reply_text('❌ Не понял дату старта. Попробуй: «завтра», «1.10»')
            print(f"⚠️ RETURN на строке 2560", flush=True)
            return True
        context.user_data['duration_start'] = d.strftime('%Y-%m-%d')
        context.user_data['duration_step'] = 'days'
        await update.message.reply_text(
            f"⏳ Старт: {d.strftime('%d.%m.%Y')}\n\n"
            f"Сколько дней? Напиши число (например, 3):"
        )
        print(f"⚠️ RETURN на строке 2567", flush=True)
        return True

    if context.user_data.get('duration_step') == 'days':
        try:
            n = int(text.strip())
        except ValueError:
            await update.message.reply_text('❌ Нужно число. Напиши, сколько дней.')
            print(f"⚠️ RETURN на строке 2574", flush=True)
            return True
        if n < 1 or n > 365:
            await update.message.reply_text('❌ От 1 до 365 дней.')
            print(f"⚠️ RETURN на строке 2577", flush=True)
            return True
        task_id = context.user_data.get('duration_task')
        start = context.user_data.get('duration_start')
        from modules.tasks import set_task_range
        from datetime import datetime as _dt, timedelta
        d_start = _dt.strptime(start, '%Y-%m-%d').date()
        d_end = d_start + timedelta(days=n - 1)
        set_task_range(task_id, start, d_end.strftime('%Y-%m-%d'))
        context.user_data['duration_step'] = None
        context.user_data['duration_task'] = None
        context.user_data['duration_start'] = None
        await update.message.reply_text(
            f"✅ Срок: {d_start.strftime('%d.%m.%Y')} — {d_end.strftime('%d.%m.%Y')} ({n} дн.)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('📋 К задаче', callback_data=f'task_{task_id}')],
                [InlineKeyboardButton('🏠 Меню', callback_data='menu_back')],
            ])
        )
        print(f"⚠️ RETURN на строке 2595", flush=True)
        return True

    # === АКТИВНОСТИ КЛИЕНТА ===
    if context.user_data.get('waiting_for') == 'activity_text':
        from modules.crm import add_activity, get_client
        client_id = context.user_data.get('activity_client_id')
        atype = context.user_data.get('activity_type')
        if not client_id or not atype:
            context.user_data['waiting_for'] = None
            await update.message.reply_text('❌ Клиент потерялся. Начни заново.')
            print(f"⚠️ RETURN на строке 2605", flush=True)
            return True
        add_activity(client_id=client_id, user_id=update.effective_user.id, type_=atype, description=text.strip())
        cl = get_client(client_id)
        context.user_data['waiting_for'] = None
        context.user_data['activity_client_id'] = None
        context.user_data['activity_type'] = None
        type_names = {'call': '📞 Звонок', 'meeting': '🤝 Встреча', 'note': '📝 Заметка'}
        await update.message.reply_text(
            f'✅ {type_names.get(atype, atype)} записан клиенту «{cl["name"] if cl else "—"}»',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('👤 К клиенту', callback_data=f'client_{client_id}')],
                [InlineKeyboardButton('🏠 Меню', callback_data='menu_back')],
            ])
        )
        print(f"⚠️ RETURN на строке 2619", flush=True)
        return True

    return False
