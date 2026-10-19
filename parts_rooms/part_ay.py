            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить", callback_data="plumb_route_new_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))])
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_route_new_"):
        panel_id = int(data.replace("plumb_route_new_", ""))
        context.user_data['plumb_route_panel_id'] = panel_id
        # Шаг 1 — тип трубы
        kb_rows = [
            [InlineKeyboardButton("PPR 20 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr20")],
            [InlineKeyboardButton("PPR 25 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr25")],
            [InlineKeyboardButton("PPR 32 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr32")],
            [InlineKeyboardButton("PEX 16 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_pex16")],
            [InlineKeyboardButton("Медь 15 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_copper15")],
            [InlineKeyboardButton("Канализация 50 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_sewer50")],
            [InlineKeyboardButton("Канализация 110 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_sewer110")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_routes_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                "📏 Новая трасса" + chr(10) + chr(10) + "Тип трубы:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_route_pipe_"):
        parts = data.replace("plumb_route_pipe_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        pipe_type = parts[1]
        context.user_data['plumb_route_pipe'] = pipe_type
        context.user_data['waiting_for'] = 'plumb_route_length'
        try:
            await query.edit_message_text(
                "📏 Длина трассы (метры):" + chr(10) + chr(10) + "_Например: 8.5_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_routes_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_route_del_"):
        route_id = int(data.replace("plumb_route_del_", ""))
        try:
            import sqlite3
            from core.db import fetchone
            row = fetchone("SELECT panel_id FROM plumbing_routes WHERE id = ?", (route_id,))
            panel_id = row['panel_id'] if row else None
            core_plumbing.delete_route(route_id)
        except Exception as e:
            print("plumb route del: " + str(e), flush=True)
            panel_id = None
        if panel_id:
            try:
                await query.edit_message_text(
                    "Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К трассам", callback_data="plumb_routes_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_route_") and not data.startswith(("plumb_route_new_", "plumb_route_pipe_", "plumb_route_del_")):
        try:
            route_id = int(data.replace("plumb_route_", ""))
        except ValueError:
            return False
        try:
            from core.db import fetchone
            row = fetchone("SELECT * FROM plumbing_routes WHERE id = ?", (route_id,))
            r = dict(row) if row else None
        except Exception:
            r = None
        if not r:
            try:
                await query.edit_message_text("Трасса не найдена")
            except Exception:
                pass
            return True
        lines = ["📏 Трасса #" + str(route_id), ""]
        lines.append("Труба: " + core_plumbing.get_pipe_label(r.get('pipe_type')))
        lines.append("Длина: " + str(r.get('length_m') or 0) + " м")
        lines.append("Прокладка: " + str(r.get('route_type') or '—'))
        try:
            cost = core_plumbing.calc_route_cost(route_id)
            if cost:
                lines.append("")
                lines.append("Труба: " + str(cost.get('pipe_cost', 0)) + " ₽")
                lines.append("Расходники: " + str(cost.get('consumable_cost', 0)) + " ₽")
                lines.append("💰 Итого: " + str(cost.get('total', 0)) + " ₽")
        except Exception:
            pass
        kb_rows = [
            [InlineKeyboardButton("🗑 Удалить", callback_data="plumb_route_del_" + str(route_id))],
            [InlineKeyboardButton("⬅️ К трассам", callback_data="plumb_routes_" + str(r.get('panel_id')))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_points_"):
        panel_id = int(data.replace("plumb_points_", ""))
        try:
            text = core_plumbing.format_points_of_panel(panel_id)
        except Exception as e:
            print("plumb points: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Привязать точку", callback_data="plumb_point_add_" + str(panel_id))],
            [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
        ]))
        return True

    if data.startswith("plumb_point_add_"):
        panel_id = int(data.replace("plumb_point_add_", ""))
        p = core_plumbing.get_panel(panel_id)
        object_id = p.get("object_id") if p else None
        all_points = core_plumbing.get_available_plumb_points(object_id) if object_id else []
        used_ids = {pt["id"] for pt in core_plumbing.get_points_of_panel(panel_id)}
        free = [pt for pt in all_points if pt["id"] not in used_ids]
        if not free:
            text = "Свободных plumb-точек нет. Добавь точки в комнатах."
        else:
            text = "Выбери точку для привязки к коллектору:"
        kb_rows = []
        for pt in free[:15]:
            label = str(pt.get("room_name") or "?") + " · " + str(pt.get("comm_type") or "?")
            kb_rows.append([InlineKeyboardButton(label[:60], callback_data="plumb_point_set_" + str(panel_id) + "_" + str(pt["id"]))])
        kb_rows.append([InlineKeyboardButton("⬅️ К точкам", callback_data="plumb_points_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_point_set_"):
        rest = data.replace("plumb_point_set_", "")
        parts = rest.split("_", 1)
        panel_id = int(parts[0])
        point_id = int(parts[1])
        try:
            core_plumbing.assign_point_to_panel(point_id, panel_id)
        except Exception as e:
            print("plumb_point_set: " + str(e), flush=True)
        await handle_panels_callback(query, context, "plumb_points_" + str(panel_id))
        return True

    if data.startswith("plumb_point_unset_"):
        rest = data.replace("plumb_point_unset_", "")
        parts = rest.split("_", 1)
        panel_id = int(parts[0])
        point_id = int(parts[1])
        try:
            core_plumbing.unassign_point_from_panel(point_id, panel_id)
        except Exception as e:
            print("plumb_point_unset: " + str(e), flush=True)
        await handle_panels_callback(query, context, "plumb_points_" + str(panel_id))
        return True

    if data.startswith("plumb_water_"):
        object_id = int(data.replace("plumb_water_", ""))
        try:
            text = core_plumbing.format_water_summary(object_id)
        except Exception as e:
            print("plumb water: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Стояк", callback_data="plumb_add_type_" + str(object_id) + "_riser")],
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
        ]))
        return True

    if data.startswith("plumb_spec_"):
        panel_id = int(data.replace("plumb_spec_", ""))
        if export_plumbing_panel_spec is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_plumbing_panel_spec(panel_id)
            if not content:
                raise Exception("Пустая спецификация")
            target = os.path.join(tempfile.gettempdir(), "plumb_spec_" + str(panel_id) + ".txt")
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            p = core_plumbing.get_panel(panel_id)
            name = (p.get('name') if p else 'panel') or 'panel'
            with open(target, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=name + "_spec.txt",
                    caption="📄 Спецификация сантехники «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("plumb spec: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_csv_obj_"):
        object_id = int(data.replace("plumb_csv_obj_", ""))
        if export_plumbing_object_csv is None or save_estimate_csv is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_plumbing_object_csv(object_id)
            if not content:
                raise Exception("Пустая смета")
            target = os.path.join(tempfile.gettempdir(), "plumb_obj_" + str(object_id) + ".csv")
            path = save_estimate_csv(content, path=target, prefix="plumb_obj")
            from modules.objects import get_object
            o = get_object(object_id)
            name = o['name'] if o else ('obj_' + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_plumb.csv",
                    caption="📊 Смета сантехники «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("plumb csv obj: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_cost_obj_"):
        object_id = int(data.replace("plumb_cost_obj_", ""))
        try:
            text = core_plumbing.format_object_cost(object_id)
        except Exception as e:
            print("plumb cost obj: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
        ]))
        return True

    if data.startswith("plumb_cost_"):
        panel_id = int(data.replace("plumb_cost_", ""))
        try:
            text = core_plumbing.format_panel_cost(panel_id)
        except Exception as e:
            print("plumb cost: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_auto_"):
        panel_id = int(data.replace("panel_auto_", ""))
        try:
            result = core_elec_panels.autocomplete_panel(panel_id)
        except Exception as e:
            print("panel auto: " + str(e), flush=True)
            result = None
        if not result:
            try:
                await query.edit_message_text(
                    "Не удалось автокомплектовать",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
