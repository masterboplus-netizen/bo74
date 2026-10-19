        f"Фаза: {phase}ф ({voltage}В)\n"
        f"Мощность: {int(load_watt)} Вт\n"
        f"Ток: {current} А\n"
        f"Автомат: *{breaker_type}*\n"
        f"Кабель: *{core_spec.get_cable_label(cable)}*"
        f"Щит: " + (core_elec_panels.get_panel(_object_panels[0]["id"])["name"] if (_object_panels and len(_object_panels) == 1 and core_elec_panels) else "не привязан") + "\n"
    )

    # Кнопки — ведём к группам этажа
    kb_btns = []
    if floor_id:
        kb_btns.append([InlineKeyboardButton("➕ Ещё группу", callback_data=f"floor_group_new_{floor_id}")])
        kb_btns.append([InlineKeyboardButton("⚡ К группам этажа", callback_data=f"floor_groups_{floor_id}")])
    if room_id:
        kb_btns.append([InlineKeyboardButton("⚡ К группам комнаты", callback_data=f"room_groups_{room_id}")])

        if len(_object_panels) > 1:
            kb_btns.append([InlineKeyboardButton("⚡ Привязать к щиту", callback_data="group_panel_pick_" + str(group_id))])

    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb_btns) if kb_btns else None
    )


