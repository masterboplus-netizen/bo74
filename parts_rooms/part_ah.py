        if areas.get('walls_net') is not None:
            text += f"📊 Площадь стен: {areas['walls_net']} м²\n"
        if areas.get('floor'):
            text += f"📊 Площадь пола: {areas['floor']} м²\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
            [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return

    next_step = step + 1
    state_next = _get_wall_state(context)
    state_next['step_num'] = next_step
    state_next['step_name'] = 'flags'
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"➡️ Стена {next_step}", callback_data=f"wall_round_start_{room_id}")],
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
    ])
    await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_wall_openings_from_update(update, context, room_id):
    """Экран проёмов через update.message."""
    state = _get_wall_state(context)
    step = state.get('step_num') or 1
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
    length_cm = state.get('length') or 0
    openings = get_openings_by_wall(room_id, pos)
    text = f"🧱 *Стена {step} — {pos}*\n📏 Длина: *{length_cm} см*\n\n"
    if openings:
        text += f"🚪 *Проёмы ({len(openings)}):*\n"
        for o in openings:
            text += f"  • {format_opening(o)}\n"
    else:
        text += "🚪 *Есть ли на этой стене проёмы?*"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪟 Окно", callback_data=f"wall_round_open_win_{room_id}"),
         InlineKeyboardButton("🚪 Дверь", callback_data=f"wall_round_open_door_{room_id}")],
        [InlineKeyboardButton("💨 Вентиляция", callback_data=f"wall_round_open_vent_{room_id}")],
        [InlineKeyboardButton("✅ Готово", callback_data=f"wall_round_openings_done_{room_id}")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_niche_depth_from_update(update, context, room_id):
    spec_step = spec.get_niche_step('depth')
    caption = spec_step.get('title', '🕳 *Ниша — ГЛУБИНА* (СМ):')
    if spec_step.get('hint'):
        caption += f"\n\n{spec_step['hint']}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_reply(update.message, caption, kb, spec_step.get('image', 'niche_depth.png'))


async def _show_niche_height_from_update(update, context, room_id):
    spec_step = spec.get_niche_step('height')
    caption = spec_step.get('title', '🕳 *Ниша — ВЫСОТА* (СМ):')
    if spec_step.get('example'):
        caption += f"\n\n_Например: {spec_step['example']}_"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_reply(update.message, caption, kb, spec_step.get('image', 'niche_height.png'))


async def _show_niche_plane_from_update(update, context, room_id):
    spec_step = spec.get_niche_step('plane')
    caption = spec_step.get('title', '🕳 *Ниша ровная или неровная по высоте?*')
    if spec_step.get('hint'):
        caption += f"\n\n{spec_step['hint']}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_niche_plane_rect_{room_id}")],
        [InlineKeyboardButton("📏 Неровная", callback_data=f"wall_niche_plane_irr_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_niche_top_width_from_update(update, context, room_id):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await update.message.reply_text("🕳 *Ширина СВЕРХУ* (СМ):", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_niche_top_depth_from_update(update, context, room_id):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await update.message.reply_text("🕳 *Глубина сверху* (СМ):", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_wall_length_from_update(update, context, room_id, step):
    """Экран длины стены через update.message (после 3 точек)."""
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = 'length'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_round_length'

    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
    spec_step = spec.get_wall_step('length', n=step, pos=pos)
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        if spec_step.get('hint'):
            caption += f"\n\n{spec_step['hint']}"
        if spec_step.get('prompt'):
            caption += f"\n\n{spec_step['prompt']}"
        image = spec_step.get('image')
    else:
        caption = (
            f"🧱 *Стена {step} — {pos}*\n\n"
            f"📏 *Длина стены* (СМ):\n\n"
            f"⚠️ *ВАЖНО:* дальномер в режиме «от ЗАДНЕЙ СТЕНКИ».\n\n"
            f"Напиши число и отправь."
        )
        image = f"wall_scheme_s{step}_length.png"

    await _send_png_or_reply(update.message, caption, None, image)


async def _handle_wall_round_opening_input(update, context, step):
    """Ввод размеров проёма при обходе."""
    room_id = context.user_data.get('wall_room_id')
    otype = context.user_data.get('wall_round_opening_type') or 'window'
    wall_pos = context.user_data.get('wall_round_opening_wall') or 'напротив'
    text_val = (update.message.text or '').strip().replace(',', '.')
    try: val = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Нужно число")
        return

    if step == 'wall_round_opening_width':
        context.user_data['wall_round_opening_width'] = val
        context.user_data['waiting_for'] = 'wall_round_opening_height'
        await update.message.reply_text("📏 *Высота проёма* (СМ):", parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'wall_round_opening_height':
        if otype == 'vent':
            final_width, final_height, final_sill = 100, 100, val
        else:
            final_width = context.user_data.get('wall_round_opening_width') or 0
            final_height, final_sill = val, None
        try: session_id = ensure_session(room_id)
        except Exception: session_id = None
        add_opening(
            room_id=room_id, opening_type=otype, wall_pos=wall_pos,
            width=final_width, height=final_height, sill_height=final_sill,
            session_id=session_id,
            created_by=update.effective_user.id if update.effective_user else None,
        )
        for k in ['wall_round_opening_type', 'wall_round_opening_width',
                  'wall_round_opening_height', 'wall_round_opening_wall']:
            context.user_data[k] = None
        state = _get_wall_state(context)
        step_num = state.get('step_num') or 1
        openings = get_openings_by_wall(room_id, wall_pos)
        length_cm = state.get('length') or 0
        text = f"✅ *Проём добавлен!*\n\n🧱 Стена {step_num}\n📏 Длина: {length_cm} см\n\n🚪 *Проёмы ({len(openings)}):*\n"
        for o in openings:
            text += f"  • {format_opening(o)}\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🪟 Окно", callback_data=f"wall_round_open_win_{room_id}"),
             InlineKeyboardButton("🚪 Дверь", callback_data=f"wall_round_open_door_{room_id}")],
            [InlineKeyboardButton("💨 Вентиляция", callback_data=f"wall_round_open_vent_{room_id}")],
            [InlineKeyboardButton("✅ Готово", callback_data=f"wall_round_openings_done_{room_id}")],
        ])
        context.user_data['waiting_for'] = None
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return


# ============================================================
# КОММУНИКАЦИИ — CALLBACK'И
# ============================================================

async def handle_comm_callback(query, context, data):
    """Обработчик callback'ов коммуникаций. Возвращает True если обработано."""
    if data.startswith("room_comms_"):
        room_id = int(data.replace("room_comms_", ""))
        await _show_comms_list(query, context, room_id)
        return True

    if data.startswith("comm_add_"):
        room_id = int(data.replace("comm_add_", ""))
        buttons = []
        for code, label, _ in COMM_TYPES:
            buttons.append([InlineKeyboardButton(label, callback_data=f"comm_type_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")])
        try:
            await query.edit_message_text(
                "🔧 *Новая коммуникация*\n\nВыбери тип:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_type_"):
        parts = data.replace("comm_type_", "").split("_", 1)
        room_id = int(parts[0])
        ctype = parts[1] if len(parts) > 1 else ''
        context.user_data['comm_room_id'] = room_id
        context.user_data['comm_type'] = ctype
        label = get_comm_type_label(ctype)
        buttons = [
            [InlineKeyboardButton("1. Напротив", callback_data=f"comm_wall_{room_id}_напротив")],
            [InlineKeyboardButton("2. Слева", callback_data=f"comm_wall_{room_id}_слева")],
            [InlineKeyboardButton("3. У входа", callback_data=f"comm_wall_{room_id}_у входа")],
            [InlineKeyboardButton("4. Справа", callback_data=f"comm_wall_{room_id}_справа")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
        ]
        try:
            await query.edit_message_text(
                f"🔧 *{label}*\n\nНа какой стене?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_wall_"):
        parts = data.replace("comm_wall_", "").split("_", 1)
        room_id = int(parts[0])
        wall = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['comm_wall'] = wall
        context.user_data['waiting_for'] = 'comm_offset_x'
        try:
            await query.edit_message_text(
                "📐 *Расстояние от угла* (СМ):\n\n_Например: 50_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_show_"):
        comm_id = int(data.replace("comm_show_", ""))
        await _show_comm_card(query, context, comm_id)
        return True

    if data.startswith("comm_del_"):
        comm_id = int(data.replace("comm_del_", ""))
        c = get_comm(comm_id)
        _room_id = c["room_id"] if c else None
        _name = (str(c.get("label") or c.get("comm_type") or "?") if c else "?")
        try:
            await query.edit_message_text(
                "🗑 *Удалить коммуникацию «" + _name + "»?*\n\nДействие нельзя отменить.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚠️ Да, удалить", callback_data="comm_delok_" + str(comm_id))],
                    [InlineKeyboardButton("❌ Отмена", callback_data="comm_" + str(comm_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_delok_"):
        comm_id = int(data.replace("comm_delok_", ""))
        c = get_comm(comm_id)
        _room_id = c["room_id"] if c else None
        try:
            delete_comm(comm_id)
        except Exception as _e:
            print("comm del: " + str(_e), flush=True)
        if _room_id:
            try:
                await query.edit_message_text(
                    "✅ Коммуникация удалена",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К коммуникациям", callback_data=f"room_comms_{_room_id}")],
                    ])
                )
            except Exception:
                pass
        return True


    if data.startswith("comm_edit_"):
        parts = data.replace("comm_edit_", "").split("_")
        comm_id = int(parts[0])
        field = "_".join(parts[1:])
        context.user_data['comm_edit_id'] = comm_id
        context.user_data['comm_edit_field'] = field
        context.user_data['waiting_for'] = 'comm_edit_value'
        prompts = {
            'offset_x': '📐 *Новое расстояние от угла* (СМ):',
            'offset_y': '📏 *Новая высота от пола* (СМ):',
            'diameter': '⭕ *Новый диаметр* (мм):',
            'voltage': '⚡ *Напряжение* (220 или 380):',
