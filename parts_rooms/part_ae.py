            text += f"⚠️ Контур не замкнут: разрыв {closure.get('gap_cm', 0)} см ({closure.get('gap_percent', 0)}%)\n"
    except Exception:
        pass

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
        [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
    ])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


# ============================================================


# ============================================================
# CALLBACK'И ОБХОДА СТЕН
# ============================================================

async def handle_wall_round_callback(query, context, data):
    """Обработчик всех callback'ов обхода стен.

    Возвращает True, если обработано.
    """
    # --- СТАРТ / ПРОДОЛЖЕНИЕ ---
    if data.startswith("wall_round_start_"):
        room_id = int(data.replace("wall_round_start_", ""))
        await _wall_round_start(query, context, room_id)
        return True

    # --- СБРОС ---
    if data.startswith("wall_round_reset_"):
        room_id = int(data.replace("wall_round_reset_", ""))
        walls = get_measures(room_id, category='wall')
        for w in walls:
            delete_measure(w['id'])
        try:
            db_commit("UPDATE rooms SET walls_started_at = NULL, walls_completed_at = NULL WHERE id = ?", (room_id,))
        except Exception:
            pass
        _clear_wall_draft(room_id)
        _reset_wall_state(context)
        state = _get_wall_state(context)
        state['step_num'] = 1
        state['step_name'] = 'flags'
        await _show_wall_step(query, context, room_id, 1, phase='flags', use_photo=True)
        return True

    # --- ФЛАГИ (галочки) ---
    if data.startswith("wall_round_flag_"):
        parts = data.replace("wall_round_flag_", "").rsplit("_", 1)
        flag = parts[0]
        room_id = int(parts[1])
        state = _get_wall_state(context)
        flags = state.get('flags') or dict(DEFAULT_FLAGS)
        flags[flag] = not flags.get(flag, False)
        state['flags'] = flags
        _save_wall_draft(context, room_id)
        step = state.get('step_num') or 1
        # use_photo=False — обновление галочки, без мигания
        await _show_wall_step(query, context, room_id, step, phase='flags', use_photo=False)
        return True

    # --- ФЛАГИ → ДАЛЬШЕ ---
    if data.startswith("wall_round_flags_done_"):
        room_id = int(data.replace("wall_round_flags_done_", ""))
        state = _get_wall_state(context)
        state['step_name'] = 'plane'
        _save_wall_draft(context, room_id)
        await _show_wall_plane(query, context, room_id)
        return True

    # --- ПРОПУСК СТЕНЫ ---
    if data.startswith("wall_round_skip_"):
        room_id = int(data.replace("wall_round_skip_", ""))
        state = _get_wall_state(context)
        step = state.get('step_num') or 1
        if step >= core_spec.get_total_walls():
            complete_walls_round(room_id)
            _clear_wall_draft(room_id)
            _reset_wall_state(context)
            await _wall_finish(query, context, room_id, "⏭ Стена пропущена")
            return True
        # Сбрасываем state и идём к следующей стене
        _reset_wall_state(context)
        state = _get_wall_state(context)
        state['step_num'] = step + 1
        state['step_name'] = 'flags'
        _save_wall_draft(context, room_id)
        await _show_wall_step(query, context, room_id, step + 1, phase='flags')
        return True

    # --- ПЛОСКОСТЬ ---
    if data.startswith("wall_round_plane_straight_"):
        room_id = int(data.replace("wall_round_plane_straight_", ""))
        context.user_data['wall_room_id'] = room_id
        state = _get_wall_state(context)
        state['plane'] = 'straight'
        state['step_name'] = 'length'
        _save_wall_draft(context, room_id)
        await _show_wall_length(query, context, room_id, state.get('step_num') or 1)
        return True

    if data.startswith("wall_round_plane_wavy_"):
        room_id = int(data.replace("wall_round_plane_wavy_", ""))
        context.user_data['wall_room_id'] = room_id
        state = _get_wall_state(context)
        state['plane'] = 'wavy'
        state['step_name'] = 'plane_wavy'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        step = state.get('step_num') or 1
        caption = (
            f"🧱 *Стена {step}*\n\n"
            f"📏 *Замер в 3 точках:*\n\n"
            f"Введи НИЗ стены (СМ):"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В комнату", callback_data=f"room_{room_id}")],
        ])
        # Фото для этого шага нет (нужна специальная схема «вид на стену»)
        # Просто текстовое сообщение — БЕЗ вводящего в заблуждение PNG
        try:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            try:
                await query.get_bot().send_message(
                    chat_id=query.message.chat_id, text=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            except Exception as e:
                print(f"⚠️ plane_wavy send: {e}", flush=True)
        return True

    # --- ПРОЁМЫ ПРИ ОБХОДЕ ---
    if data.startswith("wall_round_open_win_"):
        room_id = int(data.replace("wall_round_open_win_", ""))
        return await _wall_round_open_start(query, context, room_id, 'window')

    if data.startswith("wall_round_open_door_"):
        room_id = int(data.replace("wall_round_open_door_", ""))
        return await _wall_round_open_start(query, context, room_id, 'door_interior')

    if data.startswith("wall_round_open_vent_"):
        room_id = int(data.replace("wall_round_open_vent_", ""))
        return await _wall_round_open_start(query, context, room_id, 'vent')

    if data.startswith("wall_round_openings_done_"):
        room_id = int(data.replace("wall_round_openings_done_", ""))
        state = _get_wall_state(context)
        state['step_name'] = 'angle'
        _save_wall_draft(context, room_id)
        # Первый вход на шаг угла — с фото
        await _show_wall_angle(query, context, room_id, state.get('step_num') or 1, use_photo=True)
        return True

    # --- УГОЛ ---
    if data.startswith("wall_round_angle_90_"):
        room_id = int(data.replace("wall_round_angle_90_", ""))
        state = _get_wall_state(context)
        print(f"🔵 wall_round_angle_90_: room_id={room_id}, state['step_num']={state.get('step_num')!r}", flush=True)
        state['angle_value'] = 90
        state['angle_method'] = '90'
        state['step_name'] = 'angle_done'
        _save_wall_draft(context, room_id)
        await _after_angle(query, context, room_id)
        return True

    if data.startswith("wall_round_angle_60_"):
        room_id = int(data.replace("wall_round_angle_60_", ""))
        state = _get_wall_state(context)
        state['angle_method'] = '60'
        state['step_name'] = 'angle'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_angle_val'
        try:
            await query.edit_message_text(
                "📏 *Диагональ (60-80-100)*\n_Идеал: 100 см_\n\nВведи в СМ:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("wall_round_angle_100_"):
        room_id = int(data.replace("wall_round_angle_100_", ""))
        state = _get_wall_state(context)
        state['angle_method'] = '100'
        state['step_name'] = 'angle'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_angle_val'
        try:
            await query.edit_message_text(
                "📏 *Диагональ (100-100)*\n_Идеал: 141 см_\n\nВведи в СМ:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("wall_round_angle_deg_"):
        room_id = int(data.replace("wall_round_angle_deg_", ""))
        state = _get_wall_state(context)
        state['angle_method'] = 'deg'
        state['step_name'] = 'angle'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_angle_val'
        try:
            await query.edit_message_text(
                "📐 *Угол в градусах*\n\nВведи (например 93):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    # --- НИШИ ---
    if data.startswith("wall_niche_count_"):
        parts = data.replace("wall_niche_count_", "").rsplit("_", 1)
        count = int(parts[0])
        room_id = int(parts[1])
        state = _get_wall_state(context)
        state['niche_count'] = count
        state['niche_current'] = 1
        state['niches'] = []
        state['niche_temp'] = {}
        _save_wall_draft(context, room_id)
        await _show_niche_width(query, context, room_id)
        return True

    if data.startswith("wall_niche_plane_rect_"):
        room_id = int(data.replace("wall_niche_plane_rect_", ""))
        state = _get_wall_state(context)
        temp = state.get('niche_temp') or {}
        temp['width_top'] = temp.get('width')
        temp['depth_top'] = temp.get('depth')
        niches = state.get('niches') or []
        niches.append(temp)
        state['niches'] = niches
        state['niche_temp'] = {}
        _save_wall_draft(context, room_id)

        total = state.get('niche_count') or 1
        current = state.get('niche_current') or 1
        if current < total:
            state['niche_current'] = current + 1
            _save_wall_draft(context, room_id)
            await _show_niche_width(query, context, room_id)
            return True
        # Все ниши обработаны — идём к следующему шагу в очереди
        print(f"🔷 wall_niche_plane_rect: все ниши собраны ({len(niches)}), → _after_angle", flush=True)
        await _after_angle(query, context, room_id)
        return True

    if data.startswith("wall_niche_plane_irr_"):
        room_id = int(data.replace("wall_niche_plane_irr_", ""))
        await _show_niche_top_width(query, context, room_id)
        return True

    return False


# ============================================================
# СТАРТ ОБХОДА С ВОССТАНОВЛЕНИЕМ
# ============================================================

async def _wall_round_start(query, context, room_id):
    """Главный вход в обход стен. Восстанавливает прогресс из БД."""
    progress = get_walls_progress(room_id)
    if progress['walls_count'] >= core_spec.get_total_walls():
        await query.edit_message_text(
            "✅ Все 4 стены уже замерены.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Заново", callback_data=f"wall_round_reset_{room_id}")],
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return
