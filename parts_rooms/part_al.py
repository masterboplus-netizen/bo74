        except Exception as e:
            print("auto routes: " + str(e), flush=True)
            res = None
        if not res:
            try:
                await query.edit_message_text("Ошибка автотрассировки")
            except Exception:
                pass
            return True
        text = (
            "🪄 Авто-трассировка выполнена" + chr(10) + chr(10) +
            "Создано трасс: " + str(res.get('created', 0)) + chr(10) +
            "Пропущено: " + str(res.get('skipped', 0)) + chr(10) +
            "Суммарно: " + str(res.get('total_m', 0)) + " м"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📏 Трассы", callback_data="group_routes_" + str(group_id))],
                    [InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("group_routes_clear_"):
        group_id = int(data.replace("group_routes_clear_", ""))
        try:
            if core_elec_routes:
                core_elec_routes.delete_routes_by_group(group_id, only_auto=True)
        except Exception as e:
            print("clear routes: " + str(e), flush=True)
        try:
            await query.edit_message_text(
                "🗑 Авто-трассы удалены",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("group_routes_"):
        group_id = int(data.replace("group_routes_", ""))
        print("group_routes_ handler: group_id=" + str(group_id), flush=True)
        try:
            text = core_elec_routes.format_routes_summary(group_id=group_id) if core_elec_routes else "Модуль не загружен"
            routes = core_elec_routes.get_routes_by_group(group_id) if core_elec_routes else []
        except Exception as e:
            print("routes show: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
            routes = []
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        kb_rows = []
        for idx, r in enumerate(routes, start=1):
            label = core_elec_routes.format_route(r)[:45] if core_elec_routes else "?"
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + label,
                callback_data="route_" + str(r['id'])
            )])
        kb_rows.append([InlineKeyboardButton("🪄 Авто-трассировка", callback_data="group_routes_auto_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("🗑 Очистить", callback_data="group_routes_clear_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    # --- КАРТОЧКА ТРАССЫ ---
    if data.startswith("route_edit_len_"):
        route_id = int(data.replace("route_edit_len_", ""))
        context.user_data['route_edit_id'] = route_id
        context.user_data['waiting_for'] = 'route_length'
        try:
            await query.edit_message_text(
                "📏 Новая длина (метры):" + chr(10) + chr(10) + "_Например: 12.5_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="route_" + str(route_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("route_edit_type_"):
        route_id = int(data.replace("route_edit_type_", ""))
        context.user_data['route_edit_id'] = route_id
        try:
            await query.edit_message_text(
                "🛠 Выбери тип прокладки:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Штроба", callback_data="route_set_type_" + str(route_id) + "_shtroba")],
                    [InlineKeyboardButton("Потолок", callback_data="route_set_type_" + str(route_id) + "_potolok")],
                    [InlineKeyboardButton("Стяжка", callback_data="route_set_type_" + str(route_id) + "_styazhka")],
                    [InlineKeyboardButton("Лоток", callback_data="route_set_type_" + str(route_id) + "_lotok")],
                    [InlineKeyboardButton("Открыто", callback_data="route_set_type_" + str(route_id) + "_otkryto")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="route_" + str(route_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("route_set_type_"):
        parts = data.replace("route_set_type_", "").rsplit("_", 1)
        route_id = int(parts[0])
        rtype = parts[1]
        try:
            core_elec_routes.update_route(route_id, route_type=rtype, is_manual=1)
        except Exception as e:
            print("route set type: " + str(e), flush=True)
        await _show_route_card(query, route_id)
        return True

    if data.startswith("route_del_"):
        route_id = int(data.replace("route_del_", ""))
        try:
            r = core_elec_routes.get_route(route_id)
            group_id = r.get('group_id') if r else None
            panel_id = r.get('panel_id') if r else None
            core_elec_routes.delete_route(route_id)
        except Exception as e:
            print("route del: " + str(e), flush=True)
            group_id = None
            panel_id = None
        kb = []
        if group_id:
            kb.append([InlineKeyboardButton("⬅️ К трассам группы", callback_data="group_routes_" + str(group_id))])
        elif panel_id:
            kb.append([InlineKeyboardButton("⬅️ К трассам щита", callback_data="panel_routes_" + str(panel_id))])
        try:
            await query.edit_message_text("✅ Трасса удалена", reply_markup=InlineKeyboardMarkup(kb) if kb else None)
        except Exception:
            pass
        return True

    if data.startswith("route_") and not data.startswith(("route_edit_", "route_set_", "route_del_")):
        try:
            route_id = int(data.replace("route_", ""))
        except ValueError:
            return False
        await _show_route_card(query, route_id)
        return True

    # --- КАРТОЧКА ГРУППЫ ---
    if data.startswith("group_panel_pick_"):
        group_id = int(data.replace("group_panel_pick_", ""))
        g = core_elec.get_group(group_id) if core_elec else None
        if not g:
            try:
                await query.edit_message_text("Группа не найдена")
            except Exception:
                pass
            return True
        object_id = g.get('object_id')
        panels = core_elec_panels.get_panels(object_id) if core_elec_panels else []
        if not panels:
            try:
                await query.edit_message_text(
                    "У объекта нет щитов. Создай щит сначала.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("K группе", callback_data="group_" + str(group_id))],
                    ])
                )
            except Exception:
                pass
            return True
        cur_panel_id = g.get('panel_id')
        lines = ["Привязать группу к щиту:", ""]
        kb_rows = []
        for idx, p2 in enumerate(panels, start=1):
            ptype = core_elec_panels.get_panel_type_label(p2.get('panel_type'))
            mark = " - текущий" if p2['id'] == cur_panel_id else ""
            pname = (p2.get('name') or '?')[:30]
            lines.append(str(idx) + ". " + pname + " (" + str(ptype) + ")" + mark)
            label = str(idx) + ". " + pname + mark
            kb_rows.append([InlineKeyboardButton(
                label[:60],
                callback_data="group_panel_set_" + str(group_id) + "_" + str(p2['id'])
            )])
        kb_rows.append([InlineKeyboardButton("K группе", callback_data="group_" + str(group_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("group_panel_set_"):
        parts = data.replace("group_panel_set_", "").rsplit("_", 1)
        group_id = int(parts[0])
        panel_id = int(parts[1])
        try:
            if core_elec_panels:
                core_elec_panels.assign_group_to_panel(group_id, panel_id)
                core_elec_panels.recalc_panel_safe(panel_id)
        except Exception as e:
            print("group_panel_set: " + str(e), flush=True)
        await handle_panels_callback(query, context, "panel_" + str(panel_id))
        return True

    if data.startswith("group_panel_unset_"):
        group_id = int(data.replace("group_panel_unset_", ""))
        _old_panel_id = None
        try:
            _g_before = core_elec.get_group(group_id) if core_elec else None
            _old_panel_id = _g_before.get("panel_id") if _g_before else None
        except Exception:
            _old_panel_id = None
        try:
            if core_elec_panels:
                core_elec_panels.unassign_group_from_panel(group_id)
                if _old_panel_id:
                    core_elec_panels.recalc_panel_safe(_old_panel_id)
        except Exception as e:
            print("group_panel_unset: " + str(e), flush=True)
        _g = core_elec.get_group(group_id) if core_elec else None
        _obj_id = _g.get("object_id") if _g else 0
        await handle_panels_callback(query, context, "panels_list_" + str(_obj_id))
        return True

    if data.startswith("group_") and not data.startswith(("group_new_", "group_purpose_", "group_phase_", "group_routes_")):
        try:
            group_id = int(data.replace("group_", ""))
        except ValueError:
            return False
        try:
            g = core_elec.get_group(group_id) if core_elec else None
        except Exception:
            g = None
        if not g:
            try:
                await query.edit_message_text("Группа не найдена")
            except Exception:
                pass
            return True
        _phase = g.get('phase') or 1
        _load = int(g.get('load_watt') or 0)
        _breaker = g.get('breaker_type') or '—'
        _cable = g.get('cable_type') or '—'
        _purpose = g.get('purpose') or '—'
        _panel_id = g.get('panel_id')
        text = (
            "⚡ *" + str(g.get('name') or '?') + "*" + chr(10) + chr(10) +
            "Назначение: " + str(_purpose) + chr(10) +
            "Фаза: " + str(_phase) + "ф" + chr(10) +
            "Мощность: " + str(_load) + " Вт" + chr(10) +
            "Автомат: " + str(_breaker) + chr(10) +
            "Кабель: " + str(_cable)
        )
        if _panel_id:
            text += chr(10) + "Щит: " + (core_elec_panels.get_panel(_panel_id).get("name") if (core_elec_panels and core_elec_panels.get_panel(_panel_id)) else ("#" + str(_panel_id)))
        kb_rows = [
            [InlineKeyboardButton("📏 Трассы", callback_data="group_routes_" + str(group_id))],
        ]
        if _panel_id:
            kb_rows.append([InlineKeyboardButton("⚡ К щиту", callback_data="panel_" + str(_panel_id))])
            kb_rows.append([InlineKeyboardButton("⚡ Сменить щит", callback_data="group_panel_pick_" + str(group_id))])
            kb_rows.append([InlineKeyboardButton("⚡ Отвязать", callback_data="group_panel_unset_" + str(group_id))])
        else:
            kb_rows.append([InlineKeyboardButton("⚡ Привязать к щиту", callback_data="group_panel_pick_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К группам", callback_data="room_groups_" + str(g.get('room_id') or 0))])
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("group card: " + str(e), flush=True)
        return True

    # --- СПИСОК ГРУПП КОМНАТЫ ---
    if data.startswith("room_groups_"):
        room_id = int(data.replace("room_groups_", ""))
        room = get_room(room_id)
        name = room.get('name', '?') if room else '?'

        # Новая архитектура: группы через точки (room_comms.group_id)
        # Fallback на legacy (room_id) — если точек с группой ещё нет
        groups = core_elec.get_groups_by_room(room_id)
        if not groups:
            groups = core_elec.get_groups(room_id)
        lines = ["📋 Группы ЭОМ «" + str(name) + "»", ""]
        if not groups:
            lines.append("_Пока групп нет._\n")
        else:
            total_w = 0
            for g in groups:
                lines.append(core_elec.format_group(g))
                total_w += g.get('load_watt') or 0
            lines.append(f"\n📊 *Групп: {len(groups)} · Σ {int(total_w)} Вт*")

        kb_rows = []
        for g in groups:
            gname = (g.get('name') or ('Группа #' + str(g['id'])))[:40]
            kb_rows.append([InlineKeyboardButton(
