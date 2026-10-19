            )
        except Exception:
            pass
        return True

    if data.startswith("opening_wall_"):
        parts = data.replace("opening_wall_", "").split("_", 1)
        room_id = int(parts[0])
        wall_pos = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['opening_wall_pos'] = wall_pos
        context.user_data['waiting_for'] = 'opening_width'
        try:
            await query.edit_message_text(
                "📏 *Ширина проёма* (СМ):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_show_"):
        opening_id = int(data.replace("opening_show_", ""))
        o = get_opening(opening_id)
        if not o:
            try:
                await query.edit_message_text("❌ Проём не найден")
            except Exception:
                pass
            return True
        otype = o.get('opening_type') or '?'
        label = OPENING_TYPES.get(otype, otype)
        text = f"🚪 *Проём #{opening_id}*\n\n{label}\n"
        text += f"🧱 Стена: {o.get('wall_pos') or '?'}\n"
        if o.get('width'): text += f"📏 Ширина: {o['width']} см\n"
        if o.get('height'): text += f"📏 Высота: {o['height']} см\n"
        if o.get('sill_height'): text += f"📏 Подоконник: {o['sill_height']} см\n"
        buttons = [
            [InlineKeyboardButton("✏️ Ширина", callback_data=f"opening_edit_{opening_id}_width")],
            [InlineKeyboardButton("✏️ Высота", callback_data=f"opening_edit_{opening_id}_height")],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f"opening_del_{opening_id}")],
            [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{o['room_id']}")],
        ]
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass
        return True

    if data.startswith("opening_edit_"):
        parts = data.replace("opening_edit_", "").split("_")
        opening_id = int(parts[0])
        field = parts[1] if len(parts) > 1 else 'width'
        context.user_data['opening_edit_id'] = opening_id
        context.user_data['opening_edit_field'] = field
        context.user_data['waiting_for'] = 'opening_edit_value'
        prompts = {'width': 'Ширина', 'height': 'Высота', 'sill': 'Подоконник'}
        try:
            await query.edit_message_text(
                f"✏️ *{prompts.get(field, 'Значение')}* (СМ):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_show_{opening_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_del_"):
        opening_id = int(data.replace("opening_del_", ""))
        o = get_opening(opening_id)
        room_id = o['room_id'] if o else None
        delete_opening(opening_id)
        if room_id:
            try:
                await query.edit_message_text(
                    "✅ Проём удалён",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{room_id}")],
                    ])
                )
            except Exception:
                pass
        return True

    return False


# ============================================================
# ПЛАН КОМНАТЫ (PNG)
# ============================================================

