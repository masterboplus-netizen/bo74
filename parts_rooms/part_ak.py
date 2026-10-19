                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"floor_groups_{fid}")],
                ])
            )
        except Exception:
            pass
        return True

    return False


async def _show_floors_list(query, object_id):
    """Список помещений объекта."""
    print(f"🟠 _show_floors_list: object_id={object_id}", flush=True)
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else f'Объект {object_id}'

    floors = core_floors.get_floors(object_id)
    text = f"🏠 *Помещения «{obj_name}»*\n\n{core_floors.list_floors_text(object_id)}"

    buttons = []
    for f in floors:
        name = f.get('floor_name') or f"Этаж {f.get('floor_number')}"
        rooms = core_floors.count_rooms(f['id'])
        buttons.append([InlineKeyboardButton(
            f"🏠 {name} ({rooms} комн.)",
            callback_data=f"floor_{f['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить помещение", callback_data=f"obj_floor_add_{object_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")])

    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        print(f"⚠️ _show_floors_list: {e}", flush=True)


async def _show_floor_groups(query, floor_id):
    """Список групп этажа."""
    if not core_elec:
        try:
            await query.edit_message_text("❌ Модуль ЭОМ не загружен")
        except Exception:
            pass
        return

    f = core_floors.get_floor(floor_id)
    name = f.get('floor_name') or f"Этаж {f.get('floor_number')}" if f else "?"

    groups = core_elec.get_groups_by_floor(floor_id)

    lines = [f"⚡ *Группы этажа* «{name}»\n"]
    if not groups:
        lines.append("_Пока групп нет._\n")
    else:
        total_w = 0
        for g in groups:
            lines.append(core_elec.format_group_with_rooms(g['id']))
            total_w += g.get('load_watt') or 0
        lines.append(f"\n📊 *Групп: {len(groups)} · Σ {int(total_w)} Вт*")

    # Распределение по фазам L1/L2/L3 (для объекта этажа)
    try:
        _floor = core_floors.get_floor(floor_id)
        _obj_id = _floor.get('object_id') if _floor else None
        if _obj_id:
            _phase_text = core_elec.format_phase_distribution(_obj_id)
            if _phase_text:
                lines.append("")
                lines.append(_phase_text)
    except Exception as e:
        print(f"⚠️ floor phase distribution: {e}", flush=True)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🍳 Из шаблона (кухня)", callback_data=f"floor_kitchen_{floor_id}")],
        [InlineKeyboardButton("➕ Создать группу", callback_data=f"floor_group_new_{floor_id}")],
        [InlineKeyboardButton("⬅️ К помещению", callback_data=f"floor_{floor_id}")],
    ])
    try:
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception as e:
        print(f"⚠️ _show_floor_groups: {e}", flush=True)


async def _show_floor_card(query, floor_id):
    """Карточка помещения."""
    f = core_floors.get_floor(floor_id)
    if not f:
        try:
            await query.edit_message_text("❌ Помещение не найдено")
        except Exception:
            pass
        return

    object_id = f.get('object_id')
    name = f.get('floor_name') or f"Этаж {f.get('floor_number')}"
    rooms = core_floors.get_rooms_of_floor(floor_id)

    lines = [f"🏠 *{name}*"]
    if f.get('area_sqm'):
        lines.append(f"📐 Площадь: {f['area_sqm']} м²")
    if f.get('height_avg'):
        lines.append(f"📏 Высота: {f['height_avg']} см")
    lines.append("")
    lines.append(f"📦 *Комнаты ({len(rooms)}):*")
    if not rooms:
        lines.append("_Пока нет комнат_")
    else:
        for r in rooms:
            lines.append(f"  • {r['name']}")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Комнаты", callback_data=f"floor_rooms_{floor_id}")],
        [InlineKeyboardButton("💰 Смета этажа", callback_data=f"floor_estimate_{floor_id}")],
        [InlineKeyboardButton("📄 Экспорт TXT", callback_data=f"floor_export_{floor_id}")],
        [InlineKeyboardButton("⚡ Группы этажа", callback_data=f"floor_groups_{floor_id}")],
        [InlineKeyboardButton("⚡ ЭОМ объекта", callback_data=f"obj_elec_{object_id}")],
        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"floor_rename_{floor_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"floor_{floor_id}_del")],
        [InlineKeyboardButton("⬅️ К помещениям", callback_data=f"obj_floors_{object_id}")],
    ])
    try:
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception as e:
        print(f"⚠️ _show_floor_card: {e}", flush=True)


async def _show_floor_rooms_list(query, context, floor_id):
    """Список комнат помещения (кликабельный)."""
    f = core_floors.get_floor(floor_id)
    if not f:
        try:
            await query.edit_message_text("❌ Помещение не найдено")
        except Exception:
            pass
        return
    floor_name = f.get('floor_name') or f"Этаж {f.get('floor_number')}"
    object_id = f.get('object_id')
    rooms = core_floors.get_rooms_of_floor(floor_id)

    text = f"📦 *Комнаты «{floor_name}»*\n\n"
    if not rooms:
        text += "_Пока комнат нет._"
    else:
        text += f"Всего: {len(rooms)}\n"

    buttons = []
    for r in rooms:
        buttons.append([InlineKeyboardButton(
            f"📦 {r['name']}",
            callback_data=f"room_{r['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить комнату", callback_data=f"room_add_{floor_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К помещению", callback_data=f"floor_{floor_id}")])

    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        print(f"⚠️ _show_floor_rooms_list: {e}", flush=True)

