"""Callbacks домена «Задачи» — вынесено из _legacy.py (сессия 16).

Функция try_handle() возвращает True, если callback обработан.
Иначе — False, и _legacy.handle_callback идёт дальше.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode


async def try_handle(data: str, query, context) -> bool:
    """Обработка callback'ов домена Задачи.
    Возвращает True если обработано, False если не наш домен."""

    if data == "tasks_byobj":
        from handlers.commands.tasks import tasks_keyboard_by_object
        try:
            await query.edit_message_text(
                "🏗️ Задачи по объектам:\n\nВыбери объект:",
                reply_markup=tasks_keyboard_by_object()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"tasks_byobj: {_e}", flush=True)
        return True

    if data == "tasks_archive_list":
        try:
            from modules import tasks as _t_arch
            _arch = _t_arch.get_archived_tasks()
        except Exception as _e:
            print("archive list fail: " + str(_e), flush=True)
            _arch = []
        if not _arch:
            try:
                await query.edit_message_text(
                    "🗑 Архив пуст.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К задачам", callback_data="menu_tasks")]])
                )
            except Exception:
                pass
            return True
        kb = []
        for _a in _arch[:30]:
            _t = (_a.get("title") or "?")[:40]
            _tid = _a["id"]
            kb.append([InlineKeyboardButton("🗑 " + _t, callback_data=f"task_{_tid}")])
        kb.append([InlineKeyboardButton("⬅️ К задачам", callback_data="menu_tasks")])
        try:
            await query.edit_message_text(
                "🗑 *Архив задач (" + str(len(_arch)) + ")*\n\nУдалённые задачи (хранятся 60 дней):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception:
            pass
        return True

    if data == "menu_back":
        from handlers.commands.keyboards import main_menu_keyboard
        await query.edit_message_text(
            "🏠 **Главное меню**",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return True

    return False
