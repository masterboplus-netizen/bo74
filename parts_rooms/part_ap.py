    if data.startswith("room_delok_"):
        room_id = int(data.replace("room_delok_", ""))
        room = get_room(room_id)
        if room:
            object_id = room['object_id']
            delete_room(room_id)
            await show_rooms_list(update, context, object_id)
        return

    # --- Прогресс / размеры / комм / мебель / задачи / фото ---
    if data.startswith("room_progress_"):
        room_id = int(data.replace("room_progress_", ""))
        await _show_room_progress(query, context, room_id)
        return

    if data.startswith("room_measures_"):
        room_id = int(data.replace("room_measures_", ""))
        await _show_room_measures(query, context, room_id)
        return

    if data.startswith("room_objects_"):
        room_id = int(data.replace("room_objects_", ""))
        await _show_room_objects(query, context, room_id)
        return

    if data.startswith("room_tasks_"):
        room_id = int(data.replace("room_tasks_", ""))
        try:
            await query.edit_message_text(
                "📋 Задачи комнаты — в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return

    if data.startswith("room_photos_"):
        room_id = int(data.replace("room_photos_", ""))
        try:
            await query.edit_message_text(
                "📸 Фото комнаты — в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return

    # --- План комнаты (PNG) ---    # --- Помещения ---
    # --- ЩИТЫ ЭОМ ---
    if data.startswith("panels_") or data.startswith("panel_"):
        handled = await handle_panels_callback(query, context, data)
        if handled:
            return

    # --- ЦЕНЫ / МАРКЕТПЛЕЙСЫ ---
    if data.startswith("prices_"):
        handled = await handle_panels_callback(query, context, data)
        if handled:
            return

    # --- САНТЕХНИКА ---
    if data.startswith("plumb_"):
        handled = await handle_panels_callback(query, context, data)
        if handled:
            return

    # --- КАБЕЛЬНЫЙ ЖУРНАЛ ---
    if data.startswith("cables_"):
        handled = await handle_cables_callback(query, context, data)
        if handled:
            return

    # --- КУХОННЫЕ ШАБЛОНЫ (кафе/рестораны) ---
    if data.startswith("floor_kitchen_"):
        handled = await handle_kitchen_callback(query, context, data)
        if handled:
            return

    if data.startswith("obj_floors_") or data.startswith("obj_floor_") or data.startswith("floor_"):
        handled = await handle_floors_callback(query, context, data)
        if handled:
            return

    # --- ЭОМ объекта ---
    if data.startswith("obj_elec_"):
        handled = await handle_obj_elec_callback(query, context, data)
        if handled:
            return

    if data.startswith(("obj_elec_pdf_", "plumb_pdf_obj_", "plumb_labor_obj_")):
        handled = await handle_panels_callback(query, context, data)
        if handled:
            return

    # --- Помещения ---

    if data.startswith("obj_floors_") or data.startswith("floor_"):

        handled = await handle_floors_callback(query, context, data)

        if handled:

            return


    # --- ЭОМ объекта ---

    if data.startswith("obj_elec_"):

        handled = await handle_obj_elec_callback(query, context, data)

        if handled:

            return


    if data.startswith("room_groups_") or data.startswith("group_"):
        handled = await handle_groups_callback(query, context, data)
        if handled:
            return

    if data.startswith("room_reports_") or data.startswith("room_report_"):
        handled = await handle_reports_callback(query, context, data)
        if handled:
            return

    if data.startswith("room_plan_"):
        handled = await handle_plan_callback(query, context, data)
        if handled:
            return

    # --- Экспорт ---
    if data.startswith("room_export_"):
        handled = await handle_export_callback(query, context, data)
        if handled:
            return

    # --- Коммуникации ---
    if data.startswith("comm_") or data.startswith("room_comms_"):
        handled = await handle_comm_callback(query, context, data)
        if handled:
            return

    # --- Проёмы (отдельные) ---
    if data.startswith("openings_") or data.startswith("opening_"):
        handled = await handle_openings_callback(query, context, data)
        if handled:
            return

    # --- Обход стен ---
    if (data.startswith("wall_round_") or data.startswith("wall_niche_")):
        handled = await handle_wall_round_callback(query, context, data)
        if handled:
            return

    # --- room_start / высота ---
    if data.startswith("room_start_"):
        room_id = int(data.replace("room_start_", ""))
        await _handle_room_start(query, context, room_id)
        return

    if data.startswith("room_height_"):
        handled = await _handle_height_callback(query, context, data)
        if handled:
            return

    # --- room_<id> — карточка комнаты ---
    _exclude = ("room_add_", "room_del_", "room_delok_", "room_tasks_",
                "room_measures_", "room_comms_", "room_objects_", "room_photos_",
                "room_type_", "room_method_", "room_height_", "room_start_",
                "room_progress_", "room_rename_", "rooms_list_obj_")
    if data.startswith("room_") and not data.startswith(_exclude):
        try:
            room_id = int(data.replace("room_", ""))
        except ValueError:
            return
        await show_room_card(update, context, room_id)
        return


# ============================================================
# ХЕЛПЕРЫ ЭКРАНОВ КОМНАТ
# ============================================================

async def _show_room_progress(query, context, room_id):
    room = get_room(room_id)
    if not room:
        return
    walls = get_walls_ordered(room_id)
    h_bottom = room.get('height_bottom')
    h_avg = room.get('height')
    height_ok = bool(h_bottom and room.get('height_middle') and room.get('height_top'))
    walls_ok = len(walls) >= core_spec.get_total_walls()
    try:
        r = fetchone("SELECT COUNT(*) as cnt FROM openings WHERE room_id = ?", (room_id,))
        openings_count = r['cnt'] if r else 0
    except Exception:
        openings_count = 0
    try:
        r = fetchone("SELECT COUNT(*) as cnt FROM room_comms WHERE room_id = ?", (room_id,))
        comms_count = r['cnt'] if r else 0
    except Exception:
        comms_count = 0
    text = f"👁 *Что замерено в комнате «{room['name']}»*\n\n"
    if height_ok:
        text += f"📏 Высота: ✅ {int(h_avg) if h_avg == int(h_avg) else round(h_avg, 1)} см\n"
    elif h_bottom:
        text += f"📏 Высота: ⚠️ частично\n"
    else:
        text += f"📏 Высота: ❌ не замерена\n"
    if walls_ok:
        text += f"🧱 Стены: ✅ {len(walls)} шт.\n"
    elif walls:
        text += f"🧱 Стены: ⚠️ {len(walls)} из 4\n"
    else:
        text += f"🧱 Стены: ❌ не замерены\n"
    text += f"🚪 Проёмы: {'✅ ' + str(openings_count) + ' шт.' if openings_count > 0 else '❌ не замерены'}\n"
    text += f"🔧 Коммуникации: {'✅ ' + str(comms_count) + ' шт.' if comms_count > 0 else '❌ не замерены'}\n"
    text += "\n*Что дальше?*"
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Продолжить замер", callback_data=f"room_start_{room_id}")],
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
    except Exception:
        pass


async def _show_room_measures(query, context, room_id):
    measures = get_measures(room_id)
    if not measures:
        try:
            await query.edit_message_text(
                "📐 Размеров пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return
    lines = [f"📐 *Размеры комнаты* ({len(measures)}):\n"]
    for m in measures:
        lines.append(format_measure(m, show_area=True))
    areas = calculate_room_areas(room_id)
    lines.append("")
    if areas.get('walls_net') is not None:
        lines.append(f"Стены: {areas['walls_net']} м²")
    lines.append(f"Пол: {areas['floor']} м²")
    try:
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
    except Exception:
        pass


async def _show_room_objects(query, context, room_id):
    objects = get_room_objects(room_id)
    if not objects:
        try:
            await query.edit_message_text(
                "🪑 Мебели/техники пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return
    lines = [f"🪑 *Мебель/техника* ({len(objects)}):\n"]
    for o in objects:
        lines.append(format_room_object(o))
    try:
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
    except Exception:
        pass


# ============================================================
# ROOM_START И ВЫСОТА
# ============================================================

async def _handle_room_start(query, context, room_id):
