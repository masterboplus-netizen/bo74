    """Начало/продолжение замера комнаты."""
    print(f"🟣 _handle_room_start: room_id={room_id}", flush=True)
    room = get_room(room_id)
    if not room:
        try:
            await query.edit_message_text("❌ Комната не найдена")
        except Exception:
            pass
        return

    h_bottom = room.get('height_bottom')
    h_middle = room.get('height_middle')
    h_top = room.get('height_top')
    height_ok = bool(h_bottom and h_middle and h_top)
    walls = get_walls_ordered(room_id)
    walls_ok = len(walls) >= core_spec.get_total_walls()

    # === ЭТАП ВЫСОТЫ ===
    if not height_ok:
        if h_bottom and not (h_middle and h_top):
            context.user_data['height_room_id'] = room_id
            context.user_data['height_step'] = 2 if not h_middle else 3
            context.user_data['height_bottom'] = h_bottom
            context.user_data['height_middle'] = h_middle
            context.user_data['height_top'] = h_top
            context.user_data['waiting_for'] = 'room_height_point'
            try:
                await query.edit_message_text(
                    f"🚀 *Продолжаем замер*\n\n📏 Шаг 1: Высота\n✅ Точка 1 (центр): {h_bottom} см",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Продолжить", callback_data=f"room_height_three_start_{room_id}")],
                        [InlineKeyboardButton("🔄 Заново", callback_data=f"room_height_ask_{room_id}")],
                    ])
                )
            except Exception:
                pass
            return
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        try:
            await query.edit_message_text(
                f"🚀 *Мастер замеров*\n\n📏 *Шаг 1 из 3: Высота потолка*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Начать", callback_data=f"room_height_ask_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    # === ЭТАП ОБХОДА СТЕН ===
    if not walls_ok:
        # Спросить количество стен (если ещё не задано в этом сеансе)
        if not context.user_data.get('total_walls_asked'):
            context.user_data['total_walls_asked'] = True
            context.user_data['waiting_for'] = 'total_walls'
            try:
                await query.edit_message_text(
                    "📐 Сколько стен в комнате?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("3", callback_data=f"room_total_walls_{room_id}_3")],
                        [InlineKeyboardButton("4", callback_data=f"room_total_walls_{room_id}_4")],
                        [InlineKeyboardButton("5", callback_data=f"room_total_walls_{room_id}_5")],
                        [InlineKeyboardButton("6", callback_data=f"room_total_walls_{room_id}_6")],
                        [InlineKeyboardButton("Другое", callback_data=f"room_total_walls_{room_id}_other")],
                        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                    ])
                )
            except Exception as e:
                print("total_walls ask: " + str(e), flush=True)
            return
        # ⬇⬇⬇ ГЛАВНЫЙ ФИКС ⬇⬇⬇
        # Проверяем черновик — если есть незавершённая стена, восстанавливаем её
        try:
            draft = fetchone("SELECT step_name, step_num FROM wall_drafts WHERE room_id = ?", (room_id,))
        except Exception as e:
            print(f"⚠️ чтение wall_drafts: {e}", flush=True)
            draft = None

        # sqlite3.Row не поддерживает .get() — конвертируем в dict
        if draft:
            try:
                draft = dict(draft)
            except Exception:
                pass

        if draft and draft.get('step_name'):
            print(f"🟢 _handle_room_start: НАЙДЕН ЧЕРНОВИК step_name={draft['step_name']!r}, step_num={draft['step_num']!r} — восстанавливаем", flush=True)
            context.user_data['wall_room_id'] = room_id
            start_walls_round(room_id)
            await _wall_round_start(query, context, room_id)
            return

        # Черновика нет — начинаем с начала
        print(f"🟠 _handle_room_start: черновика нет, начинаем с галочек стены 1", flush=True)
        _reset_wall_state(context, keep_step_num=1)
        state = _get_wall_state(context)
        state['step_num'] = 1
        state['step_name'] = 'flags'
        context.user_data['wall_room_id'] = room_id
        start_walls_round(room_id)
        await _show_wall_step(query, context, room_id, 1, phase='flags', use_photo=True)
        return

    # === ФИНИШ (все стены) ===
    areas = calculate_room_areas(room_id)
    total_length = sum((w['length'] if w['length'] else 0) for w in walls)
    text = (
        f"🎉 *Замер комнаты завершён!*\n\n"
        f"📏 Высота: {room.get('height') or '—'} см\n"
        f"🧱 Стены: {len(walls)} шт.\n"
        f"📐 Сумма длин: {total_length:.0f} см\n"
    )
    if areas.get('walls_net') is not None:
        text += f"📊 Площадь стен: {areas['walls_net']} м²\n"
    if areas.get('floor'):
        text += f"📊 Площадь пола: {areas['floor']} м²\n"
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
    except Exception:
        pass



