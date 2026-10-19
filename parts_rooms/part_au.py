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

def _build_panel_total_text(panel_id):
    """Текст общей сметы щита: компоненты + монтаж."""
    from core.elec_panels import get_panel, calc_panel_cost, get_groups_by_panel
    from core import elec_routes as er

    p = get_panel(panel_id)
    if not p:
        return "Щит не найден"

    # Компоненты
    panels_cost = calc_panel_cost(panel_id)

    # Монтаж
    montage_cost = 0.0
    montage_m = 0.0
    try:
        montage = er.calc_montage_cost_by_panel(panel_id)
        montage_cost = montage['total']
        montage_m = montage['total_m']
    except Exception as e:
        print("montage cost: " + str(e), flush=True)

    total = panels_cost + montage_cost

    lines = [
        "💰 Общая смета щита «" + str(p.get('name') or '?') + "»",
        "",
        "── ЩИТ ──",
        "Компоненты щита: " + str(panels_cost) + " ₽",
        "",
        "── ЭЛЕКТРОМОНТАЖ ──",
        "Метраж: " + str(montage_m) + " м",
        "Кабель + расходники: " + str(montage_cost) + " ₽",
        "",
        "───────────────────────",
        "💰 ВСЕГО: " + str(round(total, 2)) + " ₽",
    ]
    return chr(10).join(lines)




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
