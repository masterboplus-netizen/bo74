"""Общие клавиатуры (главное меню)."""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏗️ Объекты", callback_data="menu_objects")],
        [InlineKeyboardButton("📋 Задачи", callback_data="menu_tasks")],
        [InlineKeyboardButton("💰 Финансы", callback_data="menu_finance")],
        [InlineKeyboardButton("💵 Сметы", callback_data="menu_estimates")],
        [InlineKeyboardButton("📊 Отчёты", callback_data="menu_reports")],
        [InlineKeyboardButton("📊 KPI", callback_data="menu_kpi")],
        [InlineKeyboardButton("💸 Личные", callback_data="menu_personal")],
        [InlineKeyboardButton("👥 CRM", callback_data="menu_crm")],
        [InlineKeyboardButton("🌐 Дашборд", callback_data="menu_dashboard")],
        [InlineKeyboardButton("➕ Добавить", callback_data="menu_add")],
        [InlineKeyboardButton("⚙️ Помощь", callback_data="menu_help")],
    ])

