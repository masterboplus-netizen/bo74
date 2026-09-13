"""Точка сборки БО 7.2"""
import logging
from telegram.ext import Application, CommandHandler
from config import TOKEN, validate_config
from db import init_db
from handlers.commands import (
    start, help_command, add_object_command, objects_command,
    add_task_command, tasks_command, done_command,
    finance_command, add_expense_command
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

    logger.info("🚀 БО 7.2 запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()