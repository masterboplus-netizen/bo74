"""interfaces/telegram/rooms_comm.py — коммуникации."""
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room
from core.comms import (get_comms, format_comm, get_comm_type_label, get_comm, add_comm, update_comm, delete_comm, COMM_TYPES)
from core.db import fetchone, fetchall, commit as db_commit
from core import spec as core_spec
try:
    from core import elec as core_elec
except Exception:
    core_elec = None

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
        }
        prompt = prompts.get(field, '✏️ Новое значение:')
        try:
            await query.edit_message_text(
                f"{prompt}\n\n_Напиши и отправь._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"comm_show_{comm_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_skip_"):
        # Пропуск шагов — сохраняем как есть
        parts = data.replace("comm_skip_", "").split("_")
        # comm_skip_diameter_<room> / comm_skip_voltage_<room>
        try:
            room_id = int(parts[-1])
        except ValueError:
            return True
        skip_type = parts[0] if parts else None
        if skip_type == 'diameter':
            context.user_data['comm_diameter'] = None
        elif skip_type == 'voltage':
            context.user_data['comm_voltage'] = None
        await _comm_save_and_reply(query.message, context, room_id)
        return True
    # === ПРИВЯЗКА К ГРУППЕ ЭОМ ===
    if data.startswith("comm_group_unset_"):
        comm_id = int(data.replace("comm_group_unset_", ""))
        try:
            if core_elec:
                core_elec.unassign_point_from_group(comm_id)
        except Exception as e:
            print(f"⚠️ unassign_point_from_group: {e}", flush=True)
        await _show_comm_card(query, context, comm_id)
        return True

    if data.startswith("comm_group_set_"):
        parts = data.replace("comm_group_set_", "").rsplit("_", 1)
        comm_id = int(parts[0])
        group_id = int(parts[1])
        try:
            if core_elec:
                core_elec.assign_comm_to_group(comm_id, group_id)
        except Exception as e:
            print(f"⚠️ assign_comm_to_group: {e}", flush=True)
        await _show_comm_card(query, context, comm_id)
        return True

    if data.startswith("comm_group_"):
        comm_id = int(data.replace("comm_group_", ""))
        c = get_comm(comm_id)
        if not c:
            try:
                await query.edit_message_text("❌ Коммуникация не найдена")
            except Exception:
                pass
            return True
        _room_obj = get_room(c.get('room_id')) if c.get('room_id') else None
        _floor_id = _room_obj.get('floor_id') if _room_obj else None
        if not _floor_id:
            try:
                await query.edit_message_text(
                    "⚠️ Комната не привязана к помещению.\n\nСначала привяжи комнату к этажу через «🏠 Помещения».",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")],
                    ])
                )
            except Exception:
                pass
            return True
        try:
            groups = core_elec.get_groups_by_floor(_floor_id) if core_elec else []
        except Exception as e:
            print(f"⚠️ get_groups_by_floor: {e}", flush=True)
            groups = []
        if not groups:
            try:
                await query.edit_message_text(
                    "⚠️ На этом этаже пока нет групп ЭОМ.\n\nСоздай группу через «⚡ Группы этажа».",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")],
                    ])
                )
            except Exception:
                pass
            return True
        label = get_comm_type_label(c.get('comm_type'))
        buttons = []
        for g in groups:
            g_name = (g.get('name') or f"#{g['id']}")[:30]
            w = int(g.get('load_watt') or 0)
            buttons.append([InlineKeyboardButton(
                f"⚡ {g_name} · {w}Вт",
                callback_data=f"comm_group_set_{comm_id}_{g['id']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")])
        try:
            await query.edit_message_text(
                f"📋 *Привязка к группе этажа*\n\n🔧 {label}\n🧱 Стена: {c.get('wall') or '?'}\n\nВыбери группу:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

        await _comm_save_from_context(query, context, room_id)
        return True

    return False



async def _show_comms_list(query, context, room_id):
    """Список коммуникаций комнаты."""
    comms = get_comms(room_id)
    room = get_room(room_id)
    room_name = room['name'] if room else '?'
    text = f"🔧 *Коммуникации в «{room_name}»*\n\n"
    if not comms:
        text += "_Пока ничего не добавлено._\n\nДобавь воду, канализацию, электрику, газ, вентиляцию."
    else:
        text += f"Найдено: {len(comms)}\n\n"
        for i, c in enumerate(comms, 1):
            text += f"{i}. {format_comm(c)}\n"
    buttons = []
    for c in comms:
        label = get_comm_type_label(c.get('comm_type'))
        wall = c.get('wall') or '?'
        buttons.append([InlineKeyboardButton(f"{label} ({wall})", callback_data=f"comm_show_{c['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить", callback_data=f"comm_add_{room_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass



async def _show_comm_card(query, context, comm_id):
    """Карточка коммуникации."""
    c = get_comm(comm_id)
    if not c:
        try:
            await query.edit_message_text("❌ Не найдено")
        except Exception:
            pass
        return
    label = get_comm_type_label(c.get('comm_type'))
    text = f"🔧 *Коммуникация #{comm_id}*\n\n{label}\n"
    text += f"🧱 Стена: {c.get('wall') or '?'}\n"
    if c.get('offset_x') is not None:
        text += f"📐 От угла: {c['offset_x']} см\n"
    if c.get('offset_y') is not None:
        text += f"📏 От пола: {c['offset_y']} см\n"
    if c.get('diameter'):
        text += f"⭕ Диаметр: {c['diameter']} мм\n"
    if c.get('voltage'):
        text += f"⚡ Напряжение: {c['voltage']} В\n"
    if c.get('size'):
        text += f"📦 Размер: {c['size']} см\n"
    buttons = [
        [InlineKeyboardButton("✏️ От угла", callback_data=f"comm_edit_{comm_id}_offset_x"),
         InlineKeyboardButton("✏️ От пола", callback_data=f"comm_edit_{comm_id}_offset_y")],
    ]
    ctype = c.get('comm_type')
    if ctype == 'elec_panel':
        buttons.append([InlineKeyboardButton("✏️ Размер щита", callback_data=f"comm_edit_{comm_id}_size")])
    elif ctype in ('water_cold', 'water_hot', 'sewer', 'heating', 'gas', 'drain', 'vent'):
        buttons.append([InlineKeyboardButton("✏️ Диаметр", callback_data=f"comm_edit_{comm_id}_diameter")])
    # === ПРИВЯЗКА К ГРУППЕ ЭОМ ===
    _room_obj = get_room(c.get('room_id')) if c.get('room_id') else None
    _floor_id = _room_obj.get('floor_id') if _room_obj else None
    if _floor_id and ctype in ('elec_socket', 'elec_switch', 'elec_panel', 'elec_cable'):
        _cur_gid = c.get('group_id')
        if _cur_gid:
            try:
                _g = core_elec.get_group(_cur_gid) if core_elec else None
                _g_name = (_g.get('name') if _g else f"#{_cur_gid}")
            except Exception:
                _g_name = f"#{_cur_gid}"
            buttons.append([InlineKeyboardButton(f"📋 Группа: {_g_name[:25]}", callback_data=f"comm_group_{comm_id}")])
            buttons.append([InlineKeyboardButton("❌ Отвязать от группы", callback_data=f"comm_group_unset_{comm_id}")])
        else:
            buttons.append([InlineKeyboardButton("📋 → Привязать к группе", callback_data=f"comm_group_{comm_id}")])
    buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data=f"comm_del_{comm_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К коммуникациям", callback_data=f"room_comms_{c['room_id']}")])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass



async def _comm_save_from_context(query, context, room_id):
    """Сохраняет коммуникацию из context.user_data."""
    ctype = context.user_data.get('comm_type')
    wall = context.user_data.get('comm_wall')
    offset_x = context.user_data.get('comm_offset_x')
    offset_y = context.user_data.get('comm_offset_y')
    if not all([room_id, ctype, wall]):
        try:
            await query.edit_message_text("❌ Потерялись данные")
        except Exception:
            pass
        return
    try:
        add_comm(room_id=room_id, comm_type=ctype, wall=wall,
                 offset_x=offset_x, offset_y=offset_y)
    except Exception as e:
        print(f"⚠️ add_comm: {e}", flush=True)
        return
    for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
              'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_size',
              'comm_size_w', 'comm_size_h', 'comm_size_d', 'waiting_for']:
        context.user_data[k] = None
    label = get_comm_type_label(ctype)
    text = f"✅ *{label}* добавлена!\n\n🧱 {wall}\n"
    if offset_x is not None:
        text += f"📐 От угла: {offset_x} см\n"
    if offset_y is not None:
        text += f"📏 От пола: {offset_y} см\n"
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
                [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
            ])
        )
    except Exception:
        pass