async def handle_floors_callback(query, context, data):
    """Помещения объекта (этажи / зоны)."""
    print(f"🟠 handle_floors_callback: data={data!r}, core_floors={core_floors is not None}", flush=True)
    if not core_floors:
        try:
            await query.edit_message_text("❌ Модуль помещений не загружен")
        except Exception:
            pass
        return True

    # --- СПИСОК ПОМЕЩЕНИЙ ---
    if data.startswith("floor_export_"):
        try:
            floor_id = int(data.replace("floor_export_", ""))
        except ValueError:
            return
        from core.floor_estimate import format_floor_estimate
        text = format_floor_estimate(floor_id).replace("*", "")
        path = "/tmp/floor_" + str(floor_id) + ".txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename="floor_" + str(floor_id) + "_smeta.txt",
                    caption="📄 Смета помещения",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К помещению", callback_data=f"floor_{floor_id}")],
                    ])
                )
        except Exception as e:
            print("floor_export: " + str(e), flush=True)
        return

    if data.startswith("floor_estimate_"):
        try:
            floor_id = int(data.replace("floor_estimate_", ""))
        except ValueError:
            return
        from core.floor_estimate import format_floor_estimate
        text = format_floor_estimate(floor_id).replace("*", "")
        if len(text) > 4000:
            text = text[:3900] + chr(10) + chr(10) + "..."
        try:
            await _safe_edit(query, text, InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К помещению", callback_data=f"floor_{floor_id}")],
            ]))
        except Exception as e:
            print("floor_estimate: " + str(e), flush=True)
        return

    if data.startswith("obj_floors_"):
        object_id = int(data.replace("obj_floors_", ""))
        await _show_floors_list(query, object_id)
        return True

    # --- СОЗДАТЬ ПОМЕЩЕНИЕ ---
    if data.startswith("obj_floor_type_more_"):
        object_id = int(data.replace("obj_floor_type_more_", ""))
        kb_rows = [
            [InlineKeyboardButton("🧖 Баня", callback_data="obj_floor_type_" + str(object_id) + "_bathhouse"),
             InlineKeyboardButton("🚗 Гараж", callback_data="obj_floor_type_" + str(object_id) + "_garage")],
            [InlineKeyboardButton("📦 Склад", callback_data="obj_floor_type_" + str(object_id) + "_warehouse"),
             InlineKeyboardButton("🔧 Сетевой", callback_data="obj_floor_type_" + str(object_id) + "_utility")],
            [InlineKeyboardButton("🌉 Пролёт", callback_data="obj_floor_type_" + str(object_id) + "_span"),
             InlineKeyboardButton("🏛 Памятник", callback_data="obj_floor_type_" + str(object_id) + "_monument")],
            [InlineKeyboardButton("🌳 Зелёные", callback_data="obj_floor_type_" + str(object_id) + "_green"),
             InlineKeyboardButton("📍 Зона", callback_data="obj_floor_type_" + str(object_id) + "_zone")],
            [InlineKeyboardButton("🌳 Участок", callback_data="obj_floor_type_" + str(object_id) + "_land")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="obj_floor_add_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "🏠 *Другие типы помещений:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("obj_floor_type_"):
        tail = data.replace("obj_floor_type_", "")
        try:
            oid_str, f_type = tail.rsplit("_", 1)
            object_id = int(oid_str)
        except Exception as e:
            print("floor type parse: " + str(e), flush=True)
            return True
        context.user_data["floor_new_type"] = f_type
        context.user_data["floor_new_parent"] = None
        context.user_data["floor_obj_id"] = object_id
        context.user_data["waiting_for"] = "floor_new_name"
        tlabels = {"floor": "🏠 Этаж", "apartment": "🚪 Квартира", "basement": "🏚 Подвал", "common": "🚶 МОП", "zone": "📍 Зона"}
        tlabel = tlabels.get(f_type, f_type)
        try:
            await query.edit_message_text(
                tlabel + " — напиши название:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="obj_floors_" + str(object_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("obj_floor_add_"):
        object_id = int(data.replace("obj_floor_add_", ""))
        context.user_data["floor_obj_id"] = object_id
        kb_rows = [
            [InlineKeyboardButton("🏠 Этаж", callback_data="obj_floor_type_" + str(object_id) + "_floor"),
             InlineKeyboardButton("🚪 Квартира", callback_data="obj_floor_type_" + str(object_id) + "_apartment")],
            [InlineKeyboardButton("🏚 Подвал", callback_data="obj_floor_type_" + str(object_id) + "_basement"),
             InlineKeyboardButton("⚙️ Тех.помещ", callback_data="obj_floor_type_" + str(object_id) + "_technical")],
            [InlineKeyboardButton("🚶 МОП", callback_data="obj_floor_type_" + str(object_id) + "_common"),
             InlineKeyboardButton("🅿️ Парковка", callback_data="obj_floor_type_" + str(object_id) + "_parking")],
            [InlineKeyboardButton("🌿 Ландшафт", callback_data="obj_floor_type_" + str(object_id) + "_landscape"),
             InlineKeyboardButton("🏢 Здание", callback_data="obj_floor_type_" + str(object_id) + "_building")],
            [InlineKeyboardButton("🏠 Дом", callback_data="obj_floor_type_" + str(object_id) + "_house"),
             InlineKeyboardButton("🏔 Кровля", callback_data="obj_floor_type_" + str(object_id) + "_roof")],
            [InlineKeyboardButton("📁 Другие типы", callback_data="obj_floor_type_more_" + str(object_id))],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="obj_floors_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "🏠 *Что создаём?*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True


    # --- КАРТОЧКА ПОМЕЩЕНИЯ ---
    if data.startswith("floor_"):
        parts = data.replace("floor_", "").split("_", 1)
        if parts[0].isdigit():
            floor_id = int(parts[0])
            action = parts[1] if len(parts) > 1 else ''
            if action == 'del':
                await _do_delete_floor(query, floor_id)
            else:
                await _show_floor_card(query, floor_id)
            return True

    # --- КОМНАТЫ ПОМЕЩЕНИЯ (список) ---
    if data.startswith("floor_rooms_"):
        floor_id = int(data.replace("floor_rooms_", ""))
        await _show_floor_rooms_list(query, context, floor_id)
        return True

    # --- ГРУППЫ ЭТАЖА ---
    if data.startswith("floor_groups_"):
        fid = int(data.replace("floor_groups_", ""))
        await _show_floor_groups(query, fid)
        return True

    if data.startswith("floor_group_new_"):
        fid = int(data.replace("floor_group_new_", ""))
        context.user_data['group_floor_id'] = fid
        buttons = []
        for code, label in core_spec.PURPOSE_TYPES.items():
            buttons.append([InlineKeyboardButton(label, callback_data=f"floor_group_purpose_{fid}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"floor_groups_{fid}")])
        try:
            await query.edit_message_text(
                "⚡ *Новая группа этажа*\n\nНазначение:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("floor_group_purpose_"):
        parts = data.replace("floor_group_purpose_", "").rsplit("_", 1)
        fid = int(parts[0])
        purpose = parts[1]
        context.user_data['group_floor_id'] = fid
        context.user_data['group_purpose'] = purpose
        label = core_spec.PURPOSE_TYPES.get(purpose, purpose)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1-фазная", callback_data=f"floor_group_phase_{fid}_1")],
            [InlineKeyboardButton("3-фазная", callback_data=f"floor_group_phase_{fid}_3")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"floor_groups_{fid}")],
        ])
        try:
            await query.edit_message_text(f"⚡ *{label}*\n\nФаза:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            pass
        return True

    if data.startswith("floor_group_phase_"):
        parts = data.replace("floor_group_phase_", "").rsplit("_", 1)
        fid = int(parts[0])
        phase = int(parts[1])
        context.user_data['group_floor_id'] = fid
        context.user_data['group_phase'] = phase
        context.user_data['waiting_for'] = 'group_load_watt'
        try:
            await query.edit_message_text(
                "⚡ Мощность группы в *Вт*?\n\n_Например: 500_",
                parse_mode=ParseMode.MARKDOWN,
