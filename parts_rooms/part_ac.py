            "📍 *Точка 1 — ЦЕНТР комнаты*\n\n"
            "Встань в центре комнаты, приложи дальномер к полу, наведи на потолок.\n\n"
            "Введи результат в СМ:\n\n_Например: 305_"
        ),
        2: (
            "📏 *Высота — шаг 2*\n\n"
            "📍 *Точка 2 — у ЛЕВОГО угла*\n\n"
            "Введи результат в СМ:\n\n_Например: 304_"
        ),
        3: (
            "📏 *Высота — шаг 3*\n\n"
            "📍 *Точка 3 — у ПРАВОГО угла*\n\n"
            "Введи результат в СМ:\n\n_Например: 306_"
        ),
    }
    caption = captions.get(step, captions[1])
    kb_extra = [
        [InlineKeyboardButton("✅ Все три одинаковые", callback_data=f"room_height_same_{room_id}")],
    ]
    context.user_data['waiting_for'] = 'room_height_point'
    context.user_data['height_room_id'] = room_id
    context.user_data['height_step'] = step

    # target — callback (query) или Update
    if hasattr(target, 'message') and hasattr(target, 'edit_message_text'):
        # Это CallbackQuery
        try:
            await target.message.delete()
        except Exception:
            pass
        await _send_height_scheme(target.message, context, room_id, step, caption, kb_extra)
    elif hasattr(target, 'message'):
        # Это Update
        await _send_height_scheme(target.message, context, room_id, step, caption, kb_extra)


# ============================================================
# ОБХОД СТЕН: ПОКАЗ ЭКРАНОВ
# ============================================================

