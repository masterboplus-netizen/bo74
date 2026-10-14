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

# === my_tasks : мои задачи ===
    if data == "my_tasks":
        from modules.tasks import get_tasks_by_assignee
        user_id = query.from_user.id
        my = get_tasks_by_assignee(user_id)
        if not my:
            await query.edit_message_text(
                "👤 У тебя нет назначенных задач.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data="menu_tasks")],
                ])
            )
            return True
        text = f"👤 МОИ ЗАДАЧИ ({len(my)}):\n\n"
        buttons = []
        for i, t in enumerate(my[:20], start=1):
            d = ''
            if t['deadline']:
                d = f" ({t['deadline'][:10]})"
            obj = t['object_name'] or 'без объекта'
            text += f"#{t['id']} {t['title']}{d} — {obj}\n"
            buttons.append([InlineKeyboardButton(f"{i}. {t['title'][:40]}", callback_data=f"task_{t['id']}")])
        buttons.append([InlineKeyboardButton("⬅️ К задачам", callback_data="menu_tasks")])
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return True

    # === by_assignee : список исполнителей ===
    if data == "by_assignee":
        from modules.users import get_all_users
        from modules.tasks import get_tasks_by_assignee
        users = get_all_users()
        users = [u for u in users if u.get('role') in ('master', 'prorab', 'designer')]
        buttons = []
        for u in users:
            cnt = len(get_tasks_by_assignee(u['tg_id']))
            label = f"👤 {u.get('name', '-')[:30]} ({cnt})"
            buttons.append([InlineKeyboardButton(label, callback_data=f"byassigned_{u['tg_id']}")])
        buttons.append([InlineKeyboardButton("⬅️ К задачам", callback_data="menu_tasks")])
        try:
            await query.edit_message_text(
                "👥 Задачи по исполнителям:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return True

    # === byassigned_* : задачи конкретного исполнителя ===
    if data.startswith("byassigned_"):
        from modules.tasks import get_tasks_by_assignee
        try:
            user_id = int(data.replace("byassigned_", ""))
        except ValueError:
            return True
        tasks = get_tasks_by_assignee(user_id)
        # Найти имя
        from modules.users import get_user
        u = None
        try:
            u = get_user(user_id)
        except Exception:
            pass
        uname = u.get('name', '?') if u else str(user_id)
        if not tasks:
            try:
                await query.edit_message_text(
                    f"👤 {uname}\n\nНет активных задач.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data="by_assignee")],
                    ])
                )
            except Exception as e:
                if 'not modified' not in str(e).lower():
                    raise
            return True
        text = f"👤 {uname} — {len(tasks)} задач:\n\n"
        buttons = []
        for i, t in enumerate(tasks[:20], start=1):
            d = ''
            if t['deadline']:
                d = f" ({t['deadline'][:10]})"
            obj = t['object_name'] or 'без объекта'
            text += f"#{t['id']} {t['title']}{d} — {obj}\n"
            buttons.append([InlineKeyboardButton(f"{i}. {t['title'][:40]}", callback_data=f"task_{t['id']}")])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="by_assignee")])
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return True

    return False
