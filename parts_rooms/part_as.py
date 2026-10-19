            await update.message.reply_text("Введи название")
            return
        object_id = context.user_data.get('panel_new_object_id')
        ptype = context.user_data.get('panel_new_type') or 'floor'
        if not object_id:
            await update.message.reply_text("Потерялись данные. Начни заново.")
            context.user_data['waiting_for'] = None
            return
        try:
            pid = core_elec_panels.create_panel(
                object_id=object_id, name=name, panel_type=ptype, mount_type='wall'
            )
        except Exception as e:
            print("panel create: " + str(e), flush=True)
            pid = None
        for k in ['panel_new_object_id', 'panel_new_type', 'waiting_for']:
            context.user_data[k] = None
        if pid:
            await update.message.reply_text(
                "Щит создан: " + name,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(pid))],
                    [InlineKeyboardButton("К щитам", callback_data="panels_list_" + str(object_id))],
                ])
            )
        else:
            await update.message.reply_text("Не удалось создать щит")
        return

    if step == 'group_load_watt':
        await _handle_group_load_input(update, context)
        return

    # --- ЭОМ: ввод мощности группы ---
    if step == 'group_load_watt':
        await _handle_group_load_input(update, context)
        return

    # --- Помещения: ввод названия ---
    if step == 'floor_new_name':
        object_id = context.user_data.get('floor_obj_id')
        name = (update.message.text or '').strip()
        if object_id and name:
            try:
                # Автосоздание Дом-корня
                root_id = core_floors.ensure_default_house(object_id)
                f_type = context.user_data.get("floor_new_type") or "floor"
                f_parent = context.user_data.get("floor_new_parent")
                if f_parent is None:
                    f_parent = root_id
                floor_id = core_floors.create_floor(object_id, floor_number=1, floor_name=name,
                                                     parent_id=f_parent, type=f_type)
                context.user_data['waiting_for'] = None
                context.user_data.pop('floor_new_type', None)
                context.user_data.pop('floor_new_parent', None)
                context.user_data['floor_obj_id'] = None
                # Показать карточку помещения
                await update.message.reply_text(
                    f"✅ Помещение «{name}» создано.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Открыть", callback_data=f"floor_{floor_id}")],
                        [InlineKeyboardButton("⬅️ К помещениям", callback_data=f"obj_floors_{object_id}")],
                    ])
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {e}")
        else:
            await update.message.reply_text("❌ Введи название")
        return

    # --- Переименование комнаты ---
    if step == 'room_rename':
        room_id = context.user_data.get('room_rename_id')
        new_name = (update.message.text or '').strip()
        if room_id and new_name:
            try:
                update_room(room_id, name=new_name)
            except Exception:
                db_commit("UPDATE rooms SET name = ? WHERE id = ?", (new_name, room_id))
            context.user_data['waiting_for'] = None
            context.user_data['room_rename_id'] = None
            await update.message.reply_text(
                f"✅ Имя комнаты изменено на «{new_name}»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        return

    # --- Высота ---
    if step == 'total_walls':
        try:
            n = int((update.message.text or '').strip())
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        if n < 3 or n > 12:
            await update.message.reply_text("❌ От 3 до 12")
            return
        core_spec.set_total_walls(n)
        context.user_data['total_walls_asked'] = False
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            "✅ Стён: " + str(n),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Начать обход", callback_data="wall_round_start_" + str(context.user_data.get('wall_room_id') or 0))],
            ])
        )
        return

    if step == 'room_height_point':
        room_id = context.user_data.get('height_room_id')
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната")
            return
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        h_step = context.user_data.get('height_step') or 1
        if h_step == 1:
            context.user_data['height_bottom'] = val
            context.user_data['height_step'] = 2
            await _show_height_step(update, context, room_id, step=2)
        elif h_step == 2:
            context.user_data['height_middle'] = val
            context.user_data['height_step'] = 3
            await _show_height_step(update, context, room_id, step=3)
        else:
            context.user_data['height_top'] = val
            h_bottom = context.user_data.get('height_bottom')
            h_middle = context.user_data.get('height_middle')
            h_top = val
            h_avg = (h_bottom + h_middle + h_top) / 3
            update_room(room_id, height=h_avg, height_bottom=h_bottom,
                        height_middle=h_middle, height_top=h_top)
            for k in ['waiting_for', 'height_room_id', 'height_step',
                      'height_bottom', 'height_middle', 'height_top']:
                context.user_data[k] = None
            await update.message.reply_text(
                f"✅ *Высота сохранена:*\n"
                f"Центр: {h_bottom} см\nЛевый: {h_middle} см\nПравый: {h_top} см\n"
                f"Среднее: {round(h_avg, 1)} см",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        return

    if step == 'room_height_same':
        room_id = context.user_data.get('height_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        update_room(room_id, height=val, height_bottom=val, height_middle=val, height_top=val)
        for k in ['waiting_for', 'height_room_id', 'height_step']:
            context.user_data[k] = None
        await update.message.reply_text(
            f"✅ *Высота: {val} см* (везде одинаковая)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 Начать обход", callback_data=f"wall_round_start_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    # --- Обход стен ---
    if step in ('wall_round_length', 'wall_round_angle_val',
                'wall_round_plane_bottom', 'wall_round_plane_middle', 'wall_round_plane_top',
                'wall_niche_width', 'wall_niche_depth', 'wall_niche_height',
                'wall_niche_top_width', 'wall_niche_top_depth',
                'wall_rounded_radius', 'wall_wavy_note', 'wall_hidden_note',
                'wall_round_opening_width', 'wall_round_opening_height'):
        await _handle_wall_round_input(update, context, step)
        return

    # --- Коммуникации ---
    if step in ('comm_offset_x', 'comm_offset_y', 'comm_diameter', 'comm_voltage',
                'comm_size_w', 'comm_size_h', 'comm_size_d',
                'comm_edit_value', 'comm_edit_size_part'):
        await _handle_comm_input(update, context, step)
        return

    # --- Проёмы (отдельные) ---
    if step in ('opening_width', 'opening_height', 'opening_edit_value'):
        await _handle_opening_input(update, context, step)
        return


async def _handle_comm_input(update, context, step):
    """Обработка ввода коммуникаций: offset_x → offset_y → финал."""
    from core.comms import get_comm_type_label

    room_id = context.user_data.get('comm_room_id')
    ctype = context.user_data.get('comm_type')
    wall = context.user_data.get('comm_wall')

    if not (room_id and ctype and wall):
        context.user_data['waiting_for'] = None
        await update.message.reply_text("❌ Потерялись данные. Начни заново.")
        return

    text_val = (update.message.text or '').strip().replace(',', '.')
    try:
        val = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Введи число")
        return

    if step == 'comm_offset_x':
        if val < 0 or val > 50000:
            await update.message.reply_text("❌ От 0 до 50000 см")
            return
        context.user_data['comm_offset_x'] = val
        context.user_data['waiting_for'] = 'comm_offset_y'
        await update.message.reply_text(
            "📏 *Высота от пола* (СМ):\n\n_Например: 30_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if step == 'comm_offset_y':
        if val < 0 or val > 5000:
            await update.message.reply_text("❌ От 0 до 5000 см")
            return
        context.user_data['comm_offset_y'] = val

        if ctype in ('water_cold', 'water_hot', 'sewer', 'drain', 'heating', 'gas', 'vent'):
            context.user_data['waiting_for'] = 'comm_diameter'
            await update.message.reply_text(
                "⭕ *Диаметр* (ММ):\n\n_Например: 20_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Пропустить", callback_data=f"comm_skip_diameter_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
                ])
            )
            return
        if ctype in ('elec_socket', 'elec_switch', 'elec_panel', 'elec_cable', 'net_internet', 'net_tv', 'net_phone', 'net_cctv'):
            context.user_data['waiting_for'] = 'comm_voltage'
            await update.message.reply_text(
                "⚡ *Напряжение* (В):\n\n_Например: 220_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Пропустить", callback_data=f"comm_skip_voltage_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
                ])
            )
            return
        await _comm_save_and_reply(update.message, context, room_id)
        return

    if step == 'comm_diameter':
        if val < 1 or val > 500:
            await update.message.reply_text("❌ От 1 до 500 мм")
            return
        context.user_data['comm_diameter'] = val
        await _comm_save_and_reply(update.message, context, room_id)
        return

    if step == 'comm_voltage':
        if val < 1 or val > 10000:
            await update.message.reply_text("❌ От 1 до 10000 В")
            return
        context.user_data['comm_voltage'] = val
        await _comm_save_and_reply(update.message, context, room_id)
        return

    context.user_data['waiting_for'] = None
    await update.message.reply_text("⚠️ Неизвестный шаг: " + str(step))


async def _comm_save_and_reply(message, context, room_id):
    """Сохраняет коммуникацию и отвечает."""
    from core.comms import add_comm, get_comm_type_label
    from core.geometry import wall_offset_to_world, calc_wall_coords
    from core.measures import get_walls_ordered

    ctype = context.user_data.get('comm_type')
    wall = context.user_data.get('comm_wall')
    offset_x = context.user_data.get('comm_offset_x')
    offset_y = context.user_data.get('comm_offset_y')
    diameter = context.user_data.get('comm_diameter')
    voltage = context.user_data.get('comm_voltage')

    world_x = world_y = world_z = None
    try:
        walls = get_walls_ordered(room_id)
        coords = calc_wall_coords(walls)
