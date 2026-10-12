"""Старт бота, онбординг, справка."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from db import get_connection
from config import ADMIN_IDS
from handlers.onboarding import ask_role, role_menu_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт: онбординг при первом входе, иначе — меню по роли."""
    user = update.effective_user

    # === DEEP LINK: /start photo_<id> — открыть конкретное фото ===
    if context.args and context.args[0].startswith("photo_"):
        try:
            photo_id = int(context.args[0].replace("photo_", ""))
            from db import get_connection
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT file_id, stage, caption, taken_at, task_id, object_id FROM photos WHERE id = ?", (photo_id,))
            row = c.fetchone()
            conn.close()
            if row:
                stage_names = {'before': '📸 До', 'progress': '🔵 Процесс', 'after': '✅ После', 'document': '📄 Документ'}
                caption_parts = [stage_names.get(row['stage'], row['stage'] or '')]
                if row['taken_at']:
                    caption_parts.append(f"📅 {row['taken_at'][:16]}")
                if row['caption']:
                    caption_parts.append(row['caption'])
                caption = " · ".join([p for p in caption_parts if p])
                await update.message.reply_photo(
                    photo=row['file_id'],
                    caption=caption[:1024] if caption else None
                )
                return
            else:
                await update.message.reply_text("❌ Фото не найдено.")
                return
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
            return

    # === ГЛАВНЫЙ АДМИН — сразу меню, без онбординга ===
    from config import MAIN_ADMIN_TG_ID
    if user.id == MAIN_ADMIN_TG_ID:
        # Сохраняем юзера
        try:
            from modules.users import save_user, set_role, mark_onboarded
            save_user(user.id, user.first_name or "", user.username or "", role="admin")
            set_role(user.id, "admin")
            try:
                mark_onboarded(user.id)
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️ admin save: {e}")

        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я *Бо 7.7* — твой помощник по стройке.\n"
            f"Ты вошёл как *админ*.",
            reply_markup=role_menu_keyboard("admin"),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # === ОБЫЧНЫЕ ЮЗЕРЫ ===
    # Сохраняем/обновляем юзера
    try:
        from modules.users import save_user, get_user
        save_user(user.id, user.first_name or "", user.username or "")
    except Exception as e:
        print(f"⚠️ save_user: {e}")

    # Определяем роль и онбординг
    role = "guest"
    onboarded = False
    try:
        from modules.users import get_user, is_onboarded
        u = get_user(user.id)
        if u:
            role = (u.get("role") if isinstance(u, dict) else u[3]) or "guest"
        onboarded = is_onboarded(user.id)
    except Exception as e:
        print(f"⚠️ get_user: {e}")

    # Первый вход → онбординг
    if not onboarded:
        await ask_role(update, context)
        return

    # Иначе — меню по роли
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я *Бо 7.7* — твой помощник по стройке.\n"
        f"Твоя роль: *{role}*",
        reply_markup=role_menu_keyboard(role),
        parse_mode=ParseMode.MARKDOWN,
    )







def _help_text() -> str:
    """Текст справки (общий для /help и кнопки Помощь)."""
    return (
        "📋 Бо 7.7 — команды и возможности\n\n"
        "🏗️ Объекты\n"
        "• /objects — список объектов кнопками\n"
        "• /add\\_object <название> — создать объект\n\n"
        "📋 Задачи\n"
        "• /tasks — активные задачи кнопками\n"
        "• /add <объект> <задача> — быстро добавить\n"
        "• /add — меню добавления\n"
        "• /done <id> — закрыть задачу\n\n"
        "💰 Финансы\n"
        "• /finance — общая сводка кнопками\n"
        "• /finance <объект> — по объекту\n"
        "• /add\\_expense <объект> <сумма> [категория]\n\n"
        "💸 Личные — через меню\n"
        "📊 Отчёты — через меню\n"
        "📊 KPI — мастер, объекты, красная зона\n"
        "👥 CRM — клиенты, сделки, активности\n\n"
        "📝 Свободный ввод:\n"
        "• «потратил 5000 на материалы Арбат»\n"
        "• «добавь в Арбат положить паркет»\n"
        "• «500» — спросит личный/объект\n\n"
        "⏰ Автоматика:\n"
        "• Дайджест 9:00 МСК\n"
        "• Опрос 18:00 МСК\n"
        "• Автобэкап 23:00 МСК"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_help_text(), parse_mode=ParseMode.MARKDOWN)