async def handle_measure_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер текстового ввода по waiting_for."""
    step = context.user_data.get('waiting_for')
    if not step:
        return

    # --- КАБЕЛЬНЫЙ ЖУРНАЛ ---
    if step == 'cable_from_point':
        val = (update.message.text or '').strip()
        if not val:
            await update.message.reply_text("Введи текст")
            return
        context.user_data['cable_from_point'] = val
        context.user_data['waiting_for'] = 'cable_to_point'
        await update.message.reply_text("Куда кабель (к точке)?")
        return

    if step == 'cable_to_point':
        val = (update.message.text or '').strip()
        if not val:
            await update.message.reply_text("Введи текст")
            return
        context.user_data['cable_to_point'] = val
        context.user_data['waiting_for'] = 'cable_length'
        await update.message.reply_text("Длина кабеля (метры)?")
        return

    if step == 'cable_length':
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            length_m = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if length_m <= 0 or length_m > 1000:
            await update.message.reply_text("Длина от 0.1 до 1000 м")
            return
        object_id = context.user_data.get('cable_object_id')
        group_id = context.user_data.get('cable_group_id')
        frm = context.user_data.get('cable_from_point')
        to = context.user_data.get('cable_to_point')
        cable_type = None
        try:
            if group_id:
                _g = core_elec.get_group(group_id)
                cable_type = _g.get('cable_type') if _g else None
        except Exception:
            pass
        try:
            core_elec.add_cable(
                object_id=object_id,
                group_id=group_id,
                from_point=frm,
                to_point=to,
                cable_type=cable_type,
                length_m=length_m,
                route_type=None,
                note=None,
            )
        except Exception as e:
            print(f"add_cable: {e}", flush=True)
        for k in ['cable_object_id', 'cable_group_id', 'cable_from_point', 'cable_to_point', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            "Кабель добавлен!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("К журналу", callback_data="cables_list_" + str(object_id))],
            ])
        )
        return

    if step == 'route_length':
        route_id = context.user_data.get('route_edit_id')
        if not route_id:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            length = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if length <= 0 or length > 10000:
            await update.message.reply_text("Длина от 0.1 до 10 000 м")
            return
        try:
            core_elec_routes.update_route(route_id, length_m=length, is_manual=1)
        except Exception as e:
            print("route set len: " + str(e), flush=True)
        for k in ['route_edit_id', 'waiting_for']:
            context.user_data[k] = None
        try:
            r = core_elec_routes.get_route(route_id)
            gid = r.get('group_id') if r else None
        except Exception:
            gid = None
        kb = []
        if gid:
            kb.append([InlineKeyboardButton("📏 К трассам", callback_data="group_routes_" + str(gid))])
        kb.append([InlineKeyboardButton("⬅️ К трассе", callback_data="route_" + str(route_id))])
        await update.message.reply_text(
            "✅ Длина сохранена: " + str(length) + " м",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if step == 'plumb_route_length':
        panel_id = context.user_data.get('plumb_route_panel_id')
        pipe_type = context.user_data.get('plumb_route_pipe')
        if not panel_id or not pipe_type:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            length = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if length <= 0 or length > 10000:
            await update.message.reply_text("Длина от 0.1 до 10 000 м")
            return
        try:
            p = core_plumbing.get_panel(panel_id)
            object_id = p.get('object_id') if p else None
            rid = core_plumbing.create_route(
                object_id=object_id, panel_id=panel_id,
                pipe_type=pipe_type, length_m=length,
                route_type='shtroba'
            )
        except Exception as e:
            print("plumb route create: " + str(e), flush=True)
            rid = None
        for k in ['plumb_route_panel_id', 'plumb_route_pipe', 'waiting_for']:
            context.user_data[k] = None
        if rid:
            await update.message.reply_text(
                "Трасса создана: " + core_plumbing.get_pipe_label(pipe_type) + " · " + str(length) + " м",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📏 К трассам", callback_data="plumb_routes_" + str(panel_id))],
                    [InlineKeyboardButton("📏 Открыть", callback_data="plumb_route_" + str(rid))],
                ])
            )
        else:
            await update.message.reply_text("Не удалось создать трассу")
        return

    if step == 'work_edit_value':
        work_id = context.user_data.get('work_edit_id')
        field = context.user_data.get('work_edit_field')
        if not work_id or not field:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            num = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if num <= 0 or num > 1000000:
            await update.message.reply_text("Значение от 0.1 до 1 000 000")
            return
        try:
            core_works.update_work(work_id, **{field: num, 'is_manual': 1})
        except Exception as e:
            print("work edit: " + str(e), flush=True)
        for k in ['work_edit_id', 'work_edit_field', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            "Сохранено",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔨 К работе", callback_data="works_" + str(work_id))],
            ])
        )
        return

    if step == 'work_new_qty':
        object_id = context.user_data.get('work_new_object_id')
        wtype = context.user_data.get('work_new_type')
        if not object_id or not wtype:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            qty = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if qty <= 0 or qty > 100000:
            await update.message.reply_text("Количество от 0.1 до 100 000")
            return
        try:
            wid = core_works.create_work(object_id, wtype, qty=qty)
        except Exception as e:
            print("work create: " + str(e), flush=True)
            wid = None
        for k in ['work_new_object_id', 'work_new_type', 'waiting_for']:
            context.user_data[k] = None
        if wid:
            await update.message.reply_text(
                "Работа добавлена",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔨 К работам", callback_data="works_list_" + str(object_id))],
                ])
            )
        else:
            await update.message.reply_text("Не удалось добавить")
        return

    if step == 'plumb_new_name':
        name = (update.message.text or '').strip()
        if not name:
            await update.message.reply_text("Введи название")
            return
        object_id = context.user_data.get('plumb_new_object_id')
        ptype = context.user_data.get('plumb_new_type') or 'collector'
        if not object_id:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        try:
            pid = core_plumbing.create_panel(object_id, name, ptype, mount_type='wall')
        except Exception as e:
            print("plumb create: " + str(e), flush=True)
            pid = None
        for k in ['plumb_new_object_id', 'plumb_new_type', 'waiting_for']:
            context.user_data[k] = None
        if pid:
            await update.message.reply_text(
                "Создано: " + name,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Открыть", callback_data="plumb_" + str(pid))],
                    [InlineKeyboardButton("К сантехнике", callback_data="plumb_list_" + str(object_id))],
                ])
            )
        else:
            await update.message.reply_text("Не удалось создать")
        return

    if step == 'component_price':
        comp_id = context.user_data.get('component_price_id')
        if not comp_id:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            price = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if price < 0 or price > 1000000:
            await update.message.reply_text("Цена от 0 до 1 000 000")
            return
        try:
            from core.db import commit
            commit("UPDATE elec_panel_components SET price_unit = ?, price_source = 'manual', price_updated_at = CURRENT_TIMESTAMP WHERE id = ?", (price, comp_id))
        except Exception as e:
            print("set price: " + str(e), flush=True)
        for k in ['component_price_id', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            "✅ Цена сохранена: " + str(price) + " ₽",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К компоненту", callback_data="panel_comp_item_" + str(comp_id))],
            ])
        )
        return

    if step == 'panel_new_name':
        name = (update.message.text or '').strip()
        if not name:
