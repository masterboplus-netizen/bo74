"""Фото: команда, батчи, фильтры, привязка к задаче, сохранение."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from db import get_connection
from modules.objects import get_object, get_all_objects
from modules.tasks import get_tasks_by_object


async def photos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/photos <объект> — все фото по объекту, с группировкой по этапам."""

    # Определяем объект
    if context.args:
        obj = get_object_by_name(' '.join(context.args))
        if not obj:
            await update.message.reply_text(
                f"❌ Объект «{' '.join(context.args)}» не найден"
            )
            return
    else:
        await update.message.reply_text(
            "❌ Использование: /photos <объект>\n"
            "Пример: /photos Переделкино"
        )
        return

    # Достаём фото
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.file_id, p.stage, p.caption, p.taken_at, p.created_at,
               p.task_id, t.title as task_title
        FROM photos p
        LEFT JOIN tasks t ON p.task_id = t.id
        WHERE p.object_id = ?
        ORDER BY p.stage, p.taken_at DESC
    """, (obj['id'],))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text(
            f"📸 По объекту «{obj['name']}» фото нет.\n\n"
            f"Отправь фото боту, чтобы добавить."
        )
        return

    # Группируем по этапам
    stage_names = {
        'before': '📸 До',
        'progress': '🔵 Процесс',
        'after': '✅ После',
        'document': '📄 Документы',
    }
    by_stage = {}
    for r in rows:
        st = r['stage'] or 'progress'
        by_stage.setdefault(st, []).append(r)

    # Заголовок
    text = f"📸 Фото по объекту «{obj['name']}»\n"
    text += f"Всего: {len(rows)}\n\n"
    for st, items in by_stage.items():
        text += f"{stage_names.get(st, st)}: {len(items)}\n"

    await update.message.reply_text(text)

    # Отправляем фото (максимум 20)
    count = 0
    for st, items in by_stage.items():
        for r in items:
            if count >= 20:
                break
            caption_parts = [stage_names.get(st, st)]
            if r['task_title']:
                caption_parts.append(f"#{r['task_id']} {r['task_title'][:40]}")
            if r['caption']:
                caption_parts.append(r['caption'])
            if r['taken_at']:
                caption_parts.append(f"📅 {r['taken_at'][:10]}")
            caption = " · ".join(caption_parts)

            try:
                await update.message.reply_photo(
                    photo=r['file_id'],
                    caption=caption[:1024]
                )
                count += 1
            except Exception as e:
                # Если file_id устарел — сообщаем
                await update.message.reply_text(f"⚠️ Не смог отправить фото #{r['id']}: {e}")

        if count >= 20:
            break

    if len(rows) > 20:
        await update.message.reply_text(
            f"... (показаны первые 20 из {len(rows)})"
        )


# === ФИЛЬТРЫ ФОТО ===

async def _show_photos_batch(update, context, photos, page=0, header="📸 Фото"):
    """Показывает по 3 фото, с кнопкой 'Показать ещё'."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    BATCH = 3
    start = page * BATCH
    end = start + BATCH
    batch = photos[start:end]

    stage_names = {'before': '📸 До', 'progress': '🔵 Процесс', 'after': '✅ После', 'document': '📄 Документ'}
    for r in batch:
        caption_parts = [stage_names.get(r['stage'], r['stage'] or '')]
        if r.get('task_title'):
            caption_parts.append(f"#{r['task_id']} {r['task_title'][:40]}")
        if r.get('caption'):
            caption_parts.append(r['caption'])
        if r.get('taken_at'):
            caption_parts.append(f"📅 {r['taken_at'][:10]}")
        caption = " · ".join([p for p in caption_parts if p])
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=r['file_id'],
                caption=caption[:1024]
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Не смог отправить фото #{r.get('id', '?')}: {e}"
            )

    # Кнопка «Показать ещё»
    buttons = []
    if end < len(photos):
        buttons.append([InlineKeyboardButton(
            f"⬇️ Показать ещё (осталось {len(photos) - end})",
            callback_data=f"photopage_{context.user_data.get('photo_filter_key', '')}_{page + 1}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=context.user_data.get('photo_back', 'menu_back'))])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{header}\nПоказано {min(end, len(photos))} из {len(photos)}",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
    )


async def handle_photo_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех фильтров фото."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Формат: photofilt_<тип>_<obj_id>_<доп>
    parts = data.replace("photofilt_", "").split("_")
    ftype = parts[0]
    obj_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    extra = parts[2] if len(parts) > 2 else None

    obj = get_object(obj_id) if obj_id else None
    obj_name = obj['name'] if obj else '—'

    conn = get_connection()
    c = conn.cursor()

    if ftype == "last":
        # Последние 3 задачи с фото
        c.execute("""
            SELECT DISTINCT p.task_id
            FROM photos p
            WHERE p.object_id = ? AND p.task_id IS NOT NULL
            ORDER BY p.taken_at DESC
            LIMIT 3
        """, (obj_id,))
        task_ids = [r[0] for r in c.fetchall()]
        if not task_ids:
            conn.close()
            await query.edit_message_text(
                f"📸 Последние фото «{obj_name}»\n\nЗадач с фото нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"objphotos_{obj_id}")]
                ])
            )
            return
        placeholders = ",".join("?" * len(task_ids))
        c.execute(f"""
            SELECT p.id, p.file_id, p.stage, p.caption, p.taken_at, p.task_id,
                   t.title as task_title
            FROM photos p
            LEFT JOIN tasks t ON p.task_id = t.id
            WHERE p.object_id = ? AND p.task_id IN ({placeholders})
            ORDER BY p.taken_at DESC
        """, [obj_id] + task_ids)
        photos = [dict(r) for r in c.fetchall()]
        conn.close()
        context.user_data['photo_filter_key'] = f"last_{obj_id}"
        context.user_data['photo_back'] = f"objphotos_{obj_id}"
        context.user_data['photo_cache'] = photos
        await query.edit_message_text(
            f"🆕 Последние фото «{obj_name}»\n({len(task_ids)} задач, {len(photos)} фото)"
        )
        await _show_photos_batch(update, context, photos, page=0, header=f"🆕 Последние фото «{obj_name}»")
        return

    if ftype == "tasks":
        c.execute("""
            SELECT t.id, t.title, COUNT(p.id) as cnt
            FROM tasks t
            JOIN photos p ON p.task_id = t.id
            WHERE p.object_id = ?
            GROUP BY t.id, t.title
            ORDER BY MAX(p.taken_at) DESC
        """, (obj_id,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            await query.edit_message_text(
                f"📸 Задачи с фото «{obj_name}»\n\nПока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"objphotos_{obj_id}")]
                ])
            )
            return
        buttons = []
        for r in rows[:25]:
            buttons.append([InlineKeyboardButton(
                f"#{r['id']} {r['title'][:35]} ({r['cnt']})",
                callback_data=f"photofilt_task_{obj_id}_{r['id']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"objphotos_{obj_id}")])
        await query.edit_message_text(
            f"📋 Задачи с фото «{obj_name}»\n\nВыбери задачу:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if ftype == "task":
        task_id = int(extra) if extra else 0
        c.execute("""
            SELECT p.id, p.file_id, p.stage, p.caption, p.taken_at, p.task_id,
                   t.title as task_title
            FROM photos p
            LEFT JOIN tasks t ON p.task_id = t.id
            WHERE p.object_id = ? AND p.task_id = ?
            ORDER BY p.taken_at DESC
        """, (obj_id, task_id))
        photos = [dict(r) for r in c.fetchall()]
        conn.close()
        context.user_data['photo_filter_key'] = f"task_{obj_id}_{task_id}"
        context.user_data['photo_back'] = f"photofilt_tasks_{obj_id}"
        context.user_data['photo_cache'] = photos
        title = photos[0]['task_title'] if photos else f"#{task_id}"
        await query.edit_message_text(f"📋 Фото задачи #{task_id} «{title}»\nВсего: {len(photos)}")
        await _show_photos_batch(update, context, photos, page=0, header=f"📋 Фото задачи #{task_id}")
        return

    if ftype == "dates":
        c.execute("""
            SELECT DATE(p.taken_at) as d, COUNT(*) as cnt
            FROM photos p
            WHERE p.object_id = ?
            GROUP BY DATE(p.taken_at)
            ORDER BY d DESC
        """, (obj_id,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            await query.edit_message_text(
                f"📸 Даты с фото «{obj_name}»\n\nПока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"objphotos_{obj_id}")]
                ])
            )
            return
        buttons = []
        for r in rows[:25]:
            buttons.append([InlineKeyboardButton(
                f"📅 {r['d']} ({r['cnt']})",
                callback_data=f"photofilt_date_{obj_id}_{r['d']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"objphotos_{obj_id}")])
        await query.edit_message_text(
            f"📅 Фото «{obj_name}» по датам:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if ftype == "date":
        date_str = extra or ''
        c.execute("""
            SELECT p.id, p.file_id, p.stage, p.caption, p.taken_at, p.task_id,
                   t.title as task_title
            FROM photos p
            LEFT JOIN tasks t ON p.task_id = t.id
            WHERE p.object_id = ? AND DATE(p.taken_at) = ?
            ORDER BY p.taken_at DESC
        """, (obj_id, date_str))
        photos = [dict(r) for r in c.fetchall()]
        conn.close()
        context.user_data['photo_filter_key'] = f"date_{obj_id}_{date_str}"
        context.user_data['photo_back'] = f"photofilt_dates_{obj_id}"
        context.user_data['photo_cache'] = photos
        await query.edit_message_text(f"📅 Фото за {date_str}\nВсего: {len(photos)}")
        await _show_photos_batch(update, context, photos, page=0, header=f"📅 Фото за {date_str}")
        return

    if ftype == "uploaders":
        c.execute("""
            SELECT p.uploaded_by, COUNT(*) as cnt, u.name
            FROM photos p
            LEFT JOIN users u ON u.tg_id = p.uploaded_by
            WHERE p.object_id = ?
            GROUP BY p.uploaded_by
            ORDER BY cnt DESC
        """, (obj_id,))
        rows = c.fetchall()
        conn.close()
        buttons = []
        for r in rows[:25]:
            name = r['name'] or f"id{r['uploaded_by']}"
            buttons.append([InlineKeyboardButton(
                f"👤 {name} ({r['cnt']})",
                callback_data=f"photofilt_upl_{obj_id}_{r['uploaded_by']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"objphotos_{obj_id}")])
        await query.edit_message_text(
            f"👤 Кто загрузил фото «{obj_name}»:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if ftype == "upl":
        tg_id = int(extra) if extra else 0
        c.execute("""
            SELECT p.id, p.file_id, p.stage, p.caption, p.taken_at, p.task_id,
                   t.title as task_title
            FROM photos p
            LEFT JOIN tasks t ON p.task_id = t.id
            WHERE p.object_id = ? AND p.uploaded_by = ?
            ORDER BY p.taken_at DESC
        """, (obj_id, tg_id))
        photos = [dict(r) for r in c.fetchall()]
        c.execute("SELECT name FROM users WHERE tg_id = ?", (tg_id,))
        u = c.fetchone()
        conn.close()
        name = u['name'] if u else f"id{tg_id}"
        context.user_data['photo_filter_key'] = f"upl_{obj_id}_{tg_id}"
        context.user_data['photo_back'] = f"photofilt_uploaders_{obj_id}"
        context.user_data['photo_cache'] = photos
        await query.edit_message_text(f"👤 Фото от {name}\nВсего: {len(photos)}")
        await _show_photos_batch(update, context, photos, page=0, header=f"👤 Фото от {name}")
        return

    if ftype == "assignees":
        c.execute("""
            SELECT t.assigned_to, COUNT(p.id) as cnt, u.name
            FROM photos p
            JOIN tasks t ON p.task_id = t.id
            LEFT JOIN users u ON u.tg_id = t.assigned_to
            WHERE p.object_id = ? AND t.assigned_to IS NOT NULL
            GROUP BY t.assigned_to
            ORDER BY cnt DESC
        """, (obj_id,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            await query.edit_message_text(
                f"🛠 Фото «{obj_name}» по исполнителям\n\n"
                f"Ни одна задача не назначена на исполнителя.\n"
                f"Пока все фото — без исполнителя.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"objphotos_{obj_id}")]
                ])
            )
            return
        buttons = []
        for r in rows[:25]:
            name = r['name'] or f"id{r['assigned_to']}"
            buttons.append([InlineKeyboardButton(
                f"🛠 {name} ({r['cnt']})",
                callback_data=f"photofilt_asgn_{obj_id}_{r['assigned_to']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"objphotos_{obj_id}")])
        await query.edit_message_text(
            f"🛠 Кто делал задачи «{obj_name}»:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if ftype == "asgn":
        tg_id = int(extra) if extra else 0
        c.execute("""
            SELECT p.id, p.file_id, p.stage, p.caption, p.taken_at, p.task_id,
                   t.title as task_title
            FROM photos p
            JOIN tasks t ON p.task_id = t.id
            WHERE p.object_id = ? AND t.assigned_to = ?
            ORDER BY p.taken_at DESC
        """, (obj_id, tg_id))
        photos = [dict(r) for r in c.fetchall()]
        c.execute("SELECT name FROM users WHERE tg_id = ?", (tg_id,))
        u = c.fetchone()
        conn.close()
        name = u['name'] if u else f"id{tg_id}"
        context.user_data['photo_filter_key'] = f"asgn_{obj_id}_{tg_id}"
        context.user_data['photo_back'] = f"photofilt_assignees_{obj_id}"
        context.user_data['photo_cache'] = photos
        await query.edit_message_text(f"🛠 Фото по задачам от {name}\nВсего: {len(photos)}")
        await _show_photos_batch(update, context, photos, page=0, header=f"🛠 Фото от {name}")
        return

    conn.close()
    await query.edit_message_text(f"🤔 Неизвестный фильтр: {ftype}")


async def handle_photo_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пагинация: показать ещё 3 фото."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if not data.startswith("photopage_"):
        return
    # photopage_<filter_key>_<page>
    parts = data.replace("photopage_", "").rsplit("_", 1)
    page = int(parts[1]) if len(parts) > 1 else 0
    photos = context.user_data.get('photo_cache', [])
    if not photos:
        await query.edit_message_text("❌ Фото потерялись. Открой заново.")
        return
    await _show_photos_batch(update, context, photos, page=page, header="📸 Ещё фото")


# === ОБРАБОТКА ФОТО ===

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ловит фото от пользователя. Если есть photo_for_task — привязываем к задаче. Иначе — стандартный выбор."""
    photo = update.message.photo[-1]
    file_id = photo.file_id

    # === СЦЕНАРИЙ 1: ждали фото для конкретной задачи (после /done) ===
    pft = context.user_data.get('photo_for_task')
    if pft and pft.get('task_id'):
        from datetime import datetime
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """INSERT INTO photos (object_id, task_id, file_id, caption, stage, uploaded_by, taken_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                pft.get('object_id'),
                pft['task_id'],
                file_id,
                update.message.caption or '',
                'after',
                update.effective_user.id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            )
        )
        conn.commit()
        conn.close()
        context.user_data['photo_for_task'] = None

        await update.message.reply_text(
            f"✅ Фото сохранено для задачи #{pft['task_id']} (этап: После)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 К задачам", callback_data="menu_tasks")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    # === СЦЕНАРИЙ 2: обычная загрузка (выбор объекта → этап → задача) ===
    context.user_data['pending_photo'] = {
        'file_id': file_id,
        'caption': update.message.caption or '',
    }

    objs = get_all_objects()
    if not objs:
        await update.message.reply_text("❌ Нет объектов. Сначала создай объект.")
        return

    buttons = []
    for o in objs[:20]:
        buttons.append([InlineKeyboardButton(
            f"🏗️ {o['name']}",
            callback_data=f"photo_obj_{o['id']}"
        )])
    buttons.append([InlineKeyboardButton("💳 Распознать чек (OCR)", callback_data="recognize_receipt")])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="menu_back")])

    await update.message.reply_text(
        "📸 Фото получено.\n\nВыбери объект или распознай чек:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_photo_stage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор этапа фото."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("photo_obj_"):
        return
    obj_id = int(data.replace("photo_obj_", ""))

    pending = context.user_data.get('pending_photo', {})
    if not pending or 'file_id' not in pending:
        await query.edit_message_text("❌ Фото потерялось. Пришли заново.")
        return

    pending['object_id'] = obj_id
    context.user_data['pending_photo'] = pending

    await query.edit_message_text(
        "📸 Выбери этап:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 До (before)", callback_data="photo_stage_before")],
            [InlineKeyboardButton("🔵 Процесс (progress)", callback_data="photo_stage_progress")],
            [InlineKeyboardButton("✅ После (after)", callback_data="photo_stage_after")],
            [InlineKeyboardButton("📄 Документ", callback_data="photo_stage_document")],
            [InlineKeyboardButton("❌ Отмена", callback_data="menu_back")],
        ])
    )


async def handle_photo_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор задачи после этапа."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("photo_stage_"):
        return
    stage = data.replace("photo_stage_", "")

    pending = context.user_data.get('pending_photo', {})
    if not pending or 'file_id' not in pending:
        await query.edit_message_text("❌ Фото потерялось. Пришли заново.")
        return

    pending['stage'] = stage
    context.user_data['pending_photo'] = pending

    # Показываем задачи объекта + «Без задачи»
    obj_id = pending.get('object_id')
    tasks = get_tasks_by_object(obj_id) if obj_id else []
    open_tasks = [t for t in tasks if t['status'] in ('open', 'in_progress')]

    buttons = [[InlineKeyboardButton("📌 Без задачи", callback_data="photo_task_none")]]
    for t in open_tasks[:15]:
        buttons.append([InlineKeyboardButton(
            f"#{t['id']} {t['title'][:35]}",
            callback_data=f"photo_task_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="menu_back")])

    await query.edit_message_text(
        "📸 К какой задаче привязать?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_photo_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет фото в БД."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("photo_task_"):
        return
    task_part = data.replace("photo_task_", "")
    task_id = None if task_part == "none" else int(task_part)

    pending = context.user_data.get('pending_photo', {})
    if not pending or 'file_id' not in pending:
        await query.edit_message_text("❌ Фото потерялось. Пришли заново.")
        return

    # Сохраняем в БД
    from datetime import datetime
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO photos (object_id, task_id, file_id, caption, stage, uploaded_by, taken_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            pending.get('object_id'),
            task_id,
            pending['file_id'],
            pending.get('caption', ''),
            pending.get('stage', 'progress'),
            update.effective_user.id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
    )
    photo_id = c.lastrowid
    conn.commit()
    conn.close()

    obj = get_object(pending.get('object_id')) if pending.get('object_id') else None
    obj_name = obj['name'] if obj else '—'
    stage_names = {'before': '📸 До', 'progress': '🔵 Процесс', 'after': '✅ После', 'document': '📄 Документ'}

    context.user_data['pending_photo'] = None

    await query.edit_message_text(
        f"✅ Фото сохранено!\n\n"
        f"🏗️ Объект: {obj_name}\n"
        f"📊 Этап: {stage_names.get(pending.get('stage'), pending.get('stage'))}\n"
        f"📋 Задача: #{task_id}" if task_id else
        f"✅ Фото сохранено!\n\n"
        f"🏗️ Объект: {obj_name}\n"
        f"📊 Этап: {stage_names.get(pending.get('stage'), pending.get('stage'))}\n"
        f"📋 Без задачи",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏗️ К объекту", callback_data=f"obj_{pending.get('object_id')}")],
            [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
        ])
    )