async def _show_wall_step(query, context, room_id, step, phase='flags', use_photo=False):
    """Экран галочек стены.

    use_photo=True — только при первом входе на стену (отправка фото).
    use_photo=False — при обновлении галочек (просто edit_message_text, БЕЗ мигания).
    """
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = phase
    _save_wall_draft(context, room_id)

    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
    flags = state.get('flags') or DEFAULT_FLAGS

    spec_step = spec.get_wall_step('flags', n=step, pos=pos)
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        image = spec_step.get('image')
    else:
        caption = f"🧱 *Стена {step} — {pos}*\n\n👁 Осмотри стену.\nОтметь особенности:"
        image = f"wall_scheme_s{step}_flags.png"

    f_niche = '✅' if flags.get('niche') else '⬜'
    f_rounded = '✅' if flags.get('rounded') else '⬜'
    f_wavy = '✅' if flags.get('wavy') else '⬜'
    f_hidden = '✅' if flags.get('hidden') else '⬜'

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{f_niche} С нишей", callback_data=f"wall_round_flag_niche_{room_id}")],
        [InlineKeyboardButton(f"{f_rounded} С закруглением", callback_data=f"wall_round_flag_rounded_{room_id}")],
        [InlineKeyboardButton(f"{f_wavy} Разная по высоте", callback_data=f"wall_round_flag_wavy_{room_id}")],
        [InlineKeyboardButton(f"{f_hidden} Скрытые коммуникации", callback_data=f"wall_round_flag_hidden_{room_id}")],
        [InlineKeyboardButton("➡️ Дальше", callback_data=f"wall_round_flags_done_{room_id}")],
        [InlineKeyboardButton("⏭ Пропустить стену", callback_data=f"wall_round_skip_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    # При обновлении галочек — просто редактируем (плавно, без мигания)
    if use_photo:
        await _send_png_or_edit(query, caption, kb, image)
        return

    # use_photo=False — редактируем существующее сообщение.
    # Если это фото — edit_caption; если текст — edit_text.
    # Никогда не пересоздаём, не шлём новое сообщение.
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
    except Exception as e:
        err = str(e).lower()
        if "message is not modified" in err:
            return
        print(f"⚠️ _show_wall_step edit: {e}", flush=True)


async def _show_wall_plane(query, context, room_id):
    """Экран плоскости стены (ровная / кривая)."""
    state = _get_wall_state(context)
    state['step_name'] = 'plane'
    _save_wall_draft(context, room_id)

    step = state.get('step_num') or 1
    flags = state.get('flags') or {}

    # Если галочка "Разная по высоте" уже стоит — сразу ввод 3 точек (с фото)
    if flags.get('wavy'):
        state['plane'] = 'wavy'
        state['step_name'] = 'plane_wavy'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        caption = (
            f"🧱 *Стена {step}*\n\n"
            f"📏 *Замер в 3 точках:*\n\n"
            f"Введи НИЗ стены (СМ):"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В комнату", callback_data=f"room_{room_id}")],
        ])
        # Фото для этого шага нет — только текст
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
                print(f"⚠️ plane (wavy) send: {e}", flush=True)
        return

    spec_step = spec.get_wall_step('plane', n=step, pos=core_spec.get_wall_name(step, core_spec.get_total_walls()))
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        if spec_step.get('hint'):
            caption += f"\n\n{spec_step['hint']}"
        image = spec_step.get('image')
    else:
        caption = (
            f"🧱 *Стена {step}*\n\n"
            f"📐 *Плоскость стены:*\n\n"
            f"Стена ровная или кривая по высоте?\n\n"
            f"_Если стена «горбатая» — нужно замерить в 3 точках._"
        )
        image = f"wall_scheme_s{step}_plane.png"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_round_plane_straight_{room_id}")],
        [InlineKeyboardButton("📏 Разная (3 точки)", callback_data=f"wall_round_plane_wavy_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_wall_length(query, context, room_id, step):
    """Экран длины стены."""
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

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_wall_openings(query, context, room_id, step):
    """Экран проёмов стены."""
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = 'openings'
    _save_wall_draft(context, room_id)

    context.user_data['waiting_for'] = None
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
    await _send_png_or_edit(query, text, kb, None)


async def _show_wall_angle(query, context, room_id, step, use_photo=False):
    """Экран угла между стенами.

    use_photo=True — при первом входе (пересоздать сообщение с фото).
    use_photo=False — при восстановлении/возврате (edit_caption, без пересоздания).
    """
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = 'angle'
    _save_wall_draft(context, room_id)

    context.user_data['waiting_for'] = None
    length_cm = state.get('length') or 0

    spec_step = spec.get_wall_step('angle', n=step, pos=core_spec.get_wall_name(step, core_spec.get_total_walls()), length=length_cm)
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        if spec_step.get('hint'):
            caption += f"\n\n{spec_step['hint']}"
        image = spec_step.get('image')
    else:
        caption = (
            f"✅ Длина: *{length_cm} см*\n\n"
            f"📐 *Угол между этой стеной и следующей:*\n\n"
            f"Обычно 90° — прямой угол."
        )
        image = f"wall_scheme_s{step}_angle.png"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 90° (прямой)", callback_data=f"wall_round_angle_90_{room_id}")],
        [InlineKeyboardButton("📏 60-80-100", callback_data=f"wall_round_angle_60_{room_id}")],
        [InlineKeyboardButton("📏 100-100", callback_data=f"wall_round_angle_100_{room_id}")],
        [InlineKeyboardButton("✏️ Угол в °", callback_data=f"wall_round_angle_deg_{room_id}")],
        [InlineKeyboardButton("⬅️ В комнату", callback_data=f"room_{room_id}")],
    ])
    if use_photo:
        await _send_png_or_edit(query, caption, kb, image)
        return

    # use_photo=False — редактируем существующее, при неудаче — пересоздаём.
    msg = query.message
    is_photo = bool(getattr(msg, "photo", None))
    print(f"🟠 _show_wall_angle (use_photo=False): is_photo={is_photo}, step={step}", flush=True)
    try:
        if is_photo:
            await query.edit_message_caption(caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        else:
            await query.edit_message_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        print(f"🟢 _show_wall_angle (use_photo=False): edit OK", flush=True)
    except Exception as e:
        err = str(e).lower()
        print(f"⚠️ _show_wall_angle edit failed: {e}", flush=True)
        if "message is not modified" in err:
            # Ничего не поменялось — но кнопки могут быть привязаны к другому сообщению.
            # Проверим, есть ли reply_markup
            return
        # Все остальные ошибки — пересоздаём сообщение
        chat_id = query.message.chat_id
        # Если есть фото — переслать с фото, иначе текст
        if image and _image_path(image) and os.path.exists(_image_path(image)):
            try:
                with open(_image_path(image), "rb") as f:
                    await query.get_bot().send_photo(
                        chat_id=chat_id, photo=f, caption=caption,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                    )
                print(f"🟢 _show_wall_angle: fallback send_photo OK", flush=True)
                return
            except Exception as e2:
                print(f"⚠️ _show_wall_angle send_photo fallback: {e2}", flush=True)
