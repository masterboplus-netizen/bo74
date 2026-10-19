
    start_walls_round(room_id)
    next_step = progress['current_step']

    # Пытаемся восстановить черновик
    step_name = _load_wall_draft(context, room_id)
    print(f"🔍 _wall_round_start: room_id={room_id}, next_step={next_step}, step_name={step_name!r}", flush=True)

    state = _get_wall_state(context)
    # Если черновика нет — начинаем с начала
    if step_name is None:
        state['step_num'] = next_step
        state['step_name'] = 'flags'
        _save_wall_draft(context, room_id)
        # Первый вход — фото
        await _show_wall_step(query, context, room_id, next_step, phase='flags', use_photo=True)
        return

    # Восстанавливаем step_num из черновика
    step_num = state.get('step_num') or next_step
    context.user_data['wall_room_id'] = room_id

    # === ОБРАБОТКА ВСЕХ step_name ===
    if step_name == 'flags':
        # Восстановление — показываем фото как при первом входе
        await _show_wall_step(query, context, room_id, step_num, phase='flags', use_photo=True)
        return

    if step_name == 'plane':
        await _show_wall_plane(query, context, room_id)
        return

    if step_name == 'plane_wavy':
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            f"🧱 *Стена {step_num}*\n\n"
            f"📏 *Продолжаем замер в 3 точках:*\n\n"
            f"Введи НИЗ стены (СМ):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if step_name == 'length':
        await _show_wall_length(query, context, room_id, step_num)
        return

    if step_name == 'openings':
        await _show_wall_openings(query, context, room_id, step_num)
        return

    if step_name == 'angle':
        # Восстановление — edit_caption (без пересоздания)
        await _show_wall_angle(query, context, room_id, step_num, use_photo=False)
        return

    if step_name == 'angle_done':
        await _after_angle(query, context, room_id)
        return

    # === ВОТ ОН, ТОТ САМЫЙ БАГ — niche_width !!! ===
    if step_name == 'niche_width':
        await _show_niche_width(query, context, room_id)
        return

    if step_name == 'niche_depth':
        await _show_niche_depth(query, context, room_id)
        return

    if step_name == 'niche_height':
        await _show_niche_height(query, context, room_id)
        return

    if step_name == 'niche_plane':
        await _show_niche_plane(query, context, room_id)
        return

    if step_name == 'niche_top_width':
        await _show_niche_top_width(query, context, room_id)
        return

    if step_name == 'niche_top_depth':
        await _show_niche_top_depth(query, context, room_id)
        return

    if step_name == 'niche_count':
        await _show_niche_count(query, context, room_id)
        return

    # Fallback — галочки (первый раз заходим)
    state['step_num'] = step_num
    state['step_name'] = 'flags'
    _save_wall_draft(context, room_id)
    await _show_wall_step(query, context, room_id, step_num, phase='flags', use_photo=True)


# ============================================================
# ХЕЛПЕРЫ ОБХОДА
# ============================================================

async def _after_angle(query, context, room_id):
    """После угла — обрабатываем remaining_steps (ниши/rounded/wavy/hidden).

    ЧИСТАЯ ЛОГИКА:
    - remaining_steps is None  → первый заход. Читаем флаги, чистим их, ставим очередь.
    - remaining_steps == []    → все обработано, сохраняем стену.
    - remaining_steps == [...] → берём [0], идём по очереди.
    """
    state = _get_wall_state(context)
    remaining = state.get('remaining_steps')

    # --- ФАЗА 1: первый заход после угла ---
    if remaining is None:
        flags_queue = _wall_flags_list(context)
        # ВАЖНО: чистим флаги — иначе они снова попадут в очередь
        state['flags'] = dict(DEFAULT_FLAGS)
        state['remaining_steps'] = flags_queue
        _save_wall_draft(context, room_id)
        remaining = flags_queue
        print(f"🔷 _after_angle: первый заход, очередь={remaining}", flush=True)

    # --- ФАЗА 2: очередь пуста → сохраняем стену ---
    if not remaining:
        step_num = state.get('step_num') or 1
        print(f"🔷 _after_angle: очередь пуста. state['step_num']={state.get('step_num')!r}, ИТОГ step_num={step_num} → _wall_save_and_next", flush=True)
        await _wall_save_and_next(query, context, room_id, step_num)
        return

    # --- ФАЗА 3: берём первый элемент очереди ---
    first = remaining[0]
    state['remaining_steps'] = remaining[1:]
    _save_wall_draft(context, room_id)
    print(f"🔷 _after_angle: берём {first!r}, осталось {state['remaining_steps']}", flush=True)

    if first == 'niche':
        await _show_niche_count(query, context, room_id)
        return

    if first == 'rounded':
        state['step_name'] = 'rounded'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_rounded_radius'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "🔄 *Закругление*\n\n📏 Радиус (СМ):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if first == 'wavy':
        # wavy — если УЖЕ прошли через 3 точки — пропускаем, идём дальше
        if state.get('plane') == 'wavy':
            state['remaining_steps'] = remaining[1:] if len(remaining) > 1 else []
            _save_wall_draft(context, room_id)
            await _after_angle(query, context, room_id)
            return
        # Иначе — первый раз, показываем 3 точки
        state['plane'] = 'wavy'
        state['step_name'] = 'plane_wavy'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "📐 *Разная по высоте*\n\n📏 Введи НИЗ стены (СМ):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if first == 'hidden':
        state['step_name'] = 'hidden'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_hidden_note'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "🔧 *Скрытые коммуникации*\n\nОпиши что и где:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Неизвестный шаг — сохраняем
    step_num = state.get('step_num') or 1
    await _wall_save_and_next(query, context, room_id, step_num)


