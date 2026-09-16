"""Точка сборки БО 7.2"""
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import TOKEN, validate_config
from db import init_db
from handlers.commands import (
    handle_task_action, handle_confirm_date,
    handle_choose_object, handle_category,
    start, help_command, add_object_command, objects_command,
    add_task_command, tasks_command, done_command,
    finance_command, add_expense_command, handle_callback, handle_text
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    if not validate_config():
        return
    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add_object", add_object_command))
    app.add_handler(CommandHandler("objects", objects_command))
    app.add_handler(CommandHandler("add", add_task_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("finance", finance_command))
    app.add_handler(CommandHandler("add_expense", add_expense_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🚀 БО 7.2 запущен!")
    app.add_handler(CallbackQueryHandler(handle_category, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(handle_choose_object, pattern="^choose_obj_"))
    app.add_handler(CallbackQueryHandler(handle_confirm_date, pattern="^confirmdate_"))
    app.add_handler(CallbackQueryHandler(handle_task_action, pattern="^(task_|taskdone_|taskdel_|setdate_|taskdate_|taskprio_|setprio_|taskrename_)"))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(?!cat_|choose_obj_|task_|taskdone_|taskdel_|setdate_|taskdate_|taskprio_|setprio_|taskrename_).*"))
    app.run_polling()


if __name__ == "__main__":
    main()