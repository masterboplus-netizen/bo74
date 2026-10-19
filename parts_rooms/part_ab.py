        state['niche_temp'] = json.loads(draft.get('niche_temp') or '{}')
    except Exception:
        state['niche_temp'] = {}
    try:
        rs = json.loads(draft.get('remaining_steps') or 'null')
        # Сохраняем None как маркер «первый заход», [] как «всё обработано»
        state['remaining_steps'] = rs
    except Exception:
        state['remaining_steps'] = None
    return state['step_name']


def _clear_wall_draft(room_id):
    """Удаляет черновик стены."""
    try:
        db_commit("DELETE FROM wall_drafts WHERE room_id = ?", (room_id,))
    except Exception as e:
        print(f"⚠️ _clear_wall_draft: {e}", flush=True)


# ============================================================
# ХЕЛПЕРЫ
# ============================================================

def _current_wall_pos(context):
    """Текущая позиция стены (строка) из state."""
    state = _get_wall_state(context)
    return core_spec.get_wall_name(state.get('step_num') or 1, core_spec.get_total_walls())


def _wall_flags_list(context):
    """Возвращает список флагов, которые надо обработать после угла.

    ПРАВИЛО:
    - wavy не добавляем, если плоскость УЖЕ пройдена через 3 точки (plane='wavy').
    - Функция НЕ очищает флаги — этим занимается _after_angle.
    """
    state = _get_wall_state(context)
    flags = state.get('flags') or {}
    steps = []
    if flags.get('niche'):
        steps.append('niche')
    if flags.get('rounded'):
        steps.append('rounded')
    if flags.get('wavy') and state.get('plane') != 'wavy':
        steps.append('wavy')
    if flags.get('hidden'):
        steps.append('hidden')
    return steps


def _image_path(filename):
    """Путь к PNG-схеме."""
    if not filename:
        return None
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "docs", "images", filename)


