        return

    try:
        path = render_room_plan(room_id)
        if not path or not os.path.exists(path):
            raise Exception("PNG не создан")

        room = get_room(room_id)
        name = room.get('name', f'Комната {room_id}') if room else f'Комната {room_id}'
        with open(path, "rb") as f:
            await query.message.chat.send_photo(
                photo=f,
                caption=f"🧊 *План комнаты* «{name}»",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Обновить", callback_data=f"room_plan_{room_id}")],
                    [InlineKeyboardButton("📤 Экспорт", callback_data=f"room_export_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
    except Exception as e:
        print(f"⚠️ _do_render_plan: {e}", flush=True)
        try:
            await query.edit_message_text(
                f"❌ Ошибка рендера: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 Попробовать", callback_data=f"room_plan_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass


# ============================================================
# ЭКСПОРТ КОМНАТЫ
# ============================================================

async def handle_export_callback(query, context, data):
    """Обработчик экспорта."""
    # --- Специфичные форматы (СНАЧАЛА!) ---
    if data.startswith("room_export_dxf_"):
        room_id = int(data.replace("room_export_dxf_", ""))
        await _do_export_dxf(query, context, room_id)
        return True

    if data.startswith("room_export_json_"):
        room_id = int(data.replace("room_export_json_", ""))
        await _do_export_json(query, context, room_id)
        return True

    if data.startswith("room_export_csv_"):
        room_id = int(data.replace("room_export_csv_", ""))
        await _do_export_csv(query, context, room_id)
        return True

    if data.startswith("room_export_pdf_"):
        suffix = data.split("_")[-1]
        try:
            rid = int(suffix)
        except ValueError:
            rid = 0
        try:
            await query.edit_message_text(
                "🚧 PDF в разработке. Пока доступны DXF, JSON, CSV.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_export_{rid}")],
                ])
            )
        except Exception:
            pass
        return True

    # --- Общий вызов меню: room_export_<id> (только если id — цифры) ---
    if data.startswith("room_export_"):
        suffix = data.replace("room_export_", "")
        if suffix.isdigit():
            room_id = int(suffix)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 DXF (CAD)", callback_data=f"room_export_dxf_{room_id}")],
                [InlineKeyboardButton("📦 JSON (данные)", callback_data=f"room_export_json_{room_id}")],
                [InlineKeyboardButton("📄 PDF (отчёт)", callback_data=f"room_export_pdf_{room_id}")],
                [InlineKeyboardButton("📊 CSV (смета)", callback_data=f"room_export_csv_{room_id}")],
                [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
            ])
            try:
                await query.edit_message_text(
                    "📤 *Экспорт комнаты*\n\nВыбери формат:",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            except Exception:
                pass
            return True

    return False



async def _do_export_dxf(query, context, room_id):
    """Генерирует DXF и отправляет."""
    kb_err = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Попробовать снова", callback_data=f"room_export_dxf_{room_id}")],
        [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
    ])

    if save_dxf is None:
        try:
            await query.edit_message_text(
                "❌ Модуль DXF не загружен",
                reply_markup=kb_err
            )
        except Exception:
            pass
        return

    # --- Проверка: есть ли замеры? ---
    from core.measures import get_walls_ordered
    try:
        walls = get_walls_ordered(room_id)
    except Exception:
        walls = []
    if not walls:
        try:
            await query.edit_message_text(
                "⚠️ *В комнате нет замеров*\n\n"
                "Сначала пройди мастер замеров: высота + обход стен.\n"
                "После этого DXF будет содержать контур комнаты.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать замер", callback_data=f"room_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    try:
        # Правильный путь — используем os.path
        import tempfile
        tmp_dir = tempfile.gettempdir()
        target_path = os.path.join(tmp_dir, f"export_room_{room_id}.dxf")
        path = save_dxf(room_id, path=target_path)
        if not path or not os.path.exists(path):
            # Fallback — дефолтный путь от save_dxf
            path = save_dxf(room_id)
        if not path or not os.path.exists(path):
            raise Exception(f"Файл не создан (save_dxf вернул {path})")

        room = get_room(room_id)
        name = room.get('name', f'room_{room_id}') if room else f'room_{room_id}'
        with open(path, "rb") as f:
            await query.message.chat.send_document(
                document=f,
                filename=f"{name}.dxf",
                caption=f"📐 DXF-экспорт комнаты «{name}»\n\nОткрой в: SketchUp, ArchiCAD, AutoCAD",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
    except Exception as e:
        print(f"⚠️ _do_export_dxf: {e}", flush=True)
        try:
            await query.edit_message_text(
                f"❌ Ошибка DXF: {e}",
                reply_markup=kb_err
            )
        except Exception:
            pass


async def _do_export_csv(query, context, room_id):
    """Генерирует CSV и отправляет."""
    if save_csv is None:
        try:
            await query.edit_message_text("❌ Модуль CSV не загружен")
        except Exception:
            pass
        return
    try:
        import tempfile
        tmp_dir = tempfile.gettempdir()
        target_path = os.path.join(tmp_dir, f"export_room_{room_id}.csv")
        path = save_csv(room_id, path=target_path)
        if not path or not os.path.exists(path):
            path = save_csv(room_id)
        if not path or not os.path.exists(path):
            raise Exception("Файл не создан")
        room = get_room(room_id)
        name = room.get('name', f'room_{room_id}') if room else f'room_{room_id}'
        with open(path, "rb") as f:
            await query.message.chat.send_document(
                document=f,
                filename=f"{name}.csv",
                caption=f"📊 CSV-экспорт комнаты «{name}»\n\nОткрой в Excel или Google Sheets",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
    except Exception as e:
        print(f"⚠️ _do_export_csv: {e}", flush=True)
        try:
            await query.edit_message_text(
                f"❌ Ошибка CSV: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 Попробовать снова", callback_data=f"room_export_csv_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass


async def _do_export_json(query, context, room_id):
    """Генерирует JSON и отправляет."""
    # --- Проверка: есть ли замеры? ---
    from core.measures import get_walls_ordered
    try:
        walls = get_walls_ordered(room_id)
    except Exception:
        walls = []
    if not walls:
        try:
            await query.edit_message_text(
                "⚠️ *В комнате нет замеров*\n\n"
                "Сначала пройди мастер замеров.\nJSON будет содержать пустую модель.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать замер", callback_data=f"room_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    if save_json is None:
        try:
            await query.edit_message_text("❌ Модуль JSON не загружен")
        except Exception:
            pass
        return

    try:
        import tempfile
        tmp_dir = tempfile.gettempdir()
        target_path = os.path.join(tmp_dir, f"export_room_{room_id}.json")
        path = save_json(room_id, path=target_path)
        if not path or not os.path.exists(path):
            path = save_json(room_id)
        if not path or not os.path.exists(path):
            raise Exception("Файл не создан")
        room = get_room(room_id)
        name = room.get('name', f'room_{room_id}') if room else f'room_{room_id}'
        with open(path, "rb") as f:
            await query.message.chat.send_document(
                document=f,
                filename=f"{name}.json",
                caption=f"📦 JSON-экспорт комнаты «{name}»\n\nЦифровой двойник: геометрия + замеры + проёмы + ниши",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
    except Exception as e:
        print(f"⚠️ _do_export_json: {e}", flush=True)
        try:
            await query.edit_message_text(
                f"❌ Ошибка JSON: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 Попробовать снова", callback_data=f"room_export_json_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass


# ============================================================
# ГЛАВНЫЙ РОУТЕР CALLBACK'ОВ
# ============================================================

async def handle_rooms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер всех callback'ов комнат."""
    query = update.callback_query
    print(f"🔴 HANDLE_ROOMS_CALLBACK ВЫЗВАН: {query.data!r}", flush=True)
    await query.answer()
    data = query.data
    print(f"🔍 ROOMS: data={data!r}", flush=True)

    # ─── УНИВЕРСАЛЬНОЕ ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ───
    import re as _re_del
    _m_del = _re_del.match(r"^(room|works|plumb|plumb_route|panel_comp|panel|comm|opening)_del_(\d+)$", data)
    if _m_del:
        _prefix = _m_del.group(1)
        _item_id = int(_m_del.group(2))
        _spec = None
        try:
            if _prefix == "room":
                from core import rooms as core_rooms_mod ; _o = core_rooms_mod.get_room(_item_id)
                if _o:
