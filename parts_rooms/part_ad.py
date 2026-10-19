        try:
            await query.get_bot().send_message(
                chat_id=chat_id, text=caption,
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
            print(f"🟢 _show_wall_angle: fallback send_message OK", flush=True)
        except Exception as e3:
            print(f"⚠️ _show_wall_angle send_message fallback: {e3}", flush=True)


# ============================================================
# НИШИ — ПОКАЗ ЭКРАНОВ
# ============================================================

async def _show_niche_count(query, context, room_id):
    """Сколько нишей на стене?"""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_count'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = None

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data=f"wall_niche_count_1_{room_id}")],
        [InlineKeyboardButton("2", callback_data=f"wall_niche_count_2_{room_id}")],
        [InlineKeyboardButton("3", callback_data=f"wall_niche_count_3_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    caption = "🕳 *Сколько нишей на этой стене?*"
    print(f"🟠 _show_niche_count вызван, room_id={room_id}", flush=True)

    # Правильный выбор: если текущее сообщение — фото, edit_caption; иначе edit_text
    msg = query.message
    is_photo = bool(getattr(msg, "photo", None))

    try:
        if is_photo:
            await query.edit_message_caption(
                caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        else:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        print(f"🟢 _show_niche_count OK (photo={is_photo})", flush=True)
    except Exception as e:
        err = str(e).lower()
        print(f"⚠️ _show_niche_count edit failed: {e}", flush=True)
        # Удаляем старое и шлём новое
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            await query.get_bot().send_message(
                chat_id=query.message.chat_id, text=caption,
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
            print(f"🟢 _show_niche_count fallback send OK", flush=True)
        except Exception as e2:
            print(f"⚠️ _show_niche_count fallback failed: {e2}", flush=True)


async def _show_niche_width(query, context, room_id):
    """Ширина ниши."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_width'
    _save_wall_draft(context, room_id)

    count = state.get('niche_count') or 1
    current = state.get('niche_current') or 1
    context.user_data['waiting_for'] = 'wall_niche_width'

    spec_step = spec.get_niche_step('width', i=current, count=count)
    if spec_step:
        caption = (
            f"🕳 *Ниша {current} из {count}*\n\n"
            f"{spec_step.get('subtitle', '📏 Ширина ниши (СМ):')}\n\n"
            f"_Например: {spec_step.get('example', '80')}_"
        )
        image = spec_step.get('image')
    else:
        caption = f"🕳 *Ниша {current} из {count}*\n\n📏 *Ширина ниши* (СМ):\n\n_Например: 80_"
        image = "niche_width.png"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_niche_depth(query, context, room_id):
    """Глубина ниши."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_depth'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_niche_depth'

    spec_step = spec.get_niche_step('depth')
    caption = spec_step.get('title', '🕳 *Ниша — ГЛУБИНА* (СМ):')
    hint = spec_step.get('hint')
    if hint:
        caption += f"\n\n{hint}"
    image = spec_step.get('image', 'niche_depth.png')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_niche_height(query, context, room_id):
    """Высота ниши."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_height'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_niche_height'

    spec_step = spec.get_niche_step('height')
    caption = spec_step.get('title', '🕳 *Ниша — ВЫСОТА* (СМ):')
    example = spec_step.get('example')
    if example:
        caption += f"\n\n_Например: {example}_"
    image = spec_step.get('image', 'niche_height.png')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_niche_plane(query, context, room_id):
    """Ниша ровная или неровная?"""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_plane'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = None

    spec_step = spec.get_niche_step('plane')
    caption = spec_step.get('title', '🕳 *Ниша ровная или неровная по высоте?*')
    hint = spec_step.get('hint')
    if hint:
        caption += f"\n\n{hint}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_niche_plane_rect_{room_id}")],
        [InlineKeyboardButton("📏 Неровная", callback_data=f"wall_niche_plane_irr_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, None)


async def _show_niche_top_width(query, context, room_id):
    """Ширина ниши СВЕРХУ (для неровной)."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_top_width'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_niche_top_width'

    spec_step = spec.get_niche_step('top_width')
    caption = spec_step.get('title', '🕳 *Ширина СВЕРХУ* (СМ):')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, None)


async def _show_niche_top_depth(query, context, room_id):
    """Глубина ниши СВЕРХУ (для неровной)."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_top_depth'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_niche_top_depth'

    spec_step = spec.get_niche_step('top_depth')
    caption = spec_step.get('title', '🕳 *Глубина сверху* (СМ):')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, None)


# ============================================================
# СОХРАНЕНИЕ СТЕНЫ
# ============================================================


async def _wall_save_and_next(query, context, room_id, step):
    """Сохраняет текущую стену, чистит черновик, идёт к следующей."""
    state = _get_wall_state(context)
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
    length = state.get('length') or 0
    angle = state.get('angle_value') or 90
    angle_method = state.get('angle_method') or '90'
    flags = state.get('flags') or {}

    note_parts = []
    if flags.get('rounded'): note_parts.append('Закругление')
    if flags.get('wavy'): note_parts.append('Разная по высоте')
    if flags.get('hidden'): note_parts.append('Скрытые коммуникации')
    note = '; '.join(note_parts) if note_parts else None

    try:
        session_id = ensure_session(room_id)
    except Exception:
        session_id = None

    start_x = start_y = end_x = end_y = None
    try:
        walls_existing = get_walls_ordered(room_id)
        walls_for_calc = list(walls_existing) + [{
            'wall_pos': pos, 'length': length, 'angle_value': angle,
        }]
        coords = calc_wall_coords(walls_for_calc)
        if coords:
            last = coords[-1]
            start_x = last.get('start_x'); start_y = last.get('start_y')
            end_x = last.get('end_x'); end_y = last.get('end_y')
    except Exception as e:
        print(f"⚠️ calc_wall_coords: {e}", flush=True)

    kwargs = {
        'label': f'Стена {pos}', 'wall_pos': pos, 'length': length,
        'unit': 'см', 'order_num': step,
        'angle_value': angle, 'angle_method': angle_method,
        'session_id': session_id,
    }
    if flags.get('rounded'): kwargs['has_rounded'] = 1
    if flags.get('wavy'): kwargs['is_wavy'] = 1
    if flags.get('hidden'):
        kwargs['has_hidden'] = 1
        kwargs['hidden_note'] = note
    if note: kwargs['note'] = note
    if start_x is not None:
        kwargs['start_x'] = start_x; kwargs['start_y'] = start_y
        kwargs['end_x'] = end_x; kwargs['end_y'] = end_y

    measure_id = add_measure(room_id, 'wall', **kwargs)

    niches = state.get('niches') or []
    if niches and measure_id:
        for n in niches:
            try:
                add_niche(
                    measure_id=measure_id, room_id=room_id,
                    width_bottom=n.get('width'),
                    width_top=n.get('width_top') or n.get('width'),
                    height=n.get('height'),
                    depth_bottom=n.get('depth'),
                    depth_top=n.get('depth_top') or n.get('depth'),
                    session_id=session_id,
                )
            except Exception as e:
                print(f"⚠️ add_niche: {e}", flush=True)

    _clear_wall_draft(room_id)
    next_step = step + 1 if step < core_spec.get_total_walls() else 1
    _reset_wall_state(context, keep_step_num=next_step)

    summary = f"✅ *Стена {step} ({pos}) сохранена!*\n\n📏 Длина: {length} см\n📐 Угол: {angle}°"
    if niches:
        summary += f"\n🕳 Нишей: {len(niches)}"

    if step >= core_spec.get_total_walls():
        complete_walls_round(room_id)
        await _wall_finish(query, context, room_id, summary)
        return

    state_next = _get_wall_state(context)
    state_next['step_num'] = next_step
    state_next['step_name'] = 'flags'
    _save_wall_draft(context, room_id)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"➡️ Стена {next_step}", callback_data=f"wall_round_start_{room_id}")],
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
    ])
    try:
        await query.edit_message_text(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _wall_finish(query, context, room_id, summary_prefix=''):
    """Финиш обхода стен."""
    areas = calculate_room_areas(room_id)
    text = summary_prefix + "\n\n🎉 *Все 4 стены замерены!*\n\n"
    if areas.get('walls_net') is not None:
        text += f"📊 Площадь стен: {areas['walls_net']} м²\n"
    if areas.get('floor'):
        text += f"📊 Площадь пола: {areas['floor']} м²\n"

    # Замыкание контура
    try:
        walls = get_walls_ordered(room_id)
        closure = check_closure(walls)
        if closure.get('closed'):
            text += "✅ Контур замкнут\n"
        else:
