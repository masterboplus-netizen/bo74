"""Команда для тестирования дайджеста БО 7.7"""
from telegram import Update
from telegram.ext import ContextTypes
from config import MAIN_ADMIN_TG_ID
from modules.digest import build_morning_digest, build_evening_survey


def _is_admin(update: Update) -> bool:
    return update.effective_user and update.effective_user.id == MAIN_ADMIN_TG_ID


async def digest_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает утренний дайджест прямо сейчас (для теста). Только админ."""
    if not _is_admin(update):
        await update.message.reply_text("⛔ Только для админа.")
        return
    text = build_morning_digest()
    await update.message.reply_text(text)


async def survey_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает вечерний опрос прямо сейчас (для теста). Только админ."""
    if not _is_admin(update):
        await update.message.reply_text("⛔ Только для админа.")
        return
    text = build_evening_survey()
    await update.message.reply_text(text)
