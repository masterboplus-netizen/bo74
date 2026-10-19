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


async def handle_reports_callback(query, context, data):
    """Меню планов и отчётов."""
    if data.startswith("room_total_walls_"):
        parts = data.replace("room_total_walls_", "").split("_")
        try:
            room_id = int(parts[0])
            val = parts[1]
        except (ValueError, IndexError):
            return
        if val == "other":
            context.user_data['waiting_for'] = 'total_walls'
            try:
                await query.edit_message_text(
                    "📐 Введи количество стен (число):",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                    ])
                )
            except Exception:
                pass
            return
        n = int(val)
        core_spec.set_total_walls(n)
        context.user_data['total_walls_asked'] = False
        context.user_data['waiting_for'] = None
        # Продолжаем замер
        try:
            await query.message.chat.send_message(
                "✅ Стён: " + str(n) + chr(10) + "Начинаем обход.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Продолжить", callback_data=f"room_start_{room_id}")],
                ])
            )
        except Exception as e:
            print("total_walls_set: " + str(e), flush=True)
        return

    if data.startswith("room_estimate_"):
        room_id = int(data.replace("room_estimate_", ""))
        from core.room_estimate import format_room_estimate
        text = format_room_estimate(room_id)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + chr(10) + "..."
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    if data.startswith("room_reports_"):
        room_id = int(data.replace("room_reports_", ""))
        room = get_room(room_id)
        name = room.get('name', '?') if room else '?'

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📐 Обмерный план", callback_data=f"room_plan_{room_id}")],
            [InlineKeyboardButton("⚡ Электрика", callback_data=f"room_report_electric_{room_id}")],
            [InlineKeyboardButton("🚿 Сантехника", callback_data=f"room_report_plumbing_{room_id}")],
            [InlineKeyboardButton("🧱 Плитка", callback_data=f"room_report_tiler_{room_id}")],
            [InlineKeyboardButton("🎨 Покраска", callback_data=f"room_report_painter_{room_id}")],
            [InlineKeyboardButton("📋 Ведомость", callback_data=f"room_report_spec_{room_id}")],
            [InlineKeyboardButton("📄 PDF-проект", callback_data=f"room_report_pdf_{room_id}")],
            [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
        ])

        try:
            await query.edit_message_text(
                f"📊 *Планы и отчёты* — «{name}»\n\nВыбери:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
        except Exception:
            pass
        return True

    if data.startswith("room_report_electric_"):
        room_id = int(data.replace("room_report_electric_", ""))
        await _do_report_electric(query, context, room_id)
        return True

    if data.startswith("room_report_plumbing_") or data.startswith("room_report_tiler_") or data.startswith("room_report_painter_") or data.startswith("room_report_spec_") or data.startswith("room_report_pdf_"):
        try:
            room_id = int(data.split("_")[-1])
        except ValueError:
            room_id = 0
        try:
            await query.edit_message_text(
                f"🚧 В разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К отчётам", callback_data=f"room_reports_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    return False


async def _do_report_electric(query, context, room_id):
    """ЭОМ — часть 1: план + таблица точек."""
    from core.comms import get_comms
    from core.rooms import get_room

    room = get_room(room_id)
    name = room.get('name', '?') if room else '?'

    elec_types = {
        'elec_socket': ('🔌', 'Розетки'),
        'elec_switch': ('💡', 'Выключатели'),
        'elec_panel': ('⚡', 'Щит'),
        'elec_cable': ('🔌', 'Выводы света'),
    }

    try:
        comms = get_comms(room_id)
    except Exception:
        comms = []

    groups = {t: [] for t in elec_types}
    for c in comms:
        t = c.get('comm_type')
        if t in elec_types:
            groups[t].append(c)

    lines = [f"⚡ *ЭОМ — Электрика «{name}»*\n"]

    total = 0
    for t, (icon, label) in elec_types.items():
        items = groups[t]
        if not items:
            lines.append(f"{icon} *{label}*: нет")
            continue
        lines.append(f"{icon} *{label}* ({len(items)}):")
        for c in items:
            wall = c.get('wall') or '?'
            ox = c.get('offset_x')
            oy = c.get('offset_y')
            parts = [f"стена «{wall}»"]
            if ox is not None:
                parts.append(f"{int(ox)} см от угла")
            if oy is not None:
                parts.append(f"{int(oy)} см от пола")
            lines.append("  • " + ", ".join(parts))
            total += 1

    lines.append(f"\n📊 *Всего точек: {total}*")
    text = "\n".join(lines)

    if render_room_plan is not None:
        try:
            path = render_room_plan(room_id)
            if path and os.path.exists(path):
                with open(path, "rb") as f:
                    await query.message.chat.send_photo(
                        photo=f,
                        caption=text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("⬅️ К отчётам", callback_data=f"room_reports_{room_id}")],
                        ])
                    )
                return
        except Exception as e:
            print(f"⚠️ _do_report_electric render: {e}", flush=True)

    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К отчётам", callback_data=f"room_reports_{room_id}")],
            ])
        )
    except Exception:
        pass


async def handle_plan_callback(query, context, data):
    """Обработчик плана комнаты."""
    if data.startswith("room_plan_"):
        room_id = int(data.replace("room_plan_", ""))
        await _do_render_plan(query, context, room_id)
        return True
    return False


async def _do_render_plan(query, context, room_id):
    """Рендерит план комнаты и отправляет PNG."""
    if render_room_plan is None:
        try:
            await query.edit_message_text(
                "❌ Модуль визуализации не загружен",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    # Проверка: есть ли замеры
    from core.measures import get_walls_ordered
    try:
        walls = get_walls_ordered(room_id)
    except Exception:
        walls = []
    if not walls:
        try:
            await query.edit_message_text(
                "⚠️ *В комнате нет замеров*\n\n"
                "Сначала пройди мастер замеров.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать замер", callback_data=f"room_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
