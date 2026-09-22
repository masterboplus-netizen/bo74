"""Точка сборки БО 7.5"""
import logging
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import TOKEN, validate_config
from db import init_db
from handlers.onboarding import register_onboarding_handlers
from handlers.admin import register_admin_handlers
from handlers.commands import (
    handle_task_action, handle_add_menu, handle_confirm_date,
    handle_choose_object, handle_category,
    start, help_command, add_object_command, objects_command,
    add_task_command, tasks_command, done_command,
    finance_command, add_expense_command, personal_command, handle_callback, handle_text
)
from handlers.digest_cmd import digest_now_command, survey_now_command
from modules.digest import send_morning_digest, send_evening_survey, send_morning_digest_with_log, send_evening_survey_with_log, catch_up_digests
from modules.backup_db import send_daily_backup, backup_now_command
from datetime import time
from zoneinfo import ZoneInfo

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """Ловит все ошибки в хендлерах и отправляет админу в Telegram."""
    logger.error(f"❌ Ошибка: {context.error}", exc_info=context.error)
    try:
        await context.bot.send_message(
            chat_id=1821030188,
            text=f"⚠️ Ошибка в боте:\n\n{type(context.error).__name__}: {context.error}"
        )
    except Exception:
        pass


def main():
    if not validate_config():
        return
    init_db()

    app = Application.builder().token(TOKEN).build()
    # Настройка постоянного меню команд + дайджестов
    async def post_init(app):
        await app.bot.set_my_commands([
            BotCommand("start", "🏠 Главное меню"),
            BotCommand("objects", "🏗️ Объекты"),
            BotCommand("tasks", "📋 Задачи"),
            BotCommand("finance", "💰 Финансы"),
            BotCommand("add", "➕ Добавить"),
            BotCommand("help", "⚙️ Помощь"),
        ])
        # Утренний дайджест — 9:00 МСК (6:00 UTC)
        app.job_queue.run_daily(
            send_morning_digest_with_log,
            time=time(hour=6, minute=0, tzinfo=ZoneInfo("UTC")),
            name="morning_digest"
        )
        # Вечерний опрос — 18:00 МСК (15:00 UTC)
        app.job_queue.run_daily(
            send_evening_survey_with_log,
            time=time(hour=15, minute=0, tzinfo=ZoneInfo("UTC")),
            name="evening_survey"
        )
        # Автобэкап БД — 23:00 МСК (20:00 UTC)
        app.job_queue.run_daily(
            send_daily_backup,
            time=time(hour=20, minute=0, tzinfo=ZoneInfo("UTC")),
            name="daily_backup"
        )
        logger.info("⏰ Дайджесты: 9:00 и 18:00 МСК, автобэкап БД: 23:00 МСК")

        # Догоняющий дайджест — если бот запущен после 9:00 / 18:00
        try:
            await catch_up_digests(app)
        except Exception as e:
            logger.error(f"⚠️ catch_up_digests: {e}")

    app.post_init = post_init

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add_object", add_object_command))
    app.add_handler(CommandHandler("objects", objects_command))
    app.add_handler(CommandHandler("add", add_task_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("finance", finance_command))
    app.add_handler(CommandHandler("add_expense", add_expense_command))
    app.add_handler(CommandHandler("personal", personal_command))
    app.add_handler(CommandHandler("digest_now", digest_now_command))
    app.add_handler(CommandHandler("survey_now", survey_now_command))
    app.add_handler(CommandHandler("backup_now", backup_now_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_handler(CallbackQueryHandler(handle_category, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(handle_choose_object, pattern="^choose_obj_"))
    app.add_handler(CallbackQueryHandler(handle_confirm_date, pattern="^confirmdate_"))
    app.add_handler(CallbackQueryHandler(handle_add_menu, pattern="^(menu_add|add_object|add_task|add_expense|newtask_obj_|newexp_obj_)"))
    app.add_handler(CallbackQueryHandler(handle_task_action, pattern="^(task_|taskdone_|taskdel_|setdate_|taskdate_|tasknodate_|taskprio_|setprio_|taskrename_)"))
    register_onboarding_handlers(app)
    register_admin_handlers(app)
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(?!cat_|choose_obj_|task_|taskdone_|taskdel_|setdate_|taskdate_|taskprio_|setprio_|taskrename_).*"))

    app.add_error_handler(error_handler)

    logger.info("🚀 БО 7.5 запущен! Все хендлеры зарегистрированы.")
    app.run_polling()


if __name__ == "__main__":
    main()