async def _send_png_or_edit(query, caption, kb, png_filename=None):
    """Отправляет фото или редактирует сообщение.

    Если png есть — удаляет старое сообщение, шлёт фото в тот же чат.
    Если png нет — пытается edit, при неудаче — новое сообщение.
    """
    png = _image_path(png_filename)
    chat_id = query.message.chat_id

    if png and os.path.exists(png):
        # Удаляем старое сообщение (в try — может быть уже удалено)
        try:
            await query.message.delete()
        except Exception:
            pass
        # Отправляем фото — ВСЕГДА в chat_id (не через query.message.chat)
        try:
            with open(png, "rb") as f:
                await query.get_bot().send_photo(
                    chat_id=chat_id,
                    photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            return
        except Exception as e:
            print(f"⚠️ send_photo: {e}", flush=True)
        # Fallback — просто текст, тоже через bot
        try:
            await query.get_bot().send_message(
                chat_id=chat_id, text=caption,
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
            return
        except Exception as e:
            print(f"⚠️ send_message fallback: {e}", flush=True)
        return

    # PNG нет — редактируем существующее сообщение.
    # Если это ФОТО — используем edit_message_caption, если текст — edit_message_text.
    msg = query.message
    is_photo = bool(getattr(msg, "photo", None))
    print(f"🟡 _send_png_or_edit (no png): is_photo={is_photo}, caption={caption[:60]!r}", flush=True)

    try:
        if is_photo:
            await query.edit_message_caption(
                caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        else:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        print(f"🟢 _send_png_or_edit (no png): OK", flush=True)
    except Exception as e:
        err = str(e).lower()
        print(f"⚠️ _send_png_or_edit (no png) edit failed: {e}", flush=True)
        if "message is not modified" in err:
            return
        if "message to edit not found" in err or "not found" in err or "query is too old" in err:
            try:
                await query.get_bot().send_message(
                    chat_id=chat_id, text=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
                print(f"🟢 _send_png_or_edit (no png): fallback OK", flush=True)
            except Exception as e2:
                print(f"⚠️ send_message: {e2}", flush=True)


async def _send_png_or_reply(message, caption, kb=None, png_filename=None):
    """Отправляет фото или текстовое сообщение (для update.message)."""
    png = _image_path(png_filename)
    if png and os.path.exists(png):
        try:
            with open(png, "rb") as f:
                await message.reply_photo(
                    photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            return
        except Exception as e:
            print(f"⚠️ reply_photo: {e}", flush=True)
    await message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def rooms_list_keyboard(object_id):
    """Клавиатура списка комнат объекта."""
    rooms = get_rooms(object_id)
    buttons = []
    for r in rooms:
        mark = "🏠" if r.get('is_default') else "📦"
        buttons.append([InlineKeyboardButton(f"{mark} {r['name']}", callback_data=f"room_{r['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить комнату", callback_data=f"room_add_{object_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")])
    return InlineKeyboardMarkup(buttons)


def room_card_keyboard(room_id):
    """Клавиатура карточки комнаты."""
    room = get_room(room_id)
    object_id = room['object_id'] if room else 0
    walls = get_walls_ordered(room_id)
    height_ok = bool(room.get('height_bottom') and room.get('height_middle') and room.get('height_top'))
    walls_ok = len(walls) >= core_spec.get_total_walls()

    if not height_ok and not walls:
        start_btn = InlineKeyboardButton("🚀 Начать замер", callback_data=f"room_start_{room_id}")
    elif height_ok and walls_ok:
        start_btn = InlineKeyboardButton("✅ Замер завершён", callback_data=f"room_start_{room_id}")
    else:
        start_btn = InlineKeyboardButton("▶️ Продолжить замер", callback_data=f"room_start_{room_id}")

    return InlineKeyboardMarkup([
        [start_btn],
        [InlineKeyboardButton("📐 Размеры", callback_data=f"room_measures_{room_id}"),
         InlineKeyboardButton("👁 Что замерено", callback_data=f"room_progress_{room_id}")],
        [InlineKeyboardButton("🚪 Проёмы", callback_data=f"openings_list_{room_id}"),
         InlineKeyboardButton("🔧 Коммуникации", callback_data=f"room_comms_{room_id}")],
        [InlineKeyboardButton("🪑 Мебель", callback_data=f"room_objects_{room_id}")],
        [InlineKeyboardButton("📋 Задачи", callback_data=f"room_tasks_{room_id}"),
         InlineKeyboardButton("📸 Фото", callback_data=f"room_photos_{room_id}")],
        [InlineKeyboardButton("💰 Смета комнаты", callback_data=f"room_estimate_{room_id}")],
        [InlineKeyboardButton("📊 Отчёты", callback_data=f"room_reports_{room_id}"),
         InlineKeyboardButton("📤 Экспорт", callback_data=f"room_export_{room_id}")],
        [InlineKeyboardButton("⚡ Группы ЭОМ", callback_data=f"room_groups_{room_id}")],
        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"room_rename_{room_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"room_del_{room_id}")],
        [InlineKeyboardButton("⬅️ К комнатам", callback_data=f"rooms_list_obj_{object_id}")],
    ])


# ============================================================
# ПОКАЗ КОМНАТ
# ============================================================

async def show_rooms_list(update, context, object_id):
    """Показ списка комнат объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else '—'
    text = f"📦 *Комнаты «{obj_name}»*\n\n{format_rooms_list(object_id)}"
    kb = rooms_list_keyboard(object_id)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            try:
                await update.callback_query.message.delete()
            except Exception:
                pass
            await update.callback_query.message.chat.send_message(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )


async def show_room_card(update, context, room_id):
    """Показ карточки комнаты."""
    room = get_room(room_id)
    if not room:
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Комната не найдена")
        else:
            await update.message.reply_text("❌ Комната не найдена")
        return
    text = format_room_card(room_id)
    kb = room_card_keyboard(room_id)

    if update.callback_query:
        query = update.callback_query
        has_photo = bool(getattr(query.message, "photo", None))
        if has_photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
        else:
            try:
                await query.edit_message_text(
                    text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                if "message is not modified" in str(e).lower():
                    return
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await query.message.chat.send_message(
                    text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
                )
    else:
        await update.message.reply_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )


# ============================================================
# МАСТЕР ВЫСОТЫ (3 точки)
# ============================================================

async def _send_height_scheme(message, context, room_id, step, caption, kb_extra=None):
    """Отправка PNG-схемы высоты."""
    kb_rows = list(kb_extra or [])
    kb_rows.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")])
    kb = InlineKeyboardMarkup(kb_rows)
    png = _image_path(f"height_scheme_step{step}.png")
    if png and os.path.exists(png):
        try:
            with open(png, "rb") as f:
                await message.reply_photo(
                    photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            return
        except Exception as e:
            print(f"⚠️ height scheme: {e}", flush=True)
    await message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_height_step(target, context, room_id, method=None, step=1):
    """Экран шага высоты.

    target — Update или CallbackQuery. Если CallbackQuery — сначала
    пытаемся edit, при неудаче — новое сообщение.
    """
    captions = {
        1: (
            "📏 *Высота — шаг 1*\n\n"