async def _after_niches(query, context, room_id):
    """После нишей — обрабатываем следующий remaining_step или сохраняем."""
    # Просто делегируем в _after_angle, но remaining_steps уже обрезан
    await _after_angle(query, context, room_id)


async def _wall_round_open_start(query, context, room_id, opening_type):
    """Старт добавления проёма при обходе."""
    state = _get_wall_state(context)
    step = state.get('step_num') or 1
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
    context.user_data['wall_round_opening_type'] = opening_type
    context.user_data['wall_round_opening_wall'] = pos

    if opening_type == 'vent':
        # Вентиляция — сразу высота от пола
        context.user_data['waiting_for'] = 'wall_round_opening_height'
        try:
            await query.edit_message_text(
                "💨 *Вентиляция*\n\n📏 Высота от пола (СМ):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"wall_round_openings_done_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    # Окно/Дверь — сначала ширина
    context.user_data['waiting_for'] = 'wall_round_opening_width'
    label = '🪟 Окно' if opening_type == 'window' else '🚪 Дверь'
    try:
        await query.edit_message_text(
            f"{label}\n\n📏 Ширина (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"wall_round_openings_done_{room_id}")],
            ])
        )
    except Exception:
        pass
    return True


async def _handle_wall_round_input(update, context, step):
    """Ввод при обходе стен."""
    room_id = context.user_data.get('wall_room_id')
    if not room_id:
        # Страховка: восстановить из wall_drafts
        try:
            draft = fetchone("SELECT room_id FROM wall_drafts ORDER BY updated_at DESC LIMIT 1")
            if draft:
                room_id = draft["room_id"]
                context.user_data["wall_room_id"] = room_id
                print(f"⚠️ wall_room_id восстановлен: {room_id}", flush=True)
        except Exception as e:
            print(f"⚠️ restore wall_room_id: {e}", flush=True)
    if not room_id:
        await update.message.reply_text("❌ Потерялась комната. Начни замер заново.")
        context.user_data["waiting_for"] = None
        return
    state = _get_wall_state(context)
    text_val = (update.message.text or '').strip().replace(',', '.')

    if step == 'wall_round_length':
        try:
            length_cm = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        if length_cm <= 0 or length_cm > 5000:
            await update.message.reply_text("❌ Длина от 1 до 5000 см")
            return
        state['length'] = length_cm
        state['step_name'] = 'openings'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = None
        await _show_wall_openings_from_update(update, context, room_id)
        return

    if step == 'wall_round_plane_bottom':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        state['plane_bottom'] = val
        context.user_data['waiting_for'] = 'wall_round_plane_middle'
        step_num = state.get('step_num') or 1
        pos = core_spec.get_wall_name(step_num, core_spec.get_total_walls())
        caption = (
            f"🧱 *Стена {step_num} — {pos}*\n\n"
            f"📏 *Замер в 3 точках*\n"
            f"✅ Точка 1 (низ): *{val} см*\n\n"
            f"📍 *Точка 2 — СЕРЕДИНА стены*\n"
            f"Приложи дальномер на середине стены по высоте.\n\n"
            f"Введи результат в СМ:"
        )
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'wall_round_plane_middle':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
