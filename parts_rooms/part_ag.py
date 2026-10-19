        state['plane_middle'] = val
        context.user_data['waiting_for'] = 'wall_round_plane_top'
        step_num = state.get('step_num') or 1
        pos = core_spec.get_wall_name(step_num, core_spec.get_total_walls())
        bottom = state.get('plane_bottom') or 0
        caption = (
            f"🧱 *Стена {step_num} — {pos}*\n\n"
            f"📏 *Замер в 3 точках*\n"
            f"✅ Точка 1 (низ): *{bottom} см*\n"
            f"✅ Точка 2 (середина): *{val} см*\n\n"
            f"📍 *Точка 3 — ВЕРХ стены*\n"
            f"Приложи дальномер вверху стены (под потолком).\n\n"
            f"Введи результат в СМ:"
        )
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'wall_round_plane_top':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        state['plane_top'] = val
        state['plane'] = 'wavy'
        state['step_name'] = 'length'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_length'
        step_num = state.get('step_num') or 1
        pos = core_spec.get_wall_name(step_num, core_spec.get_total_walls())
        bottom = state.get('plane_bottom') or 0
        middle = state.get('plane_middle') or 0
        # Отклонение — насколько «кривая» стена
        avg = (bottom + middle + val) / 3
        deviation = max(bottom, middle, val) - min(bottom, middle, val)
        caption = (
            f"✅ *Замер стены завершён!*\n\n"
            f"🧱 *Стена {step_num} — {pos}*\n"
            f"• Низ: *{bottom} см*\n"
            f"• Середина: *{middle} см*\n"
            f"• Верх: *{val} см*\n\n"
            f"📊 Отклонение: *{round(deviation, 1)} см*\n"
            f"📏 Средняя высота: *{round(avg, 1)} см*\n\n"
            f"Дальше — *длина стены*."
        )
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
        # Непрерывный переход: сразу показываем экран длины
        await _show_wall_length_from_update(update, context, room_id, step_num)
        return

    if step == 'wall_round_angle_val':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        method = state.get('angle_method') or '60'
        if method == '60':
            c = (60*60 + 80*80 - val*val) / (2*60*80)
            c = max(-1, min(1, c))
            angle_deg = round(math.degrees(math.acos(c)), 1)
        elif method == '100':
            c = (100*100 + 100*100 - val*val) / (2*100*100)
            c = max(-1, min(1, c))
            angle_deg = round(math.degrees(math.acos(c)), 1)
        else:
            angle_deg = val
        state['angle_value'] = angle_deg
        state['step_name'] = 'angle_done'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = None
        await _after_angle_from_update(update, context, room_id)
        return

    if step == 'wall_niche_width':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['width'] = round(val, 2)
        state['niche_temp'] = temp
        state['step_name'] = 'niche_depth'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_niche_depth'
        await _show_niche_depth_from_update(update, context, room_id)
        return

    if step == 'wall_niche_depth':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['depth'] = round(val, 2)
        state['niche_temp'] = temp
        state['step_name'] = 'niche_height'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_niche_height'
        await _show_niche_height_from_update(update, context, room_id)
        return

    if step == 'wall_niche_height':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['height'] = round(val, 2)
        state['niche_temp'] = temp
        state['step_name'] = 'niche_plane'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = None
        await _show_niche_plane_from_update(update, context, room_id)
        return

    if step == 'wall_niche_top_width':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['width_top'] = round(val, 2)
        state['niche_temp'] = temp
        state['step_name'] = 'niche_top_depth'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_niche_top_depth'
        await _show_niche_top_depth_from_update(update, context, room_id)
        return

    if step == 'wall_niche_top_depth':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['depth_top'] = round(val, 2)
        niches = state.get('niches') or []
        niches.append(temp)
        state['niches'] = niches
        state['niche_temp'] = {}
        total = state.get('niche_count') or 1
        current = state.get('niche_current') or 1
        if current < total:
            state['niche_current'] = current + 1
            state['step_name'] = 'niche_width'
            _save_wall_draft(context, room_id)
            context.user_data['waiting_for'] = 'wall_niche_width'
            await update.message.reply_text(
                f"✅ Ниша {current}\n\n🕳 *Ниша {current+1}* — Ширина (СМ):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        state['step_name'] = 'angle_done'
        _save_wall_draft(context, room_id)
        await _after_angle_from_update(update, context, room_id)
        return

    if step in ('wall_rounded_radius', 'wall_wavy_note', 'wall_hidden_note'):
        state['flags'] = state.get('flags') or dict(DEFAULT_FLAGS)
        if step == 'wall_rounded_radius':
            state['flags']['rounded'] = True
        elif step == 'wall_wavy_note':
            state['flags']['wavy'] = True
        else:
            state['flags']['hidden'] = True
        state['step_name'] = 'angle_done'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = None
        await _after_angle_from_update(update, context, room_id)
        return

    if step in ('wall_round_opening_width', 'wall_round_opening_height'):
        await _handle_wall_round_opening_input(update, context, step)
        return

    context.user_data['waiting_for'] = None
    await update.message.reply_text("⚠️ Неизвестный шаг.")


async def _after_angle_from_update(update, context, room_id):
    """После угла (через update) — остаток шагов или сохранение.

    ЧИСТАЯ ЛОГИКА: см. _after_angle.
    """
    state = _get_wall_state(context)
    remaining = state.get('remaining_steps')

    # --- ФАЗА 1: первый заход ---
    if remaining is None:
        flags_queue = _wall_flags_list(context)
        state['flags'] = dict(DEFAULT_FLAGS)
        state['remaining_steps'] = flags_queue
        _save_wall_draft(context, room_id)
        remaining = flags_queue
        print(f"🔷 _after_angle_from_update: первый заход, очередь={remaining}", flush=True)

    # --- ФАЗА 2: пусто → сохраняем ---
    if not remaining:
        print(f"🔷 _after_angle_from_update: очередь пуста → сохранение", flush=True)
        await _wall_save_and_next_from_update(update, context, room_id, state.get('step_num') or 1)
        return

    # --- ФАЗА 3: берём [0] ---
    first = remaining[0]
    state['remaining_steps'] = remaining[1:]
    _save_wall_draft(context, room_id)
    print(f"🔷 _after_angle_from_update: берём {first!r}, осталось {state['remaining_steps']}", flush=True)

    if first == 'niche':
        state['step_name'] = 'niche_count'
        _save_wall_draft(context, room_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data=f"wall_niche_count_1_{room_id}")],
            [InlineKeyboardButton("2", callback_data=f"wall_niche_count_2_{room_id}")],
            [InlineKeyboardButton("3", callback_data=f"wall_niche_count_3_{room_id}")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        await update.message.reply_text("🕳 *Сколько нишей на этой стене?*", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return
    if first == 'rounded':
        state['step_name'] = 'rounded'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_rounded_radius'
        await update.message.reply_text("🔄 *Закругление*\n\n📏 Радиус (СМ):", parse_mode=ParseMode.MARKDOWN)
        return
    if first == 'wavy':
        # Уже прошли через 3 точки — пропускаем
        if state.get('plane') == 'wavy':
            state['remaining_steps'] = remaining[1:] if len(remaining) > 1 else []
            _save_wall_draft(context, room_id)
            await _after_angle_from_update(update, context, room_id)
            return
        context.user_data['wall_room_id'] = room_id
        state['plane'] = 'wavy'
        state['step_name'] = 'plane_wavy'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        await update.message.reply_text("📐 *Разная по высоте*\n\n📏 Введи НИЗ стены (СМ):", parse_mode=ParseMode.MARKDOWN)
        return
    if first == 'hidden':
        state['step_name'] = 'hidden'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_hidden_note'
        await update.message.reply_text("🔧 *Скрытые коммуникации*\n\nОпиши что и где:", parse_mode=ParseMode.MARKDOWN)
        return
    await _wall_save_and_next_from_update(update, context, room_id, state.get('step_num') or 1)


async def _wall_save_and_next_from_update(update, context, room_id, step):
    """Сохранение стены (версия для update.message)."""
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

    try: session_id = ensure_session(room_id)
    except Exception: session_id = None

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
    if niches: summary += f"\n🕳 Нишей: {len(niches)}"

    if step >= core_spec.get_total_walls():
        complete_walls_round(room_id)
        areas = calculate_room_areas(room_id)
        text = summary + "\n\n🎉 *Все 4 стены замерены!*\n\n"
