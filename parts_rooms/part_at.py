        wc = next((c for c in coords if c.get('wall_pos') == wall), None)
        if wc and offset_x is not None:
            world_x, world_y, world_z = wall_offset_to_world(wc, offset_x, offset_y or 0)
    except Exception as e:
        print(f"⚠️ world calc: {e}", flush=True)

    try:
        add_comm(
            room_id=room_id, comm_type=ctype, wall=wall,
            offset_x=offset_x, offset_y=offset_y,
            diameter=diameter, voltage=voltage,
            world_x=world_x, world_y=world_y, world_z=world_z,
        )
    except Exception as e:
        print(f"⚠️ add_comm: {e}", flush=True)
        await message.reply_text(f"❌ Ошибка сохранения: {e}")
        return

    for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
              'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_size',
              'comm_size_w', 'comm_size_h', 'comm_size_d', 'waiting_for']:
        context.user_data[k] = None

    label = get_comm_type_label(ctype)
    text = f"✅ *{label}* добавлена!\n\n🧱 Стена: {wall}\n"
    if offset_x is not None:
        text += f"📐 От угла: {int(offset_x)} см\n"
    if offset_y is not None:
        text += f"📏 От пола: {int(offset_y)} см\n"
    if diameter:
        text += f"⭕ Ø {int(diameter)} мм\n"
    if voltage:
        text += f"⚡ {int(voltage)} В\n"

    await message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
            [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
        ])
    )


async def _handle_opening_input(update, context, step):
    """Ввод проёмов (отдельных)."""
    text_val = (update.message.text or '').strip().replace(',', '.')
    try:
        val = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Введи число")
        return

    if step == 'opening_width':
        room_id = context.user_data.get('opening_room_id')
        context.user_data['opening_width'] = val
        context.user_data['waiting_for'] = 'opening_height'
        await update.message.reply_text(
            "📏 *Высота проёма* (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
            ])
        )
        return

    if step == 'opening_height':
        room_id = context.user_data.get('opening_room_id')
        otype = context.user_data.get('opening_type')
        wall_pos = context.user_data.get('opening_wall_pos')
        width = context.user_data.get('opening_width')
        try:
            session_id = ensure_session(room_id)
        except Exception:
            session_id = None
        add_opening(room_id=room_id, opening_type=otype, wall_pos=wall_pos,
                    width=width, height=val, session_id=session_id,
                    created_by=update.effective_user.id if update.effective_user else None)
        for k in ['opening_room_id', 'opening_type', 'opening_wall_pos',
                  'opening_width', 'opening_height', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            f"✅ *Проём добавлен!*\n\n{OPENING_TYPES.get(otype, otype)} на стене «{wall_pos}»\n📏 {width} × {val} см",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"opening_add_{room_id}")],
                [InlineKeyboardButton("✅ К проёмам", callback_data=f"openings_list_{room_id}")],
            ])
        )
        return

    if step == 'opening_edit_value':
        opening_id = context.user_data.get('opening_edit_id')
        field = context.user_data.get('opening_edit_field')
        if field == 'width':
            update_opening(opening_id, width=val)
        elif field == 'height':
            update_opening(opening_id, height=val)
        elif field == 'sill':
            update_opening(opening_id, sill_height=val)
        context.user_data['waiting_for'] = None
        context.user_data['opening_edit_id'] = None
        context.user_data['opening_edit_field'] = None
        await update.message.reply_text(
            "✅ Обновлено!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К проёму", callback_data=f"opening_show_{opening_id}")],
            ])
        )
        return


# ============================================================
# ОБЪЕКТЫ — РЕДАКТИРОВАНИЕ
# ============================================================

async def handle_object_callback(update, context, data):
    """Обработчик obj_* — вызывается из handle_rooms_callback."""
    from modules.objects import get_object, delete_object

    if data.startswith("obj_del_"):
        object_id = int(data.replace("obj_del_", ""))
        obj = get_object(object_id)
        name = obj['name'] if obj else '?'
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"obj_delok_{object_id}")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"obj_{object_id}")],
        ])
        try:
            await update.callback_query.edit_message_text(
                f"🗑 *Удалить объект «{name}»?*\n\n"
                f"Будут удалены: комнаты, замеры, проёмы, коммуникации.\n"
                f"Задачи и финансы — отвязаны (не удалены).",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            pass
        return True

    if data.startswith("obj_delok_"):
        object_id = int(data.replace("obj_delok_", ""))
        delete_object(object_id)
        try:
            await update.callback_query.edit_message_text(
                "✅ Объект удалён",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("obj_rename_"):
        object_id = int(data.replace("obj_rename_", ""))
        context.user_data['waiting_for'] = 'obj_rename'
        context.user_data['obj_rename_id'] = object_id
        try:
            await update.callback_query.edit_message_text(
                "✏️ *Новое имя объекта:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"obj_{object_id}")],
                ])
            )
        except Exception:
            pass
        return True

    return False

# ============================================================
# КУХОННЫЕ ШАБЛОНЫ (кафе/рестораны) — UI
# ============================================================

async def handle_kitchen_callback(query, context, data):
    """Обработчик кухонных шаблонов. Возвращает True если обработано."""
    if not core_elec:
        return False

    # --- ПОКАЗ СПИСКА ОБОРУДОВАНИЯ ---
    if data.startswith("floor_kitchen_add_"):
        parts = data.replace("floor_kitchen_add_", "").rsplit("_", 1)
        floor_id = int(parts[0])
        equip_idx = int(parts[1])
        items = core_elec.get_kitchen_equipment()
        if equip_idx < 0 or equip_idx >= len(items):
            try:
                await query.edit_message_text("Оборудование не найдено")
            except Exception:
                pass
            return True
        equip_code = items[equip_idx][0]
        try:
            _floor = core_floors.get_floor(floor_id)
            _obj_id = _floor.get('object_id') if _floor else None
        except Exception:
            _obj_id = None
        if not _obj_id:
            try:
                await query.edit_message_text("Помещение не найдено")
            except Exception:
                pass
            return True
        try:
            gid = core_elec.create_kitchen_group(_obj_id, floor_id, equip_code)
        except Exception as e:
            print(f"kitchen create: {e}", flush=True)
            gid = None
        if gid:
            try:
                _g = core_elec.get_group(gid)
                _name = (_g.get('name') if _g else '?')
                _phase = (_g.get('phase') if _g else 0) or 1
                _load = int((_g.get('load_watt') if _g else 0) or 0)
                _breaker = (_g.get('breaker_type') if _g else '-') or '-'
                _cable = (_g.get('cable_type') if _g else '-') or '-'
                _voltage = 380 if _phase == 3 else 220
                try:
                    _current = core_elec.calc_current(_load, _phase, _voltage)
                except Exception:
                    _current = 0
                try:
                    _cable_label = core_spec.get_cable_label(_cable)
                except Exception:
                    _cable_label = _cable
                _text = (
                    "✅ Группа создана!\n\n"
                    "⚡ " + str(_name) + "\n"
                    "Фаза: " + str(_phase) + "ф (" + str(_voltage) + "В)\n"
                    "Мощность: " + str(_load) + " Вт\n"
                    "Ток: " + str(_current) + " А\n"
                    "Автомат: " + str(_breaker) + "\n"
                    "Кабель: " + str(_cable_label)
                )
                await query.edit_message_text(
                    _text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Ещё оборудование", callback_data="floor_kitchen_" + str(floor_id))],
                        [InlineKeyboardButton("⚡ К группам этажа", callback_data="floor_groups_" + str(floor_id))],
                    ])
                )
            except Exception as e:
                print(f"kitchen msg: {e}", flush=True)
                try:
                    await query.edit_message_text(
                        "✅ Группа создана (ID: " + str(gid) + ")",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("<< Назад", callback_data="floor_kitchen_" + str(floor_id))],
                        ])
                    )
                except Exception:
                    pass
        else:
            try:
                await query.edit_message_text(
                    "❌ Не удалось создать группу.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("<< Назад", callback_data="floor_kitchen_" + str(floor_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("floor_kitchen_all_"):
        floor_id = int(data.replace("floor_kitchen_all_", ""))
        try:
            _floor = core_floors.get_floor(floor_id)
            _obj_id = _floor.get('object_id') if _floor else None
        except Exception:
            _obj_id = None
        if not _obj_id:
            return True
        created = 0
        try:
            items = core_elec.get_kitchen_equipment()
            for code, name, watts, phase in items:
                try:
                    gid = core_elec.create_kitchen_group(_obj_id, floor_id, code)
                    if gid:
                        created += 1
                except Exception as e:
                    print(f"kitchen all {code}: {e}", flush=True)
        except Exception as e:
            print(f"kitchen all: {e}", flush=True)
        try:
            await query.edit_message_text(
                "Создано: " + str(created) + " групп.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("<< Назад", callback_data="floor_groups_" + str(floor_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("floor_kitchen_"):
        floor_id = int(data.replace("floor_kitchen_", ""))
        try:
            items = core_elec.get_kitchen_equipment()