# ============================================================
# ПРОЁМЫ (отдельные) — CALLBACK'И
# ============================================================


async def _comm_save_and_reply(message, context, room_id):
    """Сохраняет коммуникацию и отвечает."""
    from core.comms import add_comm, get_comm_type_label
    from core.geometry import wall_offset_to_world, calc_wall_coords
    from core.measures import get_walls_ordered

    ctype = context.user_data.get('comm_type')
    wall = context.user_data.get('comm_wall')
    offset_x = context.user_data.get('comm_offset_x')
    offset_y = context.user_data.get('comm_offset_y')
    diameter = context.user_data.get('comm_diameter')
    voltage = context.user_data.get('comm_voltage')

    world_x = world_y = world_z = None
    try:
        walls = get_walls_ordered(room_id)
        coords = calc_wall_coords(walls)
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



async def _handle_comm_input(update, context, step):
    """Обработка ввода коммуникаций: offset_x → offset_y → финал."""
    from core.comms import get_comm_type_label

    room_id = context.user_data.get('comm_room_id')
    ctype = context.user_data.get('comm_type')
    wall = context.user_data.get('comm_wall')

    if not (room_id and ctype and wall):
        context.user_data['waiting_for'] = None
        await update.message.reply_text("❌ Потерялись данные. Начни заново.")
        return

    text_val = (update.message.text or '').strip().replace(',', '.')
    try:
        val = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Введи число")
        return

    if step == 'comm_offset_x':
        if val < 0 or val > 50000:
            await update.message.reply_text("❌ От 0 до 50000 см")
            return
        context.user_data['comm_offset_x'] = val
        context.user_data['waiting_for'] = 'comm_offset_y'
        await update.message.reply_text(
            "📏 *Высота от пола* (СМ):\n\n_Например: 30_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
            ])
        )
        return

    if step == 'comm_offset_y':
        if val < 0 or val > 5000:
            await update.message.reply_text("❌ От 0 до 5000 см")
            return
        context.user_data['comm_offset_y'] = val

        if ctype in ('water_cold', 'water_hot', 'sewer', 'drain', 'heating', 'gas', 'vent'):
            context.user_data['waiting_for'] = 'comm_diameter'
            await update.message.reply_text(
                "⭕ *Диаметр* (ММ):\n\n_Например: 20_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Пропустить", callback_data=f"comm_skip_diameter_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
                ])
            )
            return
        if ctype in ('elec_socket', 'elec_switch', 'elec_panel', 'elec_cable', 'net_internet', 'net_tv', 'net_phone', 'net_cctv'):
            context.user_data['waiting_for'] = 'comm_voltage'
            await update.message.reply_text(
                "⚡ *Напряжение* (В):\n\n_Например: 220_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Пропустить", callback_data=f"comm_skip_voltage_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
                ])
            )
            return
        await _comm_save_and_reply(update.message, context, room_id)
        return

    if step == 'comm_diameter':
        if val < 1 or val > 500:
            await update.message.reply_text("❌ От 1 до 500 мм")
            return
        context.user_data['comm_diameter'] = val
        await _comm_save_and_reply(update.message, context, room_id)
        return

    if step == 'comm_voltage':
        if val < 1 or val > 10000:
            await update.message.reply_text("❌ От 1 до 10000 В")
            return
        context.user_data['comm_voltage'] = val
        await _comm_save_and_reply(update.message, context, room_id)
        return

    context.user_data['waiting_for'] = None
    await update.message.reply_text("⚠️ Неизвестный шаг: " + str(step))


