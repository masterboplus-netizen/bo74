        }
        prompt = prompts.get(field, '✏️ Новое значение:')
        try:
            await query.edit_message_text(
                f"{prompt}\n\n_Напиши и отправь._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"comm_show_{comm_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_skip_"):
        # Пропуск шагов — сохраняем как есть
        parts = data.replace("comm_skip_", "").split("_")
        # comm_skip_diameter_<room> / comm_skip_voltage_<room>
        try:
            room_id = int(parts[-1])
        except ValueError:
            return True
        skip_type = parts[0] if parts else None
        if skip_type == 'diameter':
            context.user_data['comm_diameter'] = None
        elif skip_type == 'voltage':
            context.user_data['comm_voltage'] = None
        await _comm_save_and_reply(query.message, context, room_id)
        return True
    # === ПРИВЯЗКА К ГРУППЕ ЭОМ ===
    if data.startswith("comm_group_unset_"):
        comm_id = int(data.replace("comm_group_unset_", ""))
        try:
            if core_elec:
                core_elec.unassign_point_from_group(comm_id)
        except Exception as e:
            print(f"⚠️ unassign_point_from_group: {e}", flush=True)
        await _show_comm_card(query, context, comm_id)
        return True

    if data.startswith("comm_group_set_"):
        parts = data.replace("comm_group_set_", "").rsplit("_", 1)
        comm_id = int(parts[0])
        group_id = int(parts[1])
        try:
            if core_elec:
                core_elec.assign_comm_to_group(comm_id, group_id)
        except Exception as e:
            print(f"⚠️ assign_comm_to_group: {e}", flush=True)
        await _show_comm_card(query, context, comm_id)
        return True

    if data.startswith("comm_group_"):
        comm_id = int(data.replace("comm_group_", ""))
        c = get_comm(comm_id)
        if not c:
            try:
                await query.edit_message_text("❌ Коммуникация не найдена")
            except Exception:
                pass
            return True
        _room_obj = get_room(c.get('room_id')) if c.get('room_id') else None
        _floor_id = _room_obj.get('floor_id') if _room_obj else None
        if not _floor_id:
            try:
                await query.edit_message_text(
                    "⚠️ Комната не привязана к помещению.\n\nСначала привяжи комнату к этажу через «🏠 Помещения».",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")],
                    ])
                )
            except Exception:
                pass
            return True
        try:
            groups = core_elec.get_groups_by_floor(_floor_id) if core_elec else []
        except Exception as e:
            print(f"⚠️ get_groups_by_floor: {e}", flush=True)
            groups = []
        if not groups:
            try:
                await query.edit_message_text(
                    "⚠️ На этом этаже пока нет групп ЭОМ.\n\nСоздай группу через «⚡ Группы этажа».",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")],
                    ])
                )
            except Exception:
                pass
            return True
        label = get_comm_type_label(c.get('comm_type'))
        buttons = []
        for g in groups:
            g_name = (g.get('name') or f"#{g['id']}")[:30]
            w = int(g.get('load_watt') or 0)
            buttons.append([InlineKeyboardButton(
                f"⚡ {g_name} · {w}Вт",
                callback_data=f"comm_group_set_{comm_id}_{g['id']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")])
        try:
            await query.edit_message_text(
                f"📋 *Привязка к группе этажа*\n\n🔧 {label}\n🧱 Стена: {c.get('wall') or '?'}\n\nВыбери группу:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

        await _comm_save_from_context(query, context, room_id)
        return True

    return False


async def _show_comms_list(query, context, room_id):
    """Список коммуникаций комнаты."""
    comms = get_comms(room_id)
    room = get_room(room_id)
    room_name = room['name'] if room else '?'
    text = f"🔧 *Коммуникации в «{room_name}»*\n\n"
    if not comms:
        text += "_Пока ничего не добавлено._\n\nДобавь воду, канализацию, электрику, газ, вентиляцию."
    else:
        text += f"Найдено: {len(comms)}\n\n"
        for i, c in enumerate(comms, 1):
            text += f"{i}. {format_comm(c)}\n"
    buttons = []
    for c in comms:
        label = get_comm_type_label(c.get('comm_type'))
        wall = c.get('wall') or '?'
        buttons.append([InlineKeyboardButton(f"{label} ({wall})", callback_data=f"comm_show_{c['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить", callback_data=f"comm_add_{room_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass


async def _show_comm_card(query, context, comm_id):
    """Карточка коммуникации."""
    c = get_comm(comm_id)
    if not c:
        try:
            await query.edit_message_text("❌ Не найдено")
        except Exception:
            pass
        return
    label = get_comm_type_label(c.get('comm_type'))
    text = f"🔧 *Коммуникация #{comm_id}*\n\n{label}\n"
    text += f"🧱 Стена: {c.get('wall') or '?'}\n"
    if c.get('offset_x') is not None:
        text += f"📐 От угла: {c['offset_x']} см\n"
    if c.get('offset_y') is not None:
        text += f"📏 От пола: {c['offset_y']} см\n"
    if c.get('diameter'):
        text += f"⭕ Диаметр: {c['diameter']} мм\n"
    if c.get('voltage'):
        text += f"⚡ Напряжение: {c['voltage']} В\n"
    if c.get('size'):
        text += f"📦 Размер: {c['size']} см\n"
    buttons = [
        [InlineKeyboardButton("✏️ От угла", callback_data=f"comm_edit_{comm_id}_offset_x"),
         InlineKeyboardButton("✏️ От пола", callback_data=f"comm_edit_{comm_id}_offset_y")],
    ]
    ctype = c.get('comm_type')
    if ctype == 'elec_panel':
        buttons.append([InlineKeyboardButton("✏️ Размер щита", callback_data=f"comm_edit_{comm_id}_size")])
    elif ctype in ('water_cold', 'water_hot', 'sewer', 'heating', 'gas', 'drain', 'vent'):
        buttons.append([InlineKeyboardButton("✏️ Диаметр", callback_data=f"comm_edit_{comm_id}_diameter")])
    # === ПРИВЯЗКА К ГРУППЕ ЭОМ ===
    _room_obj = get_room(c.get('room_id')) if c.get('room_id') else None
    _floor_id = _room_obj.get('floor_id') if _room_obj else None
    if _floor_id and ctype in ('elec_socket', 'elec_switch', 'elec_panel', 'elec_cable'):
        _cur_gid = c.get('group_id')
        if _cur_gid:
            try:
                _g = core_elec.get_group(_cur_gid) if core_elec else None
                _g_name = (_g.get('name') if _g else f"#{_cur_gid}")
            except Exception:
                _g_name = f"#{_cur_gid}"
            buttons.append([InlineKeyboardButton(f"📋 Группа: {_g_name[:25]}", callback_data=f"comm_group_{comm_id}")])
            buttons.append([InlineKeyboardButton("❌ Отвязать от группы", callback_data=f"comm_group_unset_{comm_id}")])
        else:
            buttons.append([InlineKeyboardButton("📋 → Привязать к группе", callback_data=f"comm_group_{comm_id}")])
    buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data=f"comm_del_{comm_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К коммуникациям", callback_data=f"room_comms_{c['room_id']}")])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass


async def _comm_save_from_context(query, context, room_id):
    """Сохраняет коммуникацию из context.user_data."""
    ctype = context.user_data.get('comm_type')
    wall = context.user_data.get('comm_wall')
    offset_x = context.user_data.get('comm_offset_x')
    offset_y = context.user_data.get('comm_offset_y')
    if not all([room_id, ctype, wall]):
        try:
            await query.edit_message_text("❌ Потерялись данные")
        except Exception:
            pass
        return
    try:
        add_comm(room_id=room_id, comm_type=ctype, wall=wall,
                 offset_x=offset_x, offset_y=offset_y)
    except Exception as e:
        print(f"⚠️ add_comm: {e}", flush=True)
        return
    for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
              'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_size',
              'comm_size_w', 'comm_size_h', 'comm_size_d', 'waiting_for']:
        context.user_data[k] = None
    label = get_comm_type_label(ctype)
    text = f"✅ *{label}* добавлена!\n\n🧱 {wall}\n"
    if offset_x is not None:
        text += f"📐 От угла: {offset_x} см\n"
    if offset_y is not None:
        text += f"📏 От пола: {offset_y} см\n"
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
                [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
            ])
        )
    except Exception:
        pass


