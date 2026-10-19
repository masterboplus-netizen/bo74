                    ])
                )
            except Exception:
                pass
            return True
        text = (
            "Автокомплектация выполнена" + chr(10) + chr(10) +
            "Создано компонентов: " + str(result.get('created', 0)) + chr(10) +
            "Ручных (сохранено): " + str(result.get('manual', 0)) + chr(10) +
            "Групп: " + str(result.get('groups', 0)) + chr(10) +
            "Нагрузка: " + str(result.get('total_watt', 0)) + " Вт" + chr(10) +
            "С K_одновр: " + str(result.get('calc_watt', 0)) + " Вт"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Комплектация", callback_data="panel_comp_" + str(panel_id))],
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_comp_price_"):
        comp_id = int(data.replace("panel_comp_price_", ""))
        context.user_data['component_price_id'] = comp_id
        context.user_data['waiting_for'] = 'component_price'
        try:
            await query.edit_message_text(
                "💰 Введи новую цену (₽):" + chr(10) + chr(10) + "_Например: 350_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_item_" + str(comp_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_comp_del_"):
        comp_id = int(data.replace("panel_comp_del_", ""))
        try:
            c = core_elec_panels.get_component(comp_id)
            panel_id = c.get('panel_id') if c else None
            if c:
                core_elec_panels.delete_component(comp_id)
        except Exception as e:
            print("panel comp del: " + str(e), flush=True)
            panel_id = None
        if panel_id:
            try:
                await query.edit_message_text(
                    "✅ Компонент удалён",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К комплектации", callback_data="panel_comp_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("panel_comp_item_"):
        comp_id = int(data.replace("panel_comp_item_", ""))
        try:
            c = core_elec_panels.get_component(comp_id)
        except Exception as e:
            print("panel comp item: " + str(e), flush=True)
            c = None
        if not c:
            try:
                await query.edit_message_text("Компонент не найден")
            except Exception:
                pass
            return True
        panel_id = c.get('panel_id')
        # Найти порядковый номер компонента среди всех компонентов щита
        try:
            all_comps = core_elec_panels.get_components(panel_id)
            idx = next((i for i, x in enumerate(all_comps, start=1) if x['id'] == comp_id), 0)
            total = len(all_comps)
        except Exception:
            idx = 0
            total = 0
        lines = ["🔧 Компонент " + str(idx) + " из " + str(total), ""]
        lines.append("Тип: " + str(c.get('component_type') or '?'))
        if c.get('component_model'):
            lines.append("Модель: " + str(c['component_model']))
        if c.get('rating'):
            lines.append("Номинал: " + str(c['rating']) + "А")
        if c.get('poles'):
            lines.append("Полюса: " + str(c['poles']) + "P")
        if c.get('curve'):
            lines.append("Кривая: " + str(c['curve']))
        if c.get('rcd_ma'):
            lines.append("УЗО: " + str(c['rcd_ma']) + "мА")
        if c.get('quantity'):
            lines.append("Количество: " + str(c['quantity']))
        if c.get('is_manual'):
            lines.append("Тип: [ручной]")
        lines.append("")
        try:
            price = core_elec_panels.calc_component_price(c)
        except Exception:
            price = 0
        unit_price = c.get('price_unit')
        if unit_price:
            lines.append("💰 Цена за шт: " + str(unit_price) + " ₽ [ручная]")
        lines.append("💰 Итого: " + str(price) + " ₽")
        kb_rows = [
            [InlineKeyboardButton("💰 Изменить цену", callback_data="panel_comp_price_" + str(comp_id))],
            [InlineKeyboardButton("🗑 Удалить", callback_data="panel_comp_del_" + str(comp_id))],
            [InlineKeyboardButton("⬅️ К комплектации", callback_data="panel_comp_" + str(panel_id))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_rating_set_"):
        tail = data.replace("panel_comp_rating_set_", "")
        try:
            pid_str, rest = tail.split("_", 1)
            panel_id = int(pid_str)
            ctype, rating_str = rest.rsplit("_", 1)
            rating = int(rating_str)
        except Exception as e:
            print("rating set parse: " + str(e), flush=True)
            return True
        try:
            _curve = context.user_data.get("panel_comp_curve") or "C"
            core_elec_panels.add_component(panel_id, component_type=ctype, rating=rating, curve=_curve, is_manual=1)
            context.user_data.pop("panel_comp_curve", None)
        except Exception as e:
            print("rating set add: " + str(e), flush=True)
        try:
            await _safe_edit(query, "✅ Компонент добавлен", InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К комплектации", callback_data="panel_comp_" + str(panel_id))],
            ]))
        except Exception:
            pass
        return True

    if data.startswith("panel_comp_rating_manual_"):
        tail = data.replace("panel_comp_rating_manual_", "")
        try:
            pid_str, ctype = tail.rsplit("_", 1)
            panel_id = int(pid_str)
        except Exception as e:
            print("rating manual parse: " + str(e), flush=True)
            return True
        context.user_data["panel_comp_panel_id"] = panel_id
        context.user_data["panel_comp_type"] = ctype
        context.user_data["waiting_for"] = "panel_comp_rating"
        labels = {"breaker": "Автомат", "rcd": "УЗО", "dif": "Дифавтомат", "meter": "Счётчик", "relay": "Реле"}
        tlabel = labels.get(ctype, ctype)
        await _safe_edit(query, "⚡ " + str(tlabel) + chr(10) + chr(10) + "Напиши номинал (А):", InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_comp_curve_set_"):
        tail = data.replace("panel_comp_curve_set_", "")
        try:
            pid_str, rest = tail.split("_", 1)
            panel_id = int(pid_str)
            ctype, curve = rest.rsplit("_", 1)
        except Exception as e:
            print("curve parse: " + str(e), flush=True)
            return True
        context.user_data["panel_comp_curve"] = curve
        context.user_data["panel_comp_panel_id"] = panel_id
        context.user_data["panel_comp_type"] = ctype
        labels = {"breaker": "Автомат", "rcd": "УЗО", "dif": "Дифавтомат", "meter": "Счётчик", "relay": "Реле"}
        tlabel = labels.get(ctype, ctype)
        RATINGS = {"breaker": [6, 10, 16, 20, 25, 32, 40, 50, 63], "rcd": [16, 25, 32, 40, 63, 80, 100], "dif": [16, 20, 25, 32, 40, 63], "meter": [5, 10, 16, 25, 32, 40, 63], "relay": [16, 25, 32, 40, 63]}
        rs = RATINGS.get(ctype, [6, 10, 16, 20, 25, 32, 40, 63])
        kb_rows = []
        row = []
        for r in rs:
            row.append(InlineKeyboardButton(str(r), callback_data="panel_comp_rating_set_" + str(panel_id) + "_" + ctype + "_" + str(r)))
            if len(row) == 3:
                kb_rows.append(row); row = []
        if row: kb_rows.append(row)
        kb_rows.append([InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_" + str(panel_id))])
        text_out = "⚡ " + str(tlabel) + " — кривая " + str(curve) + chr(10) + chr(10) + "Выбери номинал (А):"
        await _safe_edit(query, text_out, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_type_"):
        tail = data.replace("panel_comp_type_", "")
        pid_str, ctype = tail.rsplit("_", 1)
        panel_id = int(pid_str)
        context.user_data["panel_comp_panel_id"] = panel_id
        context.user_data["panel_comp_type"] = ctype
        context.user_data["waiting_for"] = "panel_comp_rating"
        labels = {"breaker": "Автомат", "rcd": "УЗО", "dif": "Дифавтомат", "meter": "Счётчик", "relay": "Реле"}
        tlabel = labels.get(ctype, ctype)
        RATINGS = {"breaker": [6, 10, 16, 20, 25, 32, 40, 50, 63], "rcd": [16, 25, 32, 40, 63, 80, 100], "dif": [16, 20, 25, 32, 40, 63], "meter": [5, 10, 16, 25, 32, 40, 63], "relay": [16, 25, 32, 40, 63]}
        rs = RATINGS.get(ctype, [6, 10, 16, 20, 25, 32, 40, 63])
        kb_rows = []
        if ctype in ("breaker", "dif"):
            kb_rows.append([
                InlineKeyboardButton("A", callback_data="panel_comp_curve_set_" + str(panel_id) + "_" + ctype + "_A"),
                InlineKeyboardButton("B", callback_data="panel_comp_curve_set_" + str(panel_id) + "_" + ctype + "_B"),
                InlineKeyboardButton("C", callback_data="panel_comp_curve_set_" + str(panel_id) + "_" + ctype + "_C"),
                InlineKeyboardButton("D", callback_data="panel_comp_curve_set_" + str(panel_id) + "_" + ctype + "_D"),
            ])
        row = []
        for r in rs:
            row.append(InlineKeyboardButton(str(r), callback_data="panel_comp_rating_set_" + str(panel_id) + "_" + ctype + "_" + str(r)))
            if len(row) == 3:
                kb_rows.append(row); row = []
        if row: kb_rows.append(row)
        kb_rows.append([InlineKeyboardButton("✏️ Другое (ввод вручную)", callback_data="panel_comp_rating_manual_" + str(panel_id) + "_" + ctype)])
        kb_rows.append([InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_" + str(panel_id))])
        text_out = "⚡ " + str(tlabel) + chr(10) + chr(10) + "Выбери номинал (А):"
        await _safe_edit(query, text_out, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_add_"):
        panel_id = int(data.replace("panel_comp_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("⚡ Автомат", callback_data="panel_comp_type_" + str(panel_id) + "_breaker")],
            [InlineKeyboardButton("🛡️ УЗО", callback_data="panel_comp_type_" + str(panel_id) + "_rcd")],
            [InlineKeyboardButton("🛡️⚡ Дифавтомат", callback_data="panel_comp_type_" + str(panel_id) + "_dif")],
            [InlineKeyboardButton("🔢 Счётчик", callback_data="panel_comp_type_" + str(panel_id) + "_meter")],
            [InlineKeyboardButton("🔌 Реле", callback_data="panel_comp_type_" + str(panel_id) + "_relay")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_" + str(panel_id))],
        ]
        await _safe_edit(query, "➕ Ручной компонент" + chr(10) + chr(10) + "Выбери тип:", InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_"):
        panel_id = int(data.replace("panel_comp_", ""))
        try:
            comps = core_elec_panels.get_components(panel_id)
            text = core_elec_panels.format_panel_components(panel_id)
        except Exception as e:
            print("panel comp: " + str(e), flush=True)
            comps = []
            text = "Ошибка"
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "... (обрезано)"
        kb_rows = []
        for idx, c in enumerate(comps, start=1):
            label = core_elec_panels.format_component(c)[:40]
            mark = " [ручной]" if c.get('is_manual') else ""
            num = str(idx) + ". "
            kb_rows.append([InlineKeyboardButton(
                num + label + mark,
                callback_data="panel_comp_item_" + str(c['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить вручную", callback_data="panel_comp_add_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_stats_"):
        panel_id = int(data.replace("panel_stats_", ""))
        try:
            stats = core_elec_panels.get_panel_stats(panel_id)
        except Exception as e:
            print("panel stats: " + str(e), flush=True)
            stats = None
        if not stats:
            try:
                await query.edit_message_text("Ошибка статистики")
            except Exception:
                pass
            return True
        text = (
            "Статистика щита" + chr(10) + chr(10) +
            "Компонентов: " + str(stats.get('components_total', 0)) + chr(10) +
            "Модулей занято: " + str(stats.get('modules_used', 0)) + chr(10) +
            "Групп: " + str(stats.get('groups_count', 0)) + chr(10) +
            "Нагрузка: " + str(stats.get('total_load_watt', 0)) + " Вт"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_del_"):
        panel_id = int(data.replace("panel_del_", ""))
        try:
            p = core_elec_panels.get_panel(panel_id)
            object_id = p.get('object_id') if p else None
            core_elec_panels.delete_panel(panel_id)
        except Exception as e:
            print("panel del: " + str(e), flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "✅ Щит удалён",
