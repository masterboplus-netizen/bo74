"""Text-хендлеры домена «задачи» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_text).
Блоки: setdate_task, rename_task.

Роутер try_handle(update, context, text) -> bool.
True = обработано, вызывающий делает return.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import get_connection
from handlers.commands.utils import parse_date
from modules.tasks import create_task
from handlers.commands.tasks import auto_confirm_date


async def try_handle(update, context, text: str) -> bool:
    """Обрабатывает text-команды задач. True = обработано."""

    # Обработка ввода даты для задачи
    setdate_task = context.user_data.get('setdate_task')
    if setdate_task:
        d = parse_date(text)
        if d:
            # Сохраняем во временное хранилище, ждём подтверждения
            context.user_data['confirm_date'] = {
                'task_id': setdate_task,
                'date': d.strftime('%Y-%m-%d'),
                'date_str': d.strftime('%d.%m.%Y')
            }
            context.user_data['setdate_task'] = None
            # Получаем задачу
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT t.title, o.name as obj FROM tasks t LEFT JOIN objects o ON t.object_id = o.id WHERE t.id = ?", (setdate_task,))
            row = c.fetchone()
            conn.close()
            title = row['title'] if row else '?'
            obj = row['obj'] if row and row['obj'] else 'Без объекта'
            await update.message.reply_text(
                f"📋 {title}\n{obj}\n\n📅 Дата: {d.strftime('%d.%m.%Y')}\n\nПодтверди:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да", callback_data=f"confirmdate_yes_{setdate_task}_{d.strftime('%Y-%m-%d')}")],
                    [InlineKeyboardButton("❌ Нет", callback_data=f"confirmdate_no_{setdate_task}")],
                ])
            )
            # Автоподтверждение через 30 секунд
            context.job_queue.run_once(
                auto_confirm_date,
                30,
                data={
                    'chat_id': update.effective_chat.id,
                    'task_id': setdate_task,
                    'date': d.strftime('%Y-%m-%d'),
                    'date_str': d.strftime('%d.%m.%Y')
                },
                name=f"confirm_{setdate_task}"
            )
            print(f"⚠️ RETURN на строке 2801", flush=True)
            return True
        else:
            await update.message.reply_text(
                "❌ Не понял дату. Попробуй: «завтра», «20.09», «пн», «+3»"
            )
            print(f"⚠️ RETURN на строке 2806", flush=True)
            return True

    # Обработка переименования задачи
    rename_task = context.user_data.get('rename_task')
    if rename_task:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE tasks SET title = ? WHERE id = ?", (text, rename_task))
        conn.commit()
        conn.close()
        context.user_data['rename_task'] = None
        await update.message.reply_text(f"✅ Задача переименована: «{text}»")
        print(f"⚠️ RETURN на строке 2818", flush=True)
        return True

    # Обработка создания новой задачи
    if context.user_data.get('waiting_for') == 'new_task_text':
        obj = context.user_data.get('pending_task_object')
        if obj:
            tid = create_task(obj['id'], text)
            context.user_data['waiting_for'] = None
            context.user_data['pending_task_object'] = None
            await update.message.reply_text(
                f"✅ Задача «{text}» добавлена в «{obj['name']}»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 К задаче", callback_data=f"task_{tid}")],
                    [InlineKeyboardButton("📋 К задачам", callback_data="menu_tasks")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
            print(f"⚠️ RETURN на строке 2660", flush=True)
            return True


    return False
