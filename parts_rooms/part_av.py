            print("panels list: " + str(e), flush=True)
            panels = []
        from modules.objects import get_object as _get_obj
        _obj = _get_obj(object_id)
        _obj_name = _obj['name'] if _obj else ('Объект ' + str(object_id))
        lines = ["⚡ *Щиты объекта «" + str(_obj_name) + "»*", ""]
        if not panels:
            lines.append("_Пока щитов нет._")
        else:
            total = 0
            for p in panels:
                try:
                    load = core_elec_panels.calc_panel_load(p['id'])
                except Exception:
                    load = 0
                total += load
            lines.append("Щитов: " + str(len(panels)) + " / Общая нагрузка: " + str(total) + " Вт")
            lines.append("")
            for p in panels:
                ptype = core_elec_panels.get_panel_type_label(p.get('panel_type'))
                lines.append("⚡ *" + str(p.get('name') or '?') + "*")
                lines.append("   " + str(ptype))
        kb_rows = []
        for p in panels:
            pname = (p.get('name') or '?')[:35]
            kb_rows.append([InlineKeyboardButton(
                "⚡ " + pname,
                callback_data="panel_" + str(p['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить щит", callback_data="panel_add_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("panels list show: " + str(e), flush=True)
        return True

    # --- КАРТОЧКА ЩИТА ---
    if data.startswith("panel_groups_"):
        panel_id = int(data.replace("panel_groups_", ""))
        try:
            groups = core_elec_panels.get_groups_by_panel(panel_id)
            p = core_elec_panels.get_panel(panel_id)
        except Exception as e:
            print("panel groups: " + str(e), flush=True)
            groups = []
            p = None
        pname = (p.get('name') if p else '?')
        lines = ["📋 Группы щита «" + str(pname) + "»", ""]
        if not groups:
            lines.append("Пока групп нет.")
        else:
            total = 0
            for idx, g in enumerate(groups, start=1):
                total += int(g.get('load_watt') or 0)
                lines.append(str(idx) + ". " + core_elec.format_group(g))
            lines.append("")
            lines.append("📊 Групп: " + str(len(groups)) + " · Σ " + str(total) + " Вт")
        kb_rows = []
        for idx, g in enumerate(groups, start=1):
            gname = (g.get('name') or ('Группа #' + str(g['id'])))[:35]
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + gname,
                callback_data="group_" + str(g['id'])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_input_type_"):
        parts = data.replace("panel_input_type_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        btype = parts[1]
        kb_rows = []
        for r in [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100]:
            kb_rows.append([InlineKeyboardButton(
                str(r) + "А",
                callback_data="panel_input_set_" + str(panel_id) + "_" + btype + "_" + str(r)
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel_input_" + str(panel_id))])
        try:
            await query.edit_message_text(
                "Номинал (" + btype + "):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_input_set_"):
        parts = data.replace("panel_input_set_", "").split("_")
        panel_id = int(parts[0])
        btype = parts[1]
        rating = int(parts[2])
        poles = 3 if btype == 'auto3' else 1
        try:
            core_elec_panels.set_input_breaker(panel_id, breaker_type=btype.replace('auto3', 'auto'),
                                                rating=rating, curve='C', poles=poles)
        except Exception as e:
            print("panel input set: " + str(e), flush=True)
        try:
            s = core_elec_panels.format_selectivity(panel_id)
        except Exception:
            s = ""
        try:
            await query.edit_message_text(
                "Вводной установлен: " + btype + " " + str(rating) + "А" + chr(10) + chr(10) + s,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_input_"):
        panel_id = int(data.replace("panel_input_", ""))
        cur = core_elec_panels.get_input_breaker(panel_id) or {}
        cur_type = cur.get('type') or 'не задан'
        cur_rating = cur.get('rating') or '-'
        cur_fmt = core_elec_panels.format_input_breaker(panel_id)
        s = core_elec_panels.format_selectivity(panel_id)
        text = (
            "🔌 Вводной автомат" + chr(10) + chr(10) +
            "Сейчас: " + cur_fmt + chr(10) + chr(10) +
            s + chr(10) + chr(10) +
            "Выбери тип:"
        )
        kb_rows = [
            [InlineKeyboardButton("Автомат 1ф", callback_data="panel_input_type_" + str(panel_id) + "_auto")],
            [InlineKeyboardButton("Автомат 3ф", callback_data="panel_input_type_" + str(panel_id) + "_auto3")],
            [InlineKeyboardButton("УЗО", callback_data="panel_input_type_" + str(panel_id) + "_uzo")],
            [InlineKeyboardButton("Дифавтомат", callback_data="panel_input_type_" + str(panel_id) + "_dif")],
            [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_children_"):
        panel_id = int(data.replace("panel_children_", ""))
        try:
            children = core_elec_panels.get_child_panels(panel_id)
        except Exception as e:
            print("panel children: " + str(e), flush=True)
            children = []
        lines = ["⬇️ Дочерние щиты:", ""]
        if not children:
            lines.append("_Пока нет._")
        else:
            for c in children:
                ctype = core_elec_panels.get_panel_type_label(c.get('panel_type'))
                lines.append("└ " + str(c.get('name')) + " (" + str(ctype) + ")")
        kb_rows = []
        for c in children:
            kb_rows.append([InlineKeyboardButton(
                "⚡ " + str(c.get('name'))[:35],
                callback_data="panel_" + str(c['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить дочерний", callback_data="panel_child_add_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("panel children show: " + str(e), flush=True)
        return True

    if data.startswith("panel_child_type_"):
        parts = data.replace("panel_child_type_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        ptype = parts[1]
        context.user_data['child_parent_id'] = panel_id
        context.user_data['child_panel_type'] = ptype
        context.user_data['waiting_for'] = 'child_panel_name'
        type_labels = {
            'floor': 'Щит этажа', 'apartment': 'Щит квартиры',
            'outdoor': 'Уличный щит', 'subpanel': 'Подщиток',
        }
        tlabel = type_labels.get(ptype, ptype)
        try:
            await query.edit_message_text(
                "⬇️ Новый дочерний: " + tlabel + chr(10) + chr(10) + "Напиши название:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_child_add_"):
        panel_id = int(data.replace("panel_child_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("⚡ Щит этажа", callback_data="panel_child_type_" + str(panel_id) + "_floor")],
            [InlineKeyboardButton("🏢 Щит квартиры", callback_data="panel_child_type_" + str(panel_id) + "_apartment")],
            [InlineKeyboardButton("📦 Подщиток", callback_data="panel_child_type_" + str(panel_id) + "_subpanel")],
            [InlineKeyboardButton("🌳 Уличный щит", callback_data="panel_child_type_" + str(panel_id) + "_outdoor")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_children_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                "⬇️ Новый дочерний щит" + chr(10) + chr(10) + "Выбери тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_routes_auto_"):
        panel_id = int(data.replace("panel_routes_auto_", ""))
        print("panel_routes_auto handler: panel_id=" + str(panel_id), flush=True)
        try:
            res = core_elec_routes.auto_routes_for_panel(panel_id, route_type="shtroba") if core_elec_routes else None
        except Exception as e:
            print("panel auto routes: " + str(e), flush=True)
            res = None
        if not res:
            try:
                await query.edit_message_text("Ошибка автотрассировки")
            except Exception:
                pass
            return True
        text = (
            "🪄 Авто-трассировка щита" + chr(10) + chr(10) +
            "Групп обработано: " + str(res.get('groups', 0)) + chr(10) +
            "Создано трасс: " + str(res.get('created', 0)) + chr(10) +
            "Суммарно: " + str(res.get('total_m', 0)) + " м"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📏 Трассы щита", callback_data="panel_routes_" + str(panel_id))],
                    [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception as e:
            print("panel auto routes show: " + str(e), flush=True)
        return True

    if data.startswith("panel_routes_"):
        panel_id = int(data.replace("panel_routes_", ""))
        print("panel_routes handler: panel_id=" + str(panel_id), flush=True)
        try:
            text = core_elec_routes.format_routes_summary(panel_id=panel_id) if core_elec_routes else "Модуль не загружен"
        except Exception as e:
            print("panel routes show: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        try:
            routes = core_elec_routes.get_routes_by_panel(panel_id) if core_elec_routes else []
        except Exception:
            routes = []
        kb_rows = []
        for idx, r in enumerate(routes, start=1):
            label = core_elec_routes.format_route(r)[:45] if core_elec_routes else "?"
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + label,
                callback_data="route_" + str(r['id'])
            )])
        kb_rows.append([InlineKeyboardButton("🪄 Трассировать все", callback_data="panel_routes_auto_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_montage_"):
        panel_id = int(data.replace("panel_montage_", ""))
        try:
            if core_elec_routes:
                text = core_elec_routes.format_montage_cost_summary(panel_id=panel_id)
            else:
                text = "Модуль маршрутов не загружен"
        except Exception as e:
            print("panel montage: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_total_"):
        panel_id = int(data.replace("panel_total_", ""))
        print("panel_total handler: panel_id=" + str(panel_id), flush=True)
        try:
            text = _build_panel_total_text(panel_id)
        except Exception as e:
            print("panel total: " + str(e), flush=True)
