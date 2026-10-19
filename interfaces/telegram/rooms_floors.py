"""interfaces/telegram/rooms_floors.py — помещения (этажи / зоны)."""
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room
from core.db import fetchone, fetchall, commit as db_commit
from core import spec as core_spec
try:
    from core import floors as core_floors
except Exception:
    core_floors = None

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




# === Дополнительные функции этажей ===

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