async def _do_delete_floor(query, floor_id):
    f = core_floors.get_floor(floor_id)
    if not f:
        return
    object_id = f.get('object_id')
    core_floors.delete_floor(floor_id)
    await _show_floors_list(query, object_id)


async def handle_obj_elec_callback(query, context, data):
    """ЭОМ объекта — основной экран."""
    print(f"🟠 handle_obj_elec_callback: data={data!r}, core_elec={core_elec is not None}", flush=True)
    if not core_elec:
        try:
            await query.edit_message_text("❌ Модуль ЭОМ не загружен")
        except Exception:
            pass
        return True

    # --- ОСНОВНОЙ ЭКРАН ЭОМ ---
    if data.startswith("obj_elec_setup_"):
        object_id = int(data.replace("obj_elec_setup_", ""))
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1-фазное (220В)", callback_data=f"obj_elec_set_{object_id}_1")],
            [InlineKeyboardButton("3-фазное (380В)", callback_data=f"obj_elec_set_{object_id}_3")],
            [InlineKeyboardButton("⬅️ К ЭОМ", callback_data=f"obj_elec_{object_id}")],
        ])
        try:
            await query.edit_message_text(
                "⚡ *Тип электроснабжения объекта*\n\nВыбери:",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            pass
        return True

    if data.startswith("obj_elec_set_"):
        parts = data.replace("obj_elec_set_", "").rsplit("_", 1)
        object_id = int(parts[0])
        phase = int(parts[1])
        voltage = 380 if phase == 3 else 220
        try:
            core_elec.set_supply(object_id, phase_count=phase, voltage=voltage,
                                 meter_type='трёхфазный' if phase == 3 else 'однофазный')
        except Exception as e:
            print(f"⚠️ set_supply: {e}", flush=True)
        await _show_obj_elec(query, object_id)
        return True

    if data.startswith("obj_elec_labor_"):
        object_id = int(data.replace("obj_elec_labor_", ""))
        try:
            from core import object_works as core_works
            text = core_works.format_object_labor(object_id, prefix="elec_")
        except Exception as e:
            print("elec labor: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К электрике", callback_data="obj_elec_" + str(object_id))],
            ]))
        return True

    if data.startswith("obj_elec_") and not data.startswith(("obj_elec_cost_", "obj_elec_pdf_", "obj_elec_labor_")):
        object_id = int(data.replace("obj_elec_", ""))
        await _show_obj_elec(query, object_id)
        return True

    return False


async def _show_obj_elec(query, object_id):
    """Показ основного экрана ЭОМ объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else f'Объект {object_id}'

    text = f"🏢 *{obj_name}*\n\n" + core_elec.format_elec_full(object_id)

    # Расчётный вводной автомат
    try:
        _sb = core_elec.calc_supply_breaker(object_id)
        if _sb and _sb.get('breaker_type'):
            text += (
                f"\n\n🔌 *Расчётный вводной автомат:*\n"
                f"   {_sb['breaker_type']} (ток: {_sb['current_a']} А)\n"
                f"   Σ мощность: {int(_sb['total_watt'])} Вт"
            )
    except Exception as e:
        print(f"⚠️ calc_supply_breaker: {e}", flush=True)

    # Распределение по фазам (если 3ф)
    try:
        _sup = core_elec.get_supply(object_id) or {}
        if _sup.get('phase_count') == 3:
            _phase_text = core_elec.format_phase_distribution(object_id)
            if _phase_text:
                text += "\n\n" + _phase_text
    except Exception as e:
        print(f"⚠️ obj phase distribution: {e}", flush=True)

    supply = core_elec.get_supply(object_id)
    supply_btn = "⚙️ Настроить питание" if not supply else "⚙️ Изменить питание"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(supply_btn, callback_data=f"obj_elec_setup_{object_id}")],
        [InlineKeyboardButton("📋 Кабельный журнал", callback_data=f"cables_list_{object_id}")],
        [InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")],
    ])

    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception as e:
        print(f"⚠️ _show_obj_elec: {e}", flush=True)
        try:
            await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            pass


async def handle_groups_callback(query, context, data):
    """Управление группами ЭОМ."""
    if not core_elec:
        try:
            await query.edit_message_text("❌ Модуль ЭОМ не загружен")
        except Exception:
            pass
        return True

    # --- ТРАССЫ ГРУППЫ ---
    if data.startswith("group_routes_auto_"):
        group_id = int(data.replace("group_routes_auto_", ""))
        try:
            res = core_elec_routes.auto_routes_for_group(group_id, route_type="shtroba") if core_elec_routes else None
