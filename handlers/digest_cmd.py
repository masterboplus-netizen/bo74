"""Команда для тестирования дайджеста БО 7.4"""
from telegram import Update
from telegram.ext import ContextTypes
from modules.digest import build_morning_digest, build_evening_survey


async def digest_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает утренний дайджест прямо сейчас (для теста)"""
    text = build_morning_digest()
    await update.message.reply_text(text)


async def survey_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает вечерний опрос прямо сейчас (для теста)"""
    text = build_evening_survey()
    await update.message.reply_text(text)