# ============================================================
# ПРОЁМЫ (отдельные) — CALLBACK'И
# ============================================================

async def handle_openings_callback(query, context, data):
    """Обработчик callback'ов проёмов."""
    if data.startswith("openings_list_"):
        room_id = int(data.replace("openings_list_", ""))
        openings = get_openings(room_id)
        room = get_room(room_id)
        room_name = room['name'] if room else '?'
        text = f"🚪 *Проёмы в комнате «{room_name}»*\n\n"
        if not openings:
            text += "_Пока проёмов нет._"
        else:
            for i, o in enumerate(openings, 1):
                text += f"{i}. {format_opening(o)}\n"
        buttons = []
        for o in openings:
            label = OPENING_TYPES.get(o.get('opening_type'), '?')
            wall = o.get('wall_pos') or '?'
            buttons.append([InlineKeyboardButton(f"{label} ({wall})", callback_data=f"opening_show_{o['id']}")])
        buttons.append([InlineKeyboardButton("➕ Добавить проём", callback_data=f"opening_add_{room_id}")])
        buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass
        return True

    if data.startswith("opening_add_"):
        room_id = int(data.replace("opening_add_", ""))
        buttons = []
        for code, label in OPENING_TYPES.items():
            buttons.append([InlineKeyboardButton(label, callback_data=f"opening_type_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")])
        try:
            await query.edit_message_text(
                "🚪 *Новый проём*\n\nВыбери тип:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_type_"):
        parts = data.replace("opening_type_", "").split("_", 1)
        room_id = int(parts[0])
        otype = parts[1] if len(parts) > 1 else 'window'
        context.user_data['opening_room_id'] = room_id
        context.user_data['opening_type'] = otype
        label = OPENING_TYPES.get(otype, otype)
        buttons = [
            [InlineKeyboardButton("1. Напротив", callback_data=f"opening_wall_{room_id}_напротив")],
            [InlineKeyboardButton("2. Слева", callback_data=f"opening_wall_{room_id}_слева")],
            [InlineKeyboardButton("3. У входа", callback_data=f"opening_wall_{room_id}_у входа")],
            [InlineKeyboardButton("4. Справа", callback_data=f"opening_wall_{room_id}_справа")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
        ]
        try:
            await query.edit_message_text(
                f"🚪 *{label}*\n\nНа какой стене?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
