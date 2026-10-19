"""interfaces/telegram/rooms_elec.py — ЭОМ: щиты, группы, кабели, кухня."""
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room
from core.db import fetchone, fetchall, commit as db_commit
from core import spec as core_spec
try:
    from core import elec as core_elec
except Exception:
    core_elec = None
try:
    from core import elec_panels as core_elec_panels
except Exception:
    core_elec_panels = None
try:
    from core import elec_routes as core_elec_routes
except Exception:
    core_elec_routes = None
try:
    from core import elec_prices as core_elec_prices
except Exception:
    core_elec_prices = None

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
        except Exception as e:
            print("auto routes: " + str(e), flush=True)
            res = None
        if not res:
            try:
                await query.edit_message_text("Ошибка автотрассировки")
            except Exception:
                pass
            return True
        text = (
            "🪄 Авто-трассировка выполнена" + chr(10) + chr(10) +
            "Создано трасс: " + str(res.get('created', 0)) + chr(10) +
            "Пропущено: " + str(res.get('skipped', 0)) + chr(10) +
            "Суммарно: " + str(res.get('total_m', 0)) + " м"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📏 Трассы", callback_data="group_routes_" + str(group_id))],
                    [InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("group_routes_clear_"):
        group_id = int(data.replace("group_routes_clear_", ""))
        try:
            if core_elec_routes:
                core_elec_routes.delete_routes_by_group(group_id, only_auto=True)
        except Exception as e:
            print("clear routes: " + str(e), flush=True)
        try:
            await query.edit_message_text(
                "🗑 Авто-трассы удалены",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("group_routes_"):
        group_id = int(data.replace("group_routes_", ""))
        print("group_routes_ handler: group_id=" + str(group_id), flush=True)
        try:
            text = core_elec_routes.format_routes_summary(group_id=group_id) if core_elec_routes else "Модуль не загружен"
            routes = core_elec_routes.get_routes_by_group(group_id) if core_elec_routes else []
        except Exception as e:
            print("routes show: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
            routes = []
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        kb_rows = []
        for idx, r in enumerate(routes, start=1):
            label = core_elec_routes.format_route(r)[:45] if core_elec_routes else "?"
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + label,
                callback_data="route_" + str(r['id'])
            )])
        kb_rows.append([InlineKeyboardButton("🪄 Авто-трассировка", callback_data="group_routes_auto_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("🗑 Очистить", callback_data="group_routes_clear_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    # --- КАРТОЧКА ТРАССЫ ---
    if data.startswith("route_edit_len_"):
        route_id = int(data.replace("route_edit_len_", ""))
        context.user_data['route_edit_id'] = route_id
        context.user_data['waiting_for'] = 'route_length'
        try:
            await query.edit_message_text(
                "📏 Новая длина (метры):" + chr(10) + chr(10) + "_Например: 12.5_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="route_" + str(route_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("route_edit_type_"):
        route_id = int(data.replace("route_edit_type_", ""))
        context.user_data['route_edit_id'] = route_id
        try:
            await query.edit_message_text(
                "🛠 Выбери тип прокладки:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Штроба", callback_data="route_set_type_" + str(route_id) + "_shtroba")],
                    [InlineKeyboardButton("Потолок", callback_data="route_set_type_" + str(route_id) + "_potolok")],
                    [InlineKeyboardButton("Стяжка", callback_data="route_set_type_" + str(route_id) + "_styazhka")],
                    [InlineKeyboardButton("Лоток", callback_data="route_set_type_" + str(route_id) + "_lotok")],
                    [InlineKeyboardButton("Открыто", callback_data="route_set_type_" + str(route_id) + "_otkryto")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="route_" + str(route_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("route_set_type_"):
        parts = data.replace("route_set_type_", "").rsplit("_", 1)
        route_id = int(parts[0])
        rtype = parts[1]
        try:
            core_elec_routes.update_route(route_id, route_type=rtype, is_manual=1)
        except Exception as e:
            print("route set type: " + str(e), flush=True)
        await _show_route_card(query, route_id)
        return True

    if data.startswith("route_del_"):
        route_id = int(data.replace("route_del_", ""))
        try:
            r = core_elec_routes.get_route(route_id)
            group_id = r.get('group_id') if r else None
            panel_id = r.get('panel_id') if r else None
            core_elec_routes.delete_route(route_id)
        except Exception as e:
            print("route del: " + str(e), flush=True)
            group_id = None
            panel_id = None
        kb = []
        if group_id:
            kb.append([InlineKeyboardButton("⬅️ К трассам группы", callback_data="group_routes_" + str(group_id))])
        elif panel_id:
            kb.append([InlineKeyboardButton("⬅️ К трассам щита", callback_data="panel_routes_" + str(panel_id))])
        try:
            await query.edit_message_text("✅ Трасса удалена", reply_markup=InlineKeyboardMarkup(kb) if kb else None)
        except Exception:
            pass
        return True

    if data.startswith("route_") and not data.startswith(("route_edit_", "route_set_", "route_del_")):
        try:
            route_id = int(data.replace("route_", ""))
        except ValueError:
            return False
        await _show_route_card(query, route_id)
        return True

    # --- КАРТОЧКА ГРУППЫ ---
    if data.startswith("group_panel_pick_"):
        group_id = int(data.replace("group_panel_pick_", ""))
        g = core_elec.get_group(group_id) if core_elec else None
        if not g:
            try:
                await query.edit_message_text("Группа не найдена")
            except Exception:
                pass
            return True
        object_id = g.get('object_id')
        panels = core_elec_panels.get_panels(object_id) if core_elec_panels else []
        if not panels:
            try:
                await query.edit_message_text(
                    "У объекта нет щитов. Создай щит сначала.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("K группе", callback_data="group_" + str(group_id))],
                    ])
                )
            except Exception:
                pass
            return True
        cur_panel_id = g.get('panel_id')
        lines = ["Привязать группу к щиту:", ""]
        kb_rows = []
        for idx, p2 in enumerate(panels, start=1):
            ptype = core_elec_panels.get_panel_type_label(p2.get('panel_type'))
            mark = " - текущий" if p2['id'] == cur_panel_id else ""
            pname = (p2.get('name') or '?')[:30]
            lines.append(str(idx) + ". " + pname + " (" + str(ptype) + ")" + mark)
            label = str(idx) + ". " + pname + mark
            kb_rows.append([InlineKeyboardButton(
                label[:60],
                callback_data="group_panel_set_" + str(group_id) + "_" + str(p2['id'])
            )])
        kb_rows.append([InlineKeyboardButton("K группе", callback_data="group_" + str(group_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("group_panel_set_"):
        parts = data.replace("group_panel_set_", "").rsplit("_", 1)
        group_id = int(parts[0])
        panel_id = int(parts[1])
        try:
            if core_elec_panels:
                core_elec_panels.assign_group_to_panel(group_id, panel_id)
                core_elec_panels.recalc_panel_safe(panel_id)
        except Exception as e:
            print("group_panel_set: " + str(e), flush=True)
        await handle_panels_callback(query, context, "panel_" + str(panel_id))
        return True

    if data.startswith("group_panel_unset_"):
        group_id = int(data.replace("group_panel_unset_", ""))
        _old_panel_id = None
        try:
            _g_before = core_elec.get_group(group_id) if core_elec else None
            _old_panel_id = _g_before.get("panel_id") if _g_before else None
        except Exception:
            _old_panel_id = None
        try:
            if core_elec_panels:
                core_elec_panels.unassign_group_from_panel(group_id)
                if _old_panel_id:
                    core_elec_panels.recalc_panel_safe(_old_panel_id)
        except Exception as e:
            print("group_panel_unset: " + str(e), flush=True)
        _g = core_elec.get_group(group_id) if core_elec else None
        _obj_id = _g.get("object_id") if _g else 0
        await handle_panels_callback(query, context, "panels_list_" + str(_obj_id))
        return True

    if data.startswith("group_") and not data.startswith(("group_new_", "group_purpose_", "group_phase_", "group_routes_")):
        try:
            group_id = int(data.replace("group_", ""))
        except ValueError:
            return False
        try:
            g = core_elec.get_group(group_id) if core_elec else None
        except Exception:
            g = None
        if not g:
            try:
                await query.edit_message_text("Группа не найдена")
            except Exception:
                pass
            return True
        _phase = g.get('phase') or 1
        _load = int(g.get('load_watt') or 0)
        _breaker = g.get('breaker_type') or '—'
        _cable = g.get('cable_type') or '—'
        _purpose = g.get('purpose') or '—'
        _panel_id = g.get('panel_id')
        text = (
            "⚡ *" + str(g.get('name') or '?') + "*" + chr(10) + chr(10) +
            "Назначение: " + str(_purpose) + chr(10) +
            "Фаза: " + str(_phase) + "ф" + chr(10) +
            "Мощность: " + str(_load) + " Вт" + chr(10) +
            "Автомат: " + str(_breaker) + chr(10) +
            "Кабель: " + str(_cable)
        )
        if _panel_id:
            text += chr(10) + "Щит: " + (core_elec_panels.get_panel(_panel_id).get("name") if (core_elec_panels and core_elec_panels.get_panel(_panel_id)) else ("#" + str(_panel_id)))
        kb_rows = [
            [InlineKeyboardButton("📏 Трассы", callback_data="group_routes_" + str(group_id))],
        ]
        if _panel_id:
            kb_rows.append([InlineKeyboardButton("⚡ К щиту", callback_data="panel_" + str(_panel_id))])
            kb_rows.append([InlineKeyboardButton("⚡ Сменить щит", callback_data="group_panel_pick_" + str(group_id))])
            kb_rows.append([InlineKeyboardButton("⚡ Отвязать", callback_data="group_panel_unset_" + str(group_id))])
        else:
            kb_rows.append([InlineKeyboardButton("⚡ Привязать к щиту", callback_data="group_panel_pick_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К группам", callback_data="room_groups_" + str(g.get('room_id') or 0))])
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("group card: " + str(e), flush=True)
        return True

    # --- СПИСОК ГРУПП КОМНАТЫ ---
    if data.startswith("room_groups_"):
        room_id = int(data.replace("room_groups_", ""))
        room = get_room(room_id)
        name = room.get('name', '?') if room else '?'

        # Новая архитектура: группы через точки (room_comms.group_id)
        # Fallback на legacy (room_id) — если точек с группой ещё нет
        groups = core_elec.get_groups_by_room(room_id)
        if not groups:
            groups = core_elec.get_groups(room_id)
        lines = ["📋 Группы ЭОМ «" + str(name) + "»", ""]
        if not groups:
            lines.append("_Пока групп нет._\n")
        else:
            total_w = 0
            for g in groups:
                lines.append(core_elec.format_group(g))
                total_w += g.get('load_watt') or 0
            lines.append(f"\n📊 *Групп: {len(groups)} · Σ {int(total_w)} Вт*")

        kb_rows = []
        for g in groups:
            gname = (g.get('name') or ('Группа #' + str(g['id'])))[:40]
            kb_rows.append([InlineKeyboardButton(
                "⚡ " + gname,
                callback_data="group_" + str(g['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Создать группу", callback_data=f"group_new_{room_id}")])
        kb_rows.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
        kb = InlineKeyboardMarkup(kb_rows)
        try:
            await query.edit_message_text(
                "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            pass
        return True

    # --- СОЗДАНИЕ ГРУППЫ (шаг 1: назначение) ---
    if data.startswith("group_new_"):
        room_id = int(data.replace("group_new_", ""))
        buttons = []
        for code, label in core_spec.PURPOSE_TYPES.items():
            buttons.append([InlineKeyboardButton(label, callback_data=f"group_purpose_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_groups_{room_id}")])
        try:
            await query.edit_message_text(
                "⚡ *Новая группа*\n\nВыбери назначение:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    # --- ВЫБОР НАЗНАЧЕНИЯ (шаг 2: фаза) ---
    if data.startswith("group_purpose_"):
        parts = data.replace("group_purpose_", "").rsplit("_", 1)
        room_id = int(parts[0])
        purpose = parts[1]
        context.user_data['group_room_id'] = room_id
        context.user_data['group_purpose'] = purpose
        label = core_spec.PURPOSE_TYPES.get(purpose, purpose)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1-фазная", callback_data=f"group_phase_{room_id}_1")],
            [InlineKeyboardButton("3-фазная", callback_data=f"group_phase_{room_id}_3")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_groups_{room_id}")],
        ])
        try:
            await query.edit_message_text(
                f"⚡ *{label}*\n\nФаза:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
        except Exception:
            pass
        return True

    # --- ВЫБОР ФАЗЫ (шаг 3: ввод мощности) ---
    if data.startswith("group_phase_"):
        parts = data.replace("group_phase_", "").rsplit("_", 1)
        room_id = int(parts[0])
        phase = int(parts[1])
        context.user_data['group_phase'] = phase
        context.user_data['waiting_for'] = 'group_load_watt'
        try:
            await query.edit_message_text(
                f"⚡ Мощность группы в *Вт*?\n\n_Например: 2000_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_groups_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    return False



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
        except Exception as e:
            print(f"kitchen list: {e}", flush=True)
            items = []
        if not items:
            try:
                await query.edit_message_text("Оборудование не найдено.")
            except Exception:
                pass
            return True
        buttons = []
        for idx, (code, name, watts, phase) in enumerate(items):
            label = name + " " + str(watts) + "W " + str(phase) + "f"
            buttons.append([InlineKeyboardButton(
                label[:60],
                callback_data="floor_kitchen_add_" + str(floor_id) + "_" + str(idx)
            )])
        buttons.append([InlineKeyboardButton(
            ">> Создать все",
            callback_data="floor_kitchen_all_" + str(floor_id)
        )])
        buttons.append([InlineKeyboardButton("<< Назад", callback_data="floor_groups_" + str(floor_id))])
        try:
            await query.edit_message_text(
                "🍳 Кухня. Выбери оборудование:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    return False

# ============================================================
# КАБЕЛЬНЫЙ ЖУРНАЛ — UI
# ============================================================


async def handle_cables_callback(query, context, data):
    """Обработчик кабельного журнала."""
    if not core_elec:
        return False

    if data.startswith("cables_list_"):
        object_id = int(data.replace("cables_list_", ""))
        try:
            cables = core_elec.get_cables_by_object(object_id)
            summary = core_elec.get_cable_summary(object_id)
        except Exception as e:
            print(f"cables list: {e}", flush=True)
            cables = []
            summary = {}
        lines = ["📋 *Кабельный журнал*"]
        if not cables:
            lines.append("")
            lines.append("_Пока кабелей нет._")
        else:
            lines.append("")
            lines.append("Записей: " + str(summary.get('count', 0)) + " / Всего: " + str(summary.get('total_m', 0)) + " м")
            lines.append("")
            for c in cables[:20]:
                lines.append(core_elec.format_cable(c))
        kb_rows = [
            [InlineKeyboardButton("➕ Добавить кабель", callback_data="cables_add_" + str(object_id))],
            [InlineKeyboardButton("⬅️ Назад", callback_data="obj_elec_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print(f"cables list show: {e}", flush=True)
        return True

    if data.startswith("cables_add_"):
        object_id = int(data.replace("cables_add_", ""))
        try:
            groups = core_elec.get_groups_by_object(object_id)
        except Exception as e:
            print(f"cables add groups: {e}", flush=True)
            groups = []
        if not groups:
            try:
                await query.edit_message_text(
                    "⚠️ Сначала создай хотя бы одну группу ЭОМ.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data="cables_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
            return True
        buttons = []
        for g in groups[:20]:
            gname = (g.get('name') or ('Группа #' + str(g['id'])))[:35]
            buttons.append([InlineKeyboardButton(
                "⚡ " + gname,
                callback_data="cables_group_" + str(object_id) + "_" + str(g['id'])
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="cables_list_" + str(object_id))])
        try:
            await query.edit_message_text(
                "📋 *Выбери группу* для кабеля:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("cables_group_"):
        parts = data.replace("cables_group_", "").rsplit("_", 1)
        object_id = int(parts[0])
        group_id = int(parts[1])
        context.user_data['cable_object_id'] = object_id
        context.user_data['cable_group_id'] = group_id
        context.user_data['waiting_for'] = 'cable_from_point'
        try:
            await query.edit_message_text(
                "📋 *Кабель*\n\nОткуда (от щита)?\n\n_Например: Щит этажа_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="cables_list_" + str(object_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("cables_del_"):
        cable_id = int(data.replace("cables_del_", ""))
        try:
            c = core_elec.get_cable(cable_id)
            object_id = c.get('object_id') if c else None
            core_elec.delete_cable(cable_id)
        except Exception as e:
            print(f"cables del: {e}", flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "✅ Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К журналу", callback_data="cables_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    return False

# ============================================================
# ЩИТЫ ЭОМ — UI
# ============================================================


async def _show_route_card(query, route_id):
    """Карточка трассы."""
    try:
        r = core_elec_routes.get_route(route_id) if core_elec_routes else None
    except Exception as e:
        print("route card: " + str(e), flush=True)
        r = None
    if not r:
        try:
            await query.edit_message_text("Трасса не найдена")
        except Exception:
            pass
        return
    # Инфо
    lines = ["📏 Трасса #" + str(route_id), ""]
    lines.append("Длина: " + str(r.get('length_m') or 0) + " м")
    lines.append("Кабель: " + str(r.get('cable_type') or '—'))
    lines.append("Прокладка: " + str(r.get('route_type') or '—'))
    if r.get('is_manual'):
        lines.append("Тип: [ручная]")
    if r.get('to_point_id'):
        lines.append("Точка: #" + str(r['to_point_id']))
    # Цена
    try:
        cost = core_elec_routes.calc_route_cost(route_id) if core_elec_routes else None
        if cost:
            lines.append("")
            lines.append("💵 Кабель: " + str(cost.get('cable_cost', 0)) + " ₽")
            lines.append("🔧 Расходники: " + str(cost.get('consumable_cost', 0)) + " ₽")
            lines.append("💰 Итого: " + str(cost.get('total', 0)) + " ₽")
    except Exception:
        pass
    # Кнопки
    kb = []
    kb.append([InlineKeyboardButton("✏️ Длина", callback_data="route_edit_len_" + str(route_id))])
    kb.append([InlineKeyboardButton("✏️ Тип прокладки", callback_data="route_edit_type_" + str(route_id))])
    kb.append([InlineKeyboardButton("🗑 Удалить", callback_data="route_del_" + str(route_id))])
    gid = r.get('group_id')
    pid = r.get('panel_id')
    if gid:
        kb.append([InlineKeyboardButton("⬅️ К трассам группы", callback_data="group_routes_" + str(gid))])
    elif pid:
        kb.append([InlineKeyboardButton("⬅️ К трассам щита", callback_data="panel_routes_" + str(pid))])
    await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb))



async def handle_panels_callback(query, context, data):
    """Обработчик щитов ЭОМ. Возвращает True если обработано."""
    if not core_elec_panels:
        try:
            await query.edit_message_text("Модуль щитов не загружен")
        except Exception:
            pass
        return True

    # ─── ПОДТВЕРЖДЁННОЕ УДАЛЕНИЕ (ДА) ───
    import re as _re_delok
    _m_delok = _re_delok.match(r"^(plumb|plumb_route|panel_comp|panel|works|comm|opening)_delok_(\d+)$", data)
    if _m_delok:
        _prefix = _m_delok.group(1)
        _item_id = int(_m_delok.group(2))
        _back = "menu_back"
        try:
            if _prefix == "plumb":
                _o = core_plumbing.get_panel(_item_id)
                _obj_id = _o.get("object_id") if _o else None
                core_plumbing.delete_panel(_item_id)
                _back = "plumb_list_" + str(_obj_id)
            elif _prefix == "plumb_route":
                _o = core_plumbing.get_route(_item_id)
                _pid = _o.get("panel_id") if _o else None
                core_plumbing.delete_route(_item_id)
                _back = "plumb_routes_" + str(_pid)
            elif _prefix == "panel_comp":
                _o = core_elec_panels.get_component(_item_id)
                _pid = _o.get("panel_id") if _o else None
                core_elec_panels.delete_component(_item_id)
                _back = "panel_comp_" + str(_pid)
            elif _prefix == "panel":
                _o = core_elec_panels.get_panel(_item_id)
                _obj_id = _o.get("object_id") if _o else None
                core_elec_panels.delete_panel(_item_id)
                _back = "panels_list_" + str(_obj_id)
            elif _prefix == "works":
                from core import object_works as _ow_del
                _o = _ow_del.get_work(_item_id)
                _obj_id = _o.get("object_id") if _o else None
                _ow_del.delete_work(_item_id)
                _back = "works_list_" + str(_obj_id)
        except Exception as _e:
            print("delok fail: " + str(_e), flush=True)
        try:
            await _safe_edit(query, "✅ Удалено", InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=_back)],
            ]))
        except Exception:
            pass
        return True

    # --- СПИСОК ЩИТОВ ОБЪЕКТА ---
    if data.startswith("panels_list_"):
        object_id = int(data.replace("panels_list_", ""))
        try:
            panels = core_elec_panels.get_panels(object_id)
        except Exception as e:
            print("panels list: " + str(e), flush=True)
            panels = []
        from modules.objects import get_object as _get_obj
        _obj = _get_obj(object_id)
        _obj_name = _obj['name'] if _obj else ('Объект ' + str(object_id))
        lines = ["⚡ *Щиты объекта «" + str(_obj_name) + "»*", ""]
        if not panels:
            lines.append("_Пока щитов нет._")
        else:
            total = 0
            for p in panels:
                try:
                    load = core_elec_panels.calc_panel_load(p['id'])
                except Exception:
                    load = 0
                total += load
            lines.append("Щитов: " + str(len(panels)) + " / Общая нагрузка: " + str(total) + " Вт")
            lines.append("")
            for p in panels:
                ptype = core_elec_panels.get_panel_type_label(p.get('panel_type'))
                lines.append("⚡ *" + str(p.get('name') or '?') + "*")
                lines.append("   " + str(ptype))
        kb_rows = []
        for p in panels:
            pname = (p.get('name') or '?')[:35]
            kb_rows.append([InlineKeyboardButton(
                "⚡ " + pname,
                callback_data="panel_" + str(p['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить щит", callback_data="panel_add_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("panels list show: " + str(e), flush=True)
        return True

    # --- КАРТОЧКА ЩИТА ---
    if data.startswith("panel_groups_"):
        panel_id = int(data.replace("panel_groups_", ""))
        try:
            groups = core_elec_panels.get_groups_by_panel(panel_id)
            p = core_elec_panels.get_panel(panel_id)
        except Exception as e:
            print("panel groups: " + str(e), flush=True)
            groups = []
            p = None
        pname = (p.get('name') if p else '?')
        lines = ["📋 Группы щита «" + str(pname) + "»", ""]
        if not groups:
            lines.append("Пока групп нет.")
        else:
            total = 0
            for idx, g in enumerate(groups, start=1):
                total += int(g.get('load_watt') or 0)
                lines.append(str(idx) + ". " + core_elec.format_group(g))
            lines.append("")
            lines.append("📊 Групп: " + str(len(groups)) + " · Σ " + str(total) + " Вт")
        kb_rows = []
        for idx, g in enumerate(groups, start=1):
            gname = (g.get('name') or ('Группа #' + str(g['id'])))[:35]
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + gname,
                callback_data="group_" + str(g['id'])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_input_type_"):
        parts = data.replace("panel_input_type_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        btype = parts[1]
        kb_rows = []
        for r in [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100]:
            kb_rows.append([InlineKeyboardButton(
                str(r) + "А",
                callback_data="panel_input_set_" + str(panel_id) + "_" + btype + "_" + str(r)
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel_input_" + str(panel_id))])
        try:
            await query.edit_message_text(
                "Номинал (" + btype + "):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_input_set_"):
        parts = data.replace("panel_input_set_", "").split("_")
        panel_id = int(parts[0])
        btype = parts[1]
        rating = int(parts[2])
        poles = 3 if btype == 'auto3' else 1
        try:
            core_elec_panels.set_input_breaker(panel_id, breaker_type=btype.replace('auto3', 'auto'),
                                                rating=rating, curve='C', poles=poles)
        except Exception as e:
            print("panel input set: " + str(e), flush=True)
        try:
            s = core_elec_panels.format_selectivity(panel_id)
        except Exception:
            s = ""
        try:
            await query.edit_message_text(
                "Вводной установлен: " + btype + " " + str(rating) + "А" + chr(10) + chr(10) + s,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_input_"):
        panel_id = int(data.replace("panel_input_", ""))
        cur = core_elec_panels.get_input_breaker(panel_id) or {}
        cur_type = cur.get('type') or 'не задан'
        cur_rating = cur.get('rating') or '-'
        cur_fmt = core_elec_panels.format_input_breaker(panel_id)
        s = core_elec_panels.format_selectivity(panel_id)
        text = (
            "🔌 Вводной автомат" + chr(10) + chr(10) +
            "Сейчас: " + cur_fmt + chr(10) + chr(10) +
            s + chr(10) + chr(10) +
            "Выбери тип:"
        )
        kb_rows = [
            [InlineKeyboardButton("Автомат 1ф", callback_data="panel_input_type_" + str(panel_id) + "_auto")],
            [InlineKeyboardButton("Автомат 3ф", callback_data="panel_input_type_" + str(panel_id) + "_auto3")],
            [InlineKeyboardButton("УЗО", callback_data="panel_input_type_" + str(panel_id) + "_uzo")],
            [InlineKeyboardButton("Дифавтомат", callback_data="panel_input_type_" + str(panel_id) + "_dif")],
            [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_children_"):
        panel_id = int(data.replace("panel_children_", ""))
        try:
            children = core_elec_panels.get_child_panels(panel_id)
        except Exception as e:
            print("panel children: " + str(e), flush=True)
            children = []
        lines = ["⬇️ Дочерние щиты:", ""]
        if not children:
            lines.append("_Пока нет._")
        else:
            for c in children:
                ctype = core_elec_panels.get_panel_type_label(c.get('panel_type'))
                lines.append("└ " + str(c.get('name')) + " (" + str(ctype) + ")")
        kb_rows = []
        for c in children:
            kb_rows.append([InlineKeyboardButton(
                "⚡ " + str(c.get('name'))[:35],
                callback_data="panel_" + str(c['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить дочерний", callback_data="panel_child_add_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("panel children show: " + str(e), flush=True)
        return True

    if data.startswith("panel_child_type_"):
        parts = data.replace("panel_child_type_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        ptype = parts[1]
        context.user_data['child_parent_id'] = panel_id
        context.user_data['child_panel_type'] = ptype
        context.user_data['waiting_for'] = 'child_panel_name'
        type_labels = {
            'floor': 'Щит этажа', 'apartment': 'Щит квартиры',
            'outdoor': 'Уличный щит', 'subpanel': 'Подщиток',
        }
        tlabel = type_labels.get(ptype, ptype)
        try:
            await query.edit_message_text(
                "⬇️ Новый дочерний: " + tlabel + chr(10) + chr(10) + "Напиши название:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_child_add_"):
        panel_id = int(data.replace("panel_child_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("⚡ Щит этажа", callback_data="panel_child_type_" + str(panel_id) + "_floor")],
            [InlineKeyboardButton("🏢 Щит квартиры", callback_data="panel_child_type_" + str(panel_id) + "_apartment")],
            [InlineKeyboardButton("📦 Подщиток", callback_data="panel_child_type_" + str(panel_id) + "_subpanel")],
            [InlineKeyboardButton("🌳 Уличный щит", callback_data="panel_child_type_" + str(panel_id) + "_outdoor")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_children_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                "⬇️ Новый дочерний щит" + chr(10) + chr(10) + "Выбери тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_routes_auto_"):
        panel_id = int(data.replace("panel_routes_auto_", ""))
        print("panel_routes_auto handler: panel_id=" + str(panel_id), flush=True)
        try:
            res = core_elec_routes.auto_routes_for_panel(panel_id, route_type="shtroba") if core_elec_routes else None
        except Exception as e:
            print("panel auto routes: " + str(e), flush=True)
            res = None
        if not res:
            try:
                await query.edit_message_text("Ошибка автотрассировки")
            except Exception:
                pass
            return True
        text = (
            "🪄 Авто-трассировка щита" + chr(10) + chr(10) +
            "Групп обработано: " + str(res.get('groups', 0)) + chr(10) +
            "Создано трасс: " + str(res.get('created', 0)) + chr(10) +
            "Суммарно: " + str(res.get('total_m', 0)) + " м"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📏 Трассы щита", callback_data="panel_routes_" + str(panel_id))],
                    [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception as e:
            print("panel auto routes show: " + str(e), flush=True)
        return True

    if data.startswith("panel_routes_"):
        panel_id = int(data.replace("panel_routes_", ""))
        print("panel_routes handler: panel_id=" + str(panel_id), flush=True)
        try:
            text = core_elec_routes.format_routes_summary(panel_id=panel_id) if core_elec_routes else "Модуль не загружен"
        except Exception as e:
            print("panel routes show: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        try:
            routes = core_elec_routes.get_routes_by_panel(panel_id) if core_elec_routes else []
        except Exception:
            routes = []
        kb_rows = []
        for idx, r in enumerate(routes, start=1):
            label = core_elec_routes.format_route(r)[:45] if core_elec_routes else "?"
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + label,
                callback_data="route_" + str(r['id'])
            )])
        kb_rows.append([InlineKeyboardButton("🪄 Трассировать все", callback_data="panel_routes_auto_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_montage_"):
        panel_id = int(data.replace("panel_montage_", ""))
        try:
            if core_elec_routes:
                text = core_elec_routes.format_montage_cost_summary(panel_id=panel_id)
            else:
                text = "Модуль маршрутов не загружен"
        except Exception as e:
            print("panel montage: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_total_"):
        panel_id = int(data.replace("panel_total_", ""))
        print("panel_total handler: panel_id=" + str(panel_id), flush=True)
        try:
            text = _build_panel_total_text(panel_id)
        except Exception as e:
            print("panel total: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_spec_"):
        panel_id = int(data.replace("panel_spec_", ""))
        print("panel_spec handler: panel_id=" + str(panel_id), flush=True)
        if save_panel_spec is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            tmp_dir = tempfile.gettempdir()
            target = os.path.join(tmp_dir, "panel_spec_" + str(panel_id) + ".txt")
            path = save_panel_spec(panel_id, path=target)
            if not path or not os.path.exists(path):
                raise Exception("Файл не создан")
            try:
                p = core_elec_panels.get_panel(panel_id)
                name = (p.get('name') if p else 'panel') or 'panel'
            except Exception:
                name = 'panel'
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=name + "_spec.txt",
                    caption="📄 Спецификация щита «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("panel spec export: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка экспорта: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("panel_pdf_"):
        panel_id = int(data.replace("panel_pdf_", ""))
        try:
            from core.export import pdf_export as _pp
            path = _pp.export_panel_spec_pdf(panel_id)
            if not path:
                raise Exception("PDF не создан")
            p = core_elec_panels.get_panel(panel_id)
            name = (p.get("name") if p else "panel") or "panel"
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_spec.pdf",
                    caption="📄 PDF-спецификация щита «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("panel_pdf: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка PDF: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("obj_elec_pdf_"):
        object_id = int(data.replace("obj_elec_pdf_", ""))
        try:
            from core.export import pdf_export as _pp
            from modules.objects import get_object
            path = _pp.export_object_elec_pdf(object_id)
            if not path:
                raise Exception("PDF не создан")
            o = get_object(object_id)
            name = o["name"] if o else ("obj_" + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_elec.pdf",
                    caption="📄 PDF-смета ЭОМ «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("obj_elec_pdf: " + str(e), flush=True)
        return True

    if data.startswith("plumb_pdf_obj_"):
        object_id = int(data.replace("plumb_pdf_obj_", ""))
        try:
            from core.export import pdf_export as _pp
            from modules.objects import get_object
            path = _pp.export_plumbing_estimate_pdf(object_id)
            if not path:
                raise Exception("PDF не создан")
            o = get_object(object_id)
            name = o["name"] if o else ("obj_" + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_plumb.pdf",
                    caption="📄 PDF-смета сантехники «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("plumb_pdf_obj: " + str(e), flush=True)
        return True

    if data.startswith("panel_est_csv_"):
        panel_id = int(data.replace("panel_est_csv_", ""))
        if save_estimate_csv is None or export_panel_estimate_csv is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_panel_estimate_csv(panel_id)
            if not content:
                raise Exception("Пустая смета")
            target = os.path.join(tempfile.gettempdir(), "panel_est_" + str(panel_id) + ".csv")
            path = save_estimate_csv(content, path=target, prefix="panel_est")
            if not path or not os.path.exists(path):
                raise Exception("Файл не создан")
            try:
                p = core_elec_panels.get_panel(panel_id)
                name = (p.get('name') if p else 'panel') or 'panel'
            except Exception:
                name = 'panel'
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=name + "_smeta.csv",
                    caption="📊 Смета щита «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("panel est csv: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка экспорта: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("obj_est_csv_"):
        object_id = int(data.replace("obj_est_csv_", ""))
        if save_estimate_csv is None or export_object_estimate_csv is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_object_estimate_csv(object_id)
            if not content:
                raise Exception("Пустая смета")
            target = os.path.join(tempfile.gettempdir(), "obj_est_" + str(object_id) + ".csv")
            path = save_estimate_csv(content, path=target, prefix="obj_est")
            if not path or not os.path.exists(path):
                raise Exception("Файл не создан")
            from modules.objects import get_object
            o = get_object(object_id)
            name = o['name'] if o else ('obj_' + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_smeta.csv",
                    caption="📊 Смета ЭОМ объекта «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("obj est csv: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка экспорта: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    # ============ ЦЕНЫ ============
    if data.startswith("prices_import_"):
        object_id = int(data.replace("prices_import_", ""))
        if core_marketplaces is None:
            try:
                await query.edit_message_text("Модуль цен не загружен")
            except Exception:
                pass
            return True
        # Сгенерировать шаблон
        try:
            import tempfile, os
            tpl_path = os.path.join(tempfile.gettempdir(), 'prices_template.csv')
            core_marketplaces.generate_csv_template(tpl_path)
            context.user_data['price_csv_object_id'] = object_id
            context.user_data['waiting_for'] = 'price_csv'
            with open(tpl_path, 'rb') as f:
                await query.message.chat.send_document(
                    document=f,
                    filename='prices_template.csv',
                    caption=(
                        "💱 Шаблон прайса (CSV)" + chr(10) + chr(10) +
                        "Заполни и пришли обратно файл — я импортирую цены." + chr(10) + chr(10) +
                        "Формат: component_type;rating;poles;brand;price;currency;market_url;market_sku"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 История импортов", callback_data="prices_history_" + str(object_id))],
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("prices_import: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("prices_history_"):
        object_id = int(data.replace("prices_history_", ""))
        try:
            text = core_marketplaces.format_imports(object_id) if core_marketplaces else "Модуль не загружен"
        except Exception as e:
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К ценам", callback_data="prices_import_" + str(object_id))],
            [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
        ]))
        return True

    # ============ РАБОТЫ ============
    if data.startswith("works_list_"):
        object_id = int(data.replace("works_list_", ""))
        if not core_works:
            try:
                await query.edit_message_text("Модуль работ не загружен")
            except Exception:
                pass
            return True
        try:
            text = core_works.format_object_works(object_id)
        except Exception as e:
            print("works list: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        kb_rows = [
            [InlineKeyboardButton("➕ Добавить работу", callback_data="works_add_" + str(object_id))],
            [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
        ]
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("works_add_type_"):
        parts = data.replace("works_add_type_", "").rsplit("_", 1)
        object_id = int(parts[0])
        wtype = parts[1]
        context.user_data['work_new_object_id'] = object_id
        context.user_data['work_new_type'] = wtype
        context.user_data['waiting_for'] = 'work_new_qty'
        try:
            await query.edit_message_text(
                "🔨 " + core_spec.get_work_label(wtype) + chr(10) + chr(10) +
                "Количество (" + core_spec.get_work_unit(wtype) + "):" + chr(10) + chr(10) +
                "_Например: 15_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="works_list_" + str(object_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("works_add_"):
        object_id = int(data.replace("works_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("Штробление (электро)", callback_data="works_add_type_" + str(object_id) + "_elec_shtroba")],
            [InlineKeyboardButton("Прокладка кабеля", callback_data="works_add_type_" + str(object_id) + "_elec_cable")],
            [InlineKeyboardButton("Установка розетки", callback_data="works_add_type_" + str(object_id) + "_elec_socket")],
            [InlineKeyboardButton("Установка светильника", callback_data="works_add_type_" + str(object_id) + "_elec_light")],
            [InlineKeyboardButton("Монтаж щита", callback_data="works_add_type_" + str(object_id) + "_elec_panel_mount")],
            [InlineKeyboardButton("Прокладка трубы", callback_data="works_add_type_" + str(object_id) + "_plumb_pipe")],
            [InlineKeyboardButton("Установка смесителя", callback_data="works_add_type_" + str(object_id) + "_plumb_socket")],
            [InlineKeyboardButton("Установка унитаза", callback_data="works_add_type_" + str(object_id) + "_plumb_toilet")],
            [InlineKeyboardButton("Установка раковины", callback_data="works_add_type_" + str(object_id) + "_plumb_sink")],
            [InlineKeyboardButton("Установка ванны", callback_data="works_add_type_" + str(object_id) + "_plumb_bath")],
            [InlineKeyboardButton("Установка душа", callback_data="works_add_type_" + str(object_id) + "_plumb_shower")],
            [InlineKeyboardButton("Установка радиатора", callback_data="works_add_type_" + str(object_id) + "_plumb_radiator")],
            [InlineKeyboardButton("Монтаж бойлера", callback_data="works_add_type_" + str(object_id) + "_plumb_boiler")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="works_list_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "🔨 Новая работа" + chr(10) + chr(10) + "Тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("works_del_"):
        work_id = int(data.replace("works_del_", ""))
        try:
            w = core_works.get_work(work_id)
            object_id = w.get('object_id') if w else None
            core_works.delete_work(work_id)
        except Exception as e:
            print("works del: " + str(e), flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К работам", callback_data="works_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("works_edit_qty_"):
        work_id = int(data.replace("works_edit_qty_", ""))
        context.user_data['work_edit_id'] = work_id
        context.user_data['work_edit_field'] = 'qty'
        context.user_data['waiting_for'] = 'work_edit_value'
        w = core_works.get_work(work_id) if core_works else None
        unit = w.get('unit') if w else ''
        try:
            await query.edit_message_text(
                "Новое количество (" + str(unit) + "):" + chr(10) + chr(10) + "_Например: 15_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="works_" + str(work_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("works_edit_price_"):
        work_id = int(data.replace("works_edit_price_", ""))
        context.user_data['work_edit_id'] = work_id
        context.user_data['work_edit_field'] = 'price_unit'
        context.user_data['waiting_for'] = 'work_edit_value'
        try:
            await query.edit_message_text(
                "Новая цена за единицу (₽):" + chr(10) + chr(10) + "_Например: 350_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="works_" + str(work_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("works_") and not data.startswith(("works_list_", "works_add_", "works_del_", "works_edit_")):
        try:
            work_id = int(data.replace("works_", ""))
        except ValueError:
            return False
        w = core_works.get_work(work_id) if core_works else None
        if not w:
            try:
                await query.edit_message_text("Работа не найдена")
            except Exception:
                pass
            return True
        lines = ["🔨 " + str(w.get('work_label') or '?'), ""]
        lines.append("Количество: " + str(w.get('qty') or 0) + " " + str(w.get('unit') or ''))
        lines.append("Цена за ед.: " + str(w.get('price_unit') or 0) + " ₽")
        lines.append("Итого: " + str(w.get('total') or 0) + " ₽")
        mark = " [ручная]" if w.get('is_manual') else ""
        if mark:
            lines.append("Тип: [ручная]")
        kb_rows = [
            [InlineKeyboardButton("✏️ Кол-во", callback_data="works_edit_qty_" + str(work_id)),
             InlineKeyboardButton("✏️ Цена", callback_data="works_edit_price_" + str(work_id))],
            [InlineKeyboardButton("🗑 Удалить", callback_data="works_del_" + str(work_id))],
            [InlineKeyboardButton("⬅️ К работам", callback_data="works_list_" + str(w.get('object_id')))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    # ============ САНТЕХНИКА ============
    if data.startswith("plumb_list_"):
        object_id = int(data.replace("plumb_list_", ""))
        if not core_plumbing:
            try:
                await query.edit_message_text("Модуль сантехники не загружен")
            except Exception:
                pass
            return True
        panels = core_plumbing.get_panels(object_id)
        lines = ["🔧 Сантехника объекта", ""]
        if not panels:
            lines.append("Пока коллекторов нет.")
        else:
            for idx, p in enumerate(panels, start=1):
                ptype = core_plumbing.get_panel_type_label(p.get('panel_type'))
                lines.append(str(idx) + ". " + str(p.get('name')) + " (" + str(ptype) + ")")
        kb_rows = []
        for idx, p in enumerate(panels, start=1):
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + str(p.get('name'))[:35],
                callback_data="plumb_" + str(p['id'])
            )])
        kb_rows.append([InlineKeyboardButton("🚰 Вода", callback_data="plumb_water_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("💰 Смета сантехники", callback_data="plumb_cost_obj_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("👷 Работы (часы)", callback_data="plumb_labor_obj_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("📊 Смета (CSV)", callback_data="plumb_csv_obj_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("➕ Добавить коллектор", callback_data="plumb_add_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))])
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_add_type_"):
        parts = data.replace("plumb_add_type_", "").rsplit("_", 1)
        object_id = int(parts[0])
        ptype = parts[1]
        context.user_data['plumb_new_object_id'] = object_id
        context.user_data['plumb_new_type'] = ptype
        context.user_data['waiting_for'] = 'plumb_new_name'
        type_labels = {
            'collector': 'Коллектор', 'riser': 'Стояк',
            'boiler': 'Котёл', 'pump': 'Насосная группа', 'filter': 'Фильтр',
        }
        try:
            await query.edit_message_text(
                "🔧 Новый элемент: " + type_labels.get(ptype, ptype) + chr(10) + chr(10) +
                "Напиши название (например «Коллектор ХВС»):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_list_" + str(object_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_add_"):
        object_id = int(data.replace("plumb_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("Коллектор", callback_data="plumb_add_type_" + str(object_id) + "_collector")],
            [InlineKeyboardButton("Стояк", callback_data="plumb_add_type_" + str(object_id) + "_riser")],
            [InlineKeyboardButton("Котёл", callback_data="plumb_add_type_" + str(object_id) + "_boiler")],
            [InlineKeyboardButton("Насосная группа", callback_data="plumb_add_type_" + str(object_id) + "_pump")],
            [InlineKeyboardButton("Фильтр", callback_data="plumb_add_type_" + str(object_id) + "_filter")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_list_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "🔧 Новый элемент сантехники" + chr(10) + chr(10) + "Тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_del_"):
        panel_id = int(data.replace("plumb_del_", ""))
        try:
            p = core_plumbing.get_panel(panel_id)
            object_id = p.get('object_id') if p else None
            core_plumbing.delete_panel(panel_id)
        except Exception as e:
            print("plumb del: " + str(e), flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_labor_obj_"):
        object_id = int(data.replace("plumb_labor_obj_", ""))
        try:
            from core import object_works as core_works
            text = core_works.format_object_labor(object_id, prefix="plumb_")
        except Exception as e:
            print("plumb labor obj: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
            ]))
        return True

    if data.startswith("plumb_") and not data.startswith(("plumb_list_", "plumb_add_", "plumb_del_", "plumb_spec_", "plumb_csv_obj_", "plumb_cost_", "plumb_cost_obj_", "plumb_routes_", "plumb_route_", "plumb_points_", "plumb_point_add_", "plumb_point_set_", "plumb_point_unset_", "plumb_pdf_obj_")):
        try:
            panel_id = int(data.replace("plumb_", ""))
        except ValueError:
            return False
        try:
            p = core_plumbing.get_panel(panel_id)
        except Exception:
            p = None
        if not p:
            try:
                await query.edit_message_text("Не найдено")
            except Exception:
                pass
            return True
        ptype = core_plumbing.get_panel_type_label(p.get('panel_type'))
        mount = core_plumbing.get_mount_type_label(p.get('mount_type'))
        lines = ["🔧 " + str(p.get('name')) + " (" + str(ptype) + ")", ""]
        lines.append("Монтаж: " + str(mount))
        if p.get('note'):
            lines.append("Заметка: " + str(p['note']))
        # Трассы
        try:
            routes = core_plumbing.get_routes_by_panel(panel_id)
            lines.append("")
            lines.append("Трассы: " + str(len(routes)))
            for idx, r in enumerate(routes, start=1):
                lines.append("  " + str(idx) + ". " + core_plumbing.format_route(r))
        except Exception:
            pass
        kb_rows = [
            [InlineKeyboardButton("📏 Трассы", callback_data="plumb_routes_" + str(panel_id))],
            [InlineKeyboardButton("➕ Добавить трассу", callback_data="plumb_route_new_" + str(panel_id))],
            [InlineKeyboardButton("💰 Смета коллектора", callback_data="plumb_cost_" + str(panel_id))],
            [InlineKeyboardButton("📍 Точки коллектора", callback_data="plumb_points_" + str(panel_id))],
            [InlineKeyboardButton("📄 Спецификация (TXT)", callback_data="plumb_spec_" + str(panel_id))],
            [InlineKeyboardButton("🔨 Работы сантехники", callback_data="works_list_" + str(p.get('object_id')))],
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(p.get('object_id')))],
            [InlineKeyboardButton("🗑 Удалить", callback_data="plumb_del_" + str(panel_id))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    # --- ТРАССЫ САНТЕХНИКИ ---
    if data.startswith("plumb_routes_"):
        panel_id = int(data.replace("plumb_routes_", ""))
        try:
            routes = core_plumbing.get_routes_by_panel(panel_id)
            p = core_plumbing.get_panel(panel_id)
            pname = p.get('name') if p else '?'
        except Exception as e:
            print("plumb routes: " + str(e), flush=True)
            routes = []
            pname = '?'
        lines = ["📏 Трассы коллектора «" + str(pname) + "»", ""]
        if not routes:
            lines.append("Трасс пока нет.")
        else:
            for idx, r in enumerate(routes, start=1):
                lines.append(str(idx) + ". " + core_plumbing.format_route(r))
        kb_rows = []
        for idx, r in enumerate(routes, start=1):
            label = core_plumbing.format_route(r)[:40]
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + label,
                callback_data="plumb_route_" + str(r['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить", callback_data="plumb_route_new_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))])
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_route_new_"):
        panel_id = int(data.replace("plumb_route_new_", ""))
        context.user_data['plumb_route_panel_id'] = panel_id
        # Шаг 1 — тип трубы
        kb_rows = [
            [InlineKeyboardButton("PPR 20 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr20")],
            [InlineKeyboardButton("PPR 25 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr25")],
            [InlineKeyboardButton("PPR 32 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr32")],
            [InlineKeyboardButton("PEX 16 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_pex16")],
            [InlineKeyboardButton("Медь 15 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_copper15")],
            [InlineKeyboardButton("Канализация 50 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_sewer50")],
            [InlineKeyboardButton("Канализация 110 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_sewer110")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_routes_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                "📏 Новая трасса" + chr(10) + chr(10) + "Тип трубы:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_route_pipe_"):
        parts = data.replace("plumb_route_pipe_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        pipe_type = parts[1]
        context.user_data['plumb_route_pipe'] = pipe_type
        context.user_data['waiting_for'] = 'plumb_route_length'
        try:
            await query.edit_message_text(
                "📏 Длина трассы (метры):" + chr(10) + chr(10) + "_Например: 8.5_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_routes_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_route_del_"):
        route_id = int(data.replace("plumb_route_del_", ""))
        try:
            import sqlite3
            from core.db import fetchone
            row = fetchone("SELECT panel_id FROM plumbing_routes WHERE id = ?", (route_id,))
            panel_id = row['panel_id'] if row else None
            core_plumbing.delete_route(route_id)
        except Exception as e:
            print("plumb route del: " + str(e), flush=True)
            panel_id = None
        if panel_id:
            try:
                await query.edit_message_text(
                    "Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К трассам", callback_data="plumb_routes_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_route_") and not data.startswith(("plumb_route_new_", "plumb_route_pipe_", "plumb_route_del_")):
        try:
            route_id = int(data.replace("plumb_route_", ""))
        except ValueError:
            return False
        try:
            from core.db import fetchone
            row = fetchone("SELECT * FROM plumbing_routes WHERE id = ?", (route_id,))
            r = dict(row) if row else None
        except Exception:
            r = None
        if not r:
            try:
                await query.edit_message_text("Трасса не найдена")
            except Exception:
                pass
            return True
        lines = ["📏 Трасса #" + str(route_id), ""]
        lines.append("Труба: " + core_plumbing.get_pipe_label(r.get('pipe_type')))
        lines.append("Длина: " + str(r.get('length_m') or 0) + " м")
        lines.append("Прокладка: " + str(r.get('route_type') or '—'))
        try:
            cost = core_plumbing.calc_route_cost(route_id)
            if cost:
                lines.append("")
                lines.append("Труба: " + str(cost.get('pipe_cost', 0)) + " ₽")
                lines.append("Расходники: " + str(cost.get('consumable_cost', 0)) + " ₽")
                lines.append("💰 Итого: " + str(cost.get('total', 0)) + " ₽")
        except Exception:
            pass
        kb_rows = [
            [InlineKeyboardButton("🗑 Удалить", callback_data="plumb_route_del_" + str(route_id))],
            [InlineKeyboardButton("⬅️ К трассам", callback_data="plumb_routes_" + str(r.get('panel_id')))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_points_"):
        panel_id = int(data.replace("plumb_points_", ""))
        try:
            text = core_plumbing.format_points_of_panel(panel_id)
        except Exception as e:
            print("plumb points: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Привязать точку", callback_data="plumb_point_add_" + str(panel_id))],
            [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
        ]))
        return True

    if data.startswith("plumb_point_add_"):
        panel_id = int(data.replace("plumb_point_add_", ""))
        p = core_plumbing.get_panel(panel_id)
        object_id = p.get("object_id") if p else None
        all_points = core_plumbing.get_available_plumb_points(object_id) if object_id else []
        used_ids = {pt["id"] for pt in core_plumbing.get_points_of_panel(panel_id)}
        free = [pt for pt in all_points if pt["id"] not in used_ids]
        if not free:
            text = "Свободных plumb-точек нет. Добавь точки в комнатах."
        else:
            text = "Выбери точку для привязки к коллектору:"
        kb_rows = []
        for pt in free[:15]:
            label = str(pt.get("room_name") or "?") + " · " + str(pt.get("comm_type") or "?")
            kb_rows.append([InlineKeyboardButton(label[:60], callback_data="plumb_point_set_" + str(panel_id) + "_" + str(pt["id"]))])
        kb_rows.append([InlineKeyboardButton("⬅️ К точкам", callback_data="plumb_points_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_point_set_"):
        rest = data.replace("plumb_point_set_", "")
        parts = rest.split("_", 1)
        panel_id = int(parts[0])
        point_id = int(parts[1])
        try:
            core_plumbing.assign_point_to_panel(point_id, panel_id)
        except Exception as e:
            print("plumb_point_set: " + str(e), flush=True)
        await handle_panels_callback(query, context, "plumb_points_" + str(panel_id))
        return True

    if data.startswith("plumb_point_unset_"):
        rest = data.replace("plumb_point_unset_", "")
        parts = rest.split("_", 1)
        panel_id = int(parts[0])
        point_id = int(parts[1])
        try:
            core_plumbing.unassign_point_from_panel(point_id, panel_id)
        except Exception as e:
            print("plumb_point_unset: " + str(e), flush=True)
        await handle_panels_callback(query, context, "plumb_points_" + str(panel_id))
        return True

    if data.startswith("plumb_water_"):
        object_id = int(data.replace("plumb_water_", ""))
        try:
            text = core_plumbing.format_water_summary(object_id)
        except Exception as e:
            print("plumb water: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Стояк", callback_data="plumb_add_type_" + str(object_id) + "_riser")],
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
        ]))
        return True

    if data.startswith("plumb_spec_"):
        panel_id = int(data.replace("plumb_spec_", ""))
        if export_plumbing_panel_spec is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_plumbing_panel_spec(panel_id)
            if not content:
                raise Exception("Пустая спецификация")
            target = os.path.join(tempfile.gettempdir(), "plumb_spec_" + str(panel_id) + ".txt")
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            p = core_plumbing.get_panel(panel_id)
            name = (p.get('name') if p else 'panel') or 'panel'
            with open(target, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=name + "_spec.txt",
                    caption="📄 Спецификация сантехники «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("plumb spec: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_csv_obj_"):
        object_id = int(data.replace("plumb_csv_obj_", ""))
        if export_plumbing_object_csv is None or save_estimate_csv is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_plumbing_object_csv(object_id)
            if not content:
                raise Exception("Пустая смета")
            target = os.path.join(tempfile.gettempdir(), "plumb_obj_" + str(object_id) + ".csv")
            path = save_estimate_csv(content, path=target, prefix="plumb_obj")
            from modules.objects import get_object
            o = get_object(object_id)
            name = o['name'] if o else ('obj_' + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_plumb.csv",
                    caption="📊 Смета сантехники «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("plumb csv obj: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_cost_obj_"):
        object_id = int(data.replace("plumb_cost_obj_", ""))
        try:
            text = core_plumbing.format_object_cost(object_id)
        except Exception as e:
            print("plumb cost obj: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
        ]))
        return True

    if data.startswith("plumb_cost_"):
        panel_id = int(data.replace("plumb_cost_", ""))
        try:
            text = core_plumbing.format_panel_cost(panel_id)
        except Exception as e:
            print("plumb cost: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_auto_"):
        panel_id = int(data.replace("panel_auto_", ""))
        try:
            result = core_elec_panels.autocomplete_panel(panel_id)
        except Exception as e:
            print("panel auto: " + str(e), flush=True)
            result = None
        if not result:
            try:
                await query.edit_message_text(
                    "Не удалось автокомплектовать",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
            return True
        text = (
            "Автокомплектация выполнена" + chr(10) + chr(10) +
            "Создано компонентов: " + str(result.get('created', 0)) + chr(10) +
            "Ручных (сохранено): " + str(result.get('manual', 0)) + chr(10) +
            "Групп: " + str(result.get('groups', 0)) + chr(10) +
            "Нагрузка: " + str(result.get('total_watt', 0)) + " Вт" + chr(10) +
            "С K_одновр: " + str(result.get('calc_watt', 0)) + " Вт"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Комплектация", callback_data="panel_comp_" + str(panel_id))],
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_comp_price_"):
        comp_id = int(data.replace("panel_comp_price_", ""))
        context.user_data['component_price_id'] = comp_id
        context.user_data['waiting_for'] = 'component_price'
        try:
            await query.edit_message_text(
                "💰 Введи новую цену (₽):" + chr(10) + chr(10) + "_Например: 350_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_item_" + str(comp_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_comp_del_"):
        comp_id = int(data.replace("panel_comp_del_", ""))
        try:
            c = core_elec_panels.get_component(comp_id)
            panel_id = c.get('panel_id') if c else None
            if c:
                core_elec_panels.delete_component(comp_id)
        except Exception as e:
            print("panel comp del: " + str(e), flush=True)
            panel_id = None
        if panel_id:
            try:
                await query.edit_message_text(
                    "✅ Компонент удалён",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К комплектации", callback_data="panel_comp_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("panel_comp_item_"):
        comp_id = int(data.replace("panel_comp_item_", ""))
        try:
            c = core_elec_panels.get_component(comp_id)
        except Exception as e:
            print("panel comp item: " + str(e), flush=True)
            c = None
        if not c:
            try:
                await query.edit_message_text("Компонент не найден")
            except Exception:
                pass
            return True
        panel_id = c.get('panel_id')
        # Найти порядковый номер компонента среди всех компонентов щита
        try:
            all_comps = core_elec_panels.get_components(panel_id)
            idx = next((i for i, x in enumerate(all_comps, start=1) if x['id'] == comp_id), 0)
            total = len(all_comps)
        except Exception:
            idx = 0
            total = 0
        lines = ["🔧 Компонент " + str(idx) + " из " + str(total), ""]
        lines.append("Тип: " + str(c.get('component_type') or '?'))
        if c.get('component_model'):
            lines.append("Модель: " + str(c['component_model']))
        if c.get('rating'):
            lines.append("Номинал: " + str(c['rating']) + "А")
        if c.get('poles'):
            lines.append("Полюса: " + str(c['poles']) + "P")
        if c.get('curve'):
            lines.append("Кривая: " + str(c['curve']))
        if c.get('rcd_ma'):
            lines.append("УЗО: " + str(c['rcd_ma']) + "мА")
        if c.get('quantity'):
            lines.append("Количество: " + str(c['quantity']))
        if c.get('is_manual'):
            lines.append("Тип: [ручной]")
        lines.append("")
        try:
            price = core_elec_panels.calc_component_price(c)
        except Exception:
            price = 0
        unit_price = c.get('price_unit')
        if unit_price:
            lines.append("💰 Цена за шт: " + str(unit_price) + " ₽ [ручная]")
        lines.append("💰 Итого: " + str(price) + " ₽")
        kb_rows = [
            [InlineKeyboardButton("💰 Изменить цену", callback_data="panel_comp_price_" + str(comp_id))],
            [InlineKeyboardButton("🗑 Удалить", callback_data="panel_comp_del_" + str(comp_id))],
            [InlineKeyboardButton("⬅️ К комплектации", callback_data="panel_comp_" + str(panel_id))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_rating_set_"):
        tail = data.replace("panel_comp_rating_set_", "")
        try:
            pid_str, rest = tail.split("_", 1)
            panel_id = int(pid_str)
            ctype, rating_str = rest.rsplit("_", 1)
            rating = int(rating_str)
        except Exception as e:
            print("rating set parse: " + str(e), flush=True)
            return True
        try:
            _curve = context.user_data.get("panel_comp_curve") or "C"
            core_elec_panels.add_component(panel_id, component_type=ctype, rating=rating, curve=_curve, is_manual=1)
            context.user_data.pop("panel_comp_curve", None)
        except Exception as e:
            print("rating set add: " + str(e), flush=True)
        try:
            await _safe_edit(query, "✅ Компонент добавлен", InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К комплектации", callback_data="panel_comp_" + str(panel_id))],
            ]))
        except Exception:
            pass
        return True

    if data.startswith("panel_comp_rating_manual_"):
        tail = data.replace("panel_comp_rating_manual_", "")
        try:
            pid_str, ctype = tail.rsplit("_", 1)
            panel_id = int(pid_str)
        except Exception as e:
            print("rating manual parse: " + str(e), flush=True)
            return True
        context.user_data["panel_comp_panel_id"] = panel_id
        context.user_data["panel_comp_type"] = ctype
        context.user_data["waiting_for"] = "panel_comp_rating"
        labels = {"breaker": "Автомат", "rcd": "УЗО", "dif": "Дифавтомат", "meter": "Счётчик", "relay": "Реле"}
        tlabel = labels.get(ctype, ctype)
        await _safe_edit(query, "⚡ " + str(tlabel) + chr(10) + chr(10) + "Напиши номинал (А):", InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_comp_curve_set_"):
        tail = data.replace("panel_comp_curve_set_", "")
        try:
            pid_str, rest = tail.split("_", 1)
            panel_id = int(pid_str)
            ctype, curve = rest.rsplit("_", 1)
        except Exception as e:
            print("curve parse: " + str(e), flush=True)
            return True
        context.user_data["panel_comp_curve"] = curve
        context.user_data["panel_comp_panel_id"] = panel_id
        context.user_data["panel_comp_type"] = ctype
        labels = {"breaker": "Автомат", "rcd": "УЗО", "dif": "Дифавтомат", "meter": "Счётчик", "relay": "Реле"}
        tlabel = labels.get(ctype, ctype)
        RATINGS = {"breaker": [6, 10, 16, 20, 25, 32, 40, 50, 63], "rcd": [16, 25, 32, 40, 63, 80, 100], "dif": [16, 20, 25, 32, 40, 63], "meter": [5, 10, 16, 25, 32, 40, 63], "relay": [16, 25, 32, 40, 63]}
        rs = RATINGS.get(ctype, [6, 10, 16, 20, 25, 32, 40, 63])
        kb_rows = []
        row = []
        for r in rs:
            row.append(InlineKeyboardButton(str(r), callback_data="panel_comp_rating_set_" + str(panel_id) + "_" + ctype + "_" + str(r)))
            if len(row) == 3:
                kb_rows.append(row); row = []
        if row: kb_rows.append(row)
        kb_rows.append([InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_" + str(panel_id))])
        text_out = "⚡ " + str(tlabel) + " — кривая " + str(curve) + chr(10) + chr(10) + "Выбери номинал (А):"
        await _safe_edit(query, text_out, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_type_"):
        tail = data.replace("panel_comp_type_", "")
        pid_str, ctype = tail.rsplit("_", 1)
        panel_id = int(pid_str)
        context.user_data["panel_comp_panel_id"] = panel_id
        context.user_data["panel_comp_type"] = ctype
        context.user_data["waiting_for"] = "panel_comp_rating"
        labels = {"breaker": "Автомат", "rcd": "УЗО", "dif": "Дифавтомат", "meter": "Счётчик", "relay": "Реле"}
        tlabel = labels.get(ctype, ctype)
        RATINGS = {"breaker": [6, 10, 16, 20, 25, 32, 40, 50, 63], "rcd": [16, 25, 32, 40, 63, 80, 100], "dif": [16, 20, 25, 32, 40, 63], "meter": [5, 10, 16, 25, 32, 40, 63], "relay": [16, 25, 32, 40, 63]}
        rs = RATINGS.get(ctype, [6, 10, 16, 20, 25, 32, 40, 63])
        kb_rows = []
        if ctype in ("breaker", "dif"):
            kb_rows.append([
                InlineKeyboardButton("A", callback_data="panel_comp_curve_set_" + str(panel_id) + "_" + ctype + "_A"),
                InlineKeyboardButton("B", callback_data="panel_comp_curve_set_" + str(panel_id) + "_" + ctype + "_B"),
                InlineKeyboardButton("C", callback_data="panel_comp_curve_set_" + str(panel_id) + "_" + ctype + "_C"),
                InlineKeyboardButton("D", callback_data="panel_comp_curve_set_" + str(panel_id) + "_" + ctype + "_D"),
            ])
        row = []
        for r in rs:
            row.append(InlineKeyboardButton(str(r), callback_data="panel_comp_rating_set_" + str(panel_id) + "_" + ctype + "_" + str(r)))
            if len(row) == 3:
                kb_rows.append(row); row = []
        if row: kb_rows.append(row)
        kb_rows.append([InlineKeyboardButton("✏️ Другое (ввод вручную)", callback_data="panel_comp_rating_manual_" + str(panel_id) + "_" + ctype)])
        kb_rows.append([InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_" + str(panel_id))])
        text_out = "⚡ " + str(tlabel) + chr(10) + chr(10) + "Выбери номинал (А):"
        await _safe_edit(query, text_out, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_add_"):
        panel_id = int(data.replace("panel_comp_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("⚡ Автомат", callback_data="panel_comp_type_" + str(panel_id) + "_breaker")],
            [InlineKeyboardButton("🛡️ УЗО", callback_data="panel_comp_type_" + str(panel_id) + "_rcd")],
            [InlineKeyboardButton("🛡️⚡ Дифавтомат", callback_data="panel_comp_type_" + str(panel_id) + "_dif")],
            [InlineKeyboardButton("🔢 Счётчик", callback_data="panel_comp_type_" + str(panel_id) + "_meter")],
            [InlineKeyboardButton("🔌 Реле", callback_data="panel_comp_type_" + str(panel_id) + "_relay")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_" + str(panel_id))],
        ]
        await _safe_edit(query, "➕ Ручной компонент" + chr(10) + chr(10) + "Выбери тип:", InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_"):
        panel_id = int(data.replace("panel_comp_", ""))
        try:
            comps = core_elec_panels.get_components(panel_id)
            text = core_elec_panels.format_panel_components(panel_id)
        except Exception as e:
            print("panel comp: " + str(e), flush=True)
            comps = []
            text = "Ошибка"
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "... (обрезано)"
        kb_rows = []
        for idx, c in enumerate(comps, start=1):
            label = core_elec_panels.format_component(c)[:40]
            mark = " [ручной]" if c.get('is_manual') else ""
            num = str(idx) + ". "
            kb_rows.append([InlineKeyboardButton(
                num + label + mark,
                callback_data="panel_comp_item_" + str(c['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить вручную", callback_data="panel_comp_add_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_stats_"):
        panel_id = int(data.replace("panel_stats_", ""))
        try:
            stats = core_elec_panels.get_panel_stats(panel_id)
        except Exception as e:
            print("panel stats: " + str(e), flush=True)
            stats = None
        if not stats:
            try:
                await query.edit_message_text("Ошибка статистики")
            except Exception:
                pass
            return True
        text = (
            "Статистика щита" + chr(10) + chr(10) +
            "Компонентов: " + str(stats.get('components_total', 0)) + chr(10) +
            "Модулей занято: " + str(stats.get('modules_used', 0)) + chr(10) +
            "Групп: " + str(stats.get('groups_count', 0)) + chr(10) +
            "Нагрузка: " + str(stats.get('total_load_watt', 0)) + " Вт"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_del_"):
        panel_id = int(data.replace("panel_del_", ""))
        try:
            p = core_elec_panels.get_panel(panel_id)
            object_id = p.get('object_id') if p else None
            core_elec_panels.delete_panel(panel_id)
        except Exception as e:
            print("panel del: " + str(e), flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "✅ Щит удалён",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щитам", callback_data="panels_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    # --- СОЗДАНИЕ ЩИТА: ШАГ 1 (тип) ---
    if data.startswith("panel_add_type_"):
        parts = data.replace("panel_add_type_", "").rsplit("_", 1)
        object_id = int(parts[0])
        ptype = parts[1]
        context.user_data['panel_new_object_id'] = object_id
        context.user_data['panel_new_type'] = ptype
        context.user_data['waiting_for'] = 'panel_new_name'
        type_labels = {
            'vru': 'ВРУ (вводно-распределительное)',
            'floor': 'Щит этажа',
            'apartment': 'Щит квартиры',
            'outdoor': 'Уличный щит',
        }
        tlabel = type_labels.get(ptype, ptype)
        kb_rows = [
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panels_list_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "⚡ Новый щит: " + tlabel + chr(10) + chr(10) +
                "Напиши название (например «Щит 1 этажа», «ВРУ на столбе»):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_add_"):
        object_id = int(data.replace("panel_add_", ""))
        context.user_data['panel_new_object_id'] = object_id
        kb_rows = [
            [InlineKeyboardButton("🔌 ВРУ (ввод)", callback_data="panel_add_type_" + str(object_id) + "_vru")],
            [InlineKeyboardButton("⚡ Щит этажа", callback_data="panel_add_type_" + str(object_id) + "_floor")],
            [InlineKeyboardButton("🏢 Щит квартиры", callback_data="panel_add_type_" + str(object_id) + "_apartment")],
            [InlineKeyboardButton("🌳 Уличный щит", callback_data="panel_add_type_" + str(object_id) + "_outdoor")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panels_list_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "⚡ Новый щит" + chr(10) + chr(10) + "Выбери тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_"):
        panel_id = int(data.replace("panel_", ""))
        try:
            summary = core_elec_panels.get_panel_summary(panel_id)
        except Exception as e:
            print("panel card: " + str(e), flush=True)
            summary = None
        if not summary:
            try:
                await query.edit_message_text("Щит не найден")
            except Exception:
                pass
            return True
        p = summary['panel']
        ptype = core_elec_panels.get_panel_type_label(p.get('panel_type'))
        mount = core_elec_panels.get_mount_type_label(p.get('mount_type'))
        lines = ["⚡ *" + str(p.get('name') or '?') + "*", ""]
        lines.append("Тип: " + str(ptype))
        lines.append("Монтаж: " + str(mount))
        if p.get('input_breaker'):
            lines.append("Вводной: " + str(p['input_breaker']))
        if p.get('meter_type'):
            lines.append("Счётчик: " + str(p['meter_type']))
        lines.append("")
        lines.append("📋 Групп: " + str(summary['groups_count']))
        lines.append("📊 Нагрузка: " + str(summary['total_load_watt']) + " Вт")
        parent = summary.get('parent')
        if parent:
            lines.append("⬆️ Питается от: " + str(parent.get('name')))
        children = summary.get('children') or []
        if children:
            lines.append("⬇️ Питает: " + ", ".join(c.get('name') or '?' for c in children))
        kb_rows = []
        try:
            _children_count = len(core_elec_panels.get_child_panels(panel_id))
        except Exception:
            _children_count = 0
        if _children_count > 0:
            kb_rows.append([InlineKeyboardButton("⬇️ Дочерние щиты (" + str(_children_count) + ")", callback_data="panel_children_" + str(panel_id))])
        kb_rows.extend([
            [InlineKeyboardButton("🔌 Вводной автомат", callback_data="panel_input_" + str(panel_id))],
            [InlineKeyboardButton("🪄 Автокомплектация", callback_data="panel_auto_" + str(panel_id))],
            [InlineKeyboardButton("📏 Трассы щита", callback_data="panel_routes_" + str(panel_id))],
            [InlineKeyboardButton("🪄 Трассировать все группы", callback_data="panel_routes_auto_" + str(panel_id))],
            [InlineKeyboardButton("🔧 Смета монтажа", callback_data="panel_montage_" + str(panel_id))],
            [InlineKeyboardButton("💰 Общая смета щита", callback_data="panel_total_" + str(panel_id))],
            [InlineKeyboardButton("📄 Спецификация (TXT)", callback_data="panel_spec_" + str(panel_id))],
            [InlineKeyboardButton("📄 PDF-спецификация", callback_data="panel_pdf_" + str(panel_id))],
            [InlineKeyboardButton("📊 Смета (CSV)", callback_data="panel_est_csv_" + str(panel_id))],
            [InlineKeyboardButton("📋 Комплектация", callback_data="panel_comp_" + str(panel_id))],
            [InlineKeyboardButton("📊 Статистика", callback_data="panel_stats_" + str(panel_id))],
            [InlineKeyboardButton("📋 Группы щита", callback_data="panel_groups_" + str(panel_id))],
            [InlineKeyboardButton("🗑 Удалить щит", callback_data="panel_del_" + str(panel_id))],
            [InlineKeyboardButton("⬅️ К щитам", callback_data="panels_list_" + str(p.get('object_id')))],
        ])
        try:
            await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        except Exception as e:
            print("panel card show: " + str(e), flush=True)
        return True

    return False

# === Comm (вынесено в rooms_comm.py) ===
from .rooms_comm import *
from .rooms_comm import _handle_comm_input, _show_comms_list, _show_comm_card, _comm_save_from_context, _comm_save_and_reply

# === Openings (вынесено в rooms_openings.py) ===
from .rooms_openings import *
from .rooms_openings import _handle_opening_input, handle_openings_callback

# === Floors (вынесено в rooms_floors.py) ===
from .rooms_floors import *
from .rooms_floors import _show_floors_list, _show_floor_card