async def _handle_height_callback(query, context, data):
    """Обработка callback'ов высоты."""
    if data.startswith("room_height_ask_"):
        room_id = int(data.replace("room_height_ask_", ""))
        context.user_data['height_room_id'] = room_id
        try:
            await query.edit_message_text(
                "📏 *Высота потолка*\n\nВысота одинаковая во всей комнате\nили отличается в разных точках?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Одинаковая (1 замер)", callback_data=f"room_height_same_start_{room_id}")],
                    [InlineKeyboardButton("📏 Разная (3 замера)", callback_data=f"room_height_three_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("room_height_same_start_"):
        room_id = int(data.replace("room_height_same_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_mode'] = 'same'
        context.user_data['waiting_for'] = 'room_height_same'
        try:
            await query.message.delete()
        except Exception:
            pass
        caption = (
            "📏 *Высота потолка*\n\n"
            "Введи ОДНУ цифру в СМ — она применится ко всем точкам:\n\n"
            "_Например: 305_"
        )
        png = _image_path("height_scheme_step1.png")
        if png and os.path.exists(png):
            try:
                with open(png, "rb") as f:
                    await query.message.chat.send_photo(
                        photo=f, caption=caption, parse_mode=ParseMode.MARKDOWN
                    )
                return True
            except Exception:
                pass
        await query.message.chat.send_message(caption, parse_mode=ParseMode.MARKDOWN)
        return True

    if data.startswith("room_height_three_start_"):
        room_id = int(data.replace("room_height_three_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        context.user_data['height_mode'] = 'three'
        await _show_height_step(query, context, room_id, step=1)
        return True

    if data.startswith("room_height_same_"):
        # Старое — уже обрабатывается вводом
        return True

    return False


# ============================================================
# ОБРАБОТЧИК ВВОДА (главный)
# ============================================================

async def _handle_group_load_input(update, context):
    """Обработка ввода мощности группы ЭОМ."""
    if not core_elec:
        await update.message.reply_text("❌ Модуль ЭОМ не загружен")
        context.user_data['waiting_for'] = None
        return

    floor_id = context.user_data.get('group_floor_id')
    room_id = context.user_data.get('group_room_id')
    purpose = context.user_data.get('group_purpose')
    phase = context.user_data.get('group_phase') or 1

    object_id = None
    if floor_id:
        try:
            from core.floors import get_floor
            floor = get_floor(floor_id)
            object_id = floor.get('object_id') if floor else None
        except Exception:
            pass
    if not object_id and room_id:
        try:
            from core.rooms import get_room
            room = get_room(room_id)
            object_id = room.get('object_id') if room else None
            if not floor_id and room:
                floor_id = room.get('floor_id')
        except Exception:
            pass

    if not (object_id and purpose):
        await update.message.reply_text("❌ Потерялись данные группы")
        context.user_data['waiting_for'] = None
        return

    text_val = (update.message.text or '').strip().replace(',', '.')
    try:
        load_watt = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Нужно число (Вт)")
        return

    if load_watt <= 0 or load_watt > 100000:
        await update.message.reply_text("❌ Мощность от 1 до 100 000 Вт")
        return

    supply = core_elec.get_supply(object_id)
    if not supply:
        core_elec.set_supply(object_id, phase_count=1, voltage=220)

    voltage = 380 if phase == 3 else 220
    current = core_elec.calc_current(load_watt, phase, voltage)
    rating, curve = core_elec.pick_breaker(load_watt, phase, 'C')
    cable = core_elec.pick_cable(load_watt, phase, voltage)
    breaker_type = f"{'3P' if phase == 3 else '1P'} {curve}{rating}"

    purpose_label = core_spec.PURPOSE_TYPES.get(purpose, purpose).split(' ', 1)[-1]
    name = f"{purpose_label} {int(load_watt)}Вт"

    try:
        group_id = core_elec.create_group(
            object_id=object_id,
            room_id=None,
            name=name,
            phase=phase,
            purpose=purpose,
            cable_type=cable,
            load_watt=load_watt,
            breaker_type=breaker_type,
            breaker_curve=curve,
            floor_id=floor_id,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка создания группы: {e}")
        context.user_data['waiting_for'] = None
        return

    for k in ['group_room_id', 'group_floor_id', 'group_purpose', 'group_phase']:
        context.user_data[k] = None
    context.user_data['waiting_for'] = None

    _object_panels = []
    try:
        if core_elec_panels:
            _object_panels = core_elec_panels.get_panels(object_id)
            if len(_object_panels) == 1:
                core_elec_panels.assign_group_to_panel(group_id, _object_panels[0]["id"])
                core_elec_panels.recalc_panel_safe(_object_panels[0]["id"])
    except Exception as _e:
        print("auto assign: " + str(_e), flush=True)

    text = (
        f"✅ *Группа создана*\n\n"
        f"⚡ *{name}*\n"
