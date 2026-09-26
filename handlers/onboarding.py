# -*- coding: utf-8 -*-
"""Бо 7.7 — Онбординг: выбор роли + меню по ролям."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode


# === ГЛАВНЫЙ АДМИН (из config) ===
from config import MAIN_ADMIN_TG_ID


ONBOARDING_ROLES = [
    ("designer", "🎨 Дизайнер"),
    ("prorab",   "👷 Прораб"),
    ("master",   "🔧 Мастер"),
]


def role_menu_keyboard(role: str):
    if role in ("admin", "prorab", "designer"):
        rows = [
            [InlineKeyboardButton("🏗️ Объекты",  callback_data="menu_objects")],
            [InlineKeyboardButton("📋 Задачи",   callback_data="menu_tasks")],
            [InlineKeyboardButton("💰 Финансы",  callback_data="menu_finance")],
            [InlineKeyboardButton("📊 Отчёты",   callback_data="menu_reports")],
            [InlineKeyboardButton("📊 KPI",      callback_data="menu_kpi")],
            [InlineKeyboardButton("💸 Личные",   callback_data="menu_personal")],
            [InlineKeyboardButton("👥 CRM",      callback_data="menu_crm")],
            [InlineKeyboardButton("🌐 Дашборд",  callback_data="menu_dashboard")],
            [InlineKeyboardButton("➕ Добавить", callback_data="menu_add")],
            [InlineKeyboardButton("⚙️ Помощь",   callback_data="menu_help")],
        ]
    elif role == "master":
        rows = [
            [InlineKeyboardButton("🏗️ Объекты",  callback_data="menu_objects")],
            [InlineKeyboardButton("📋 Задачи",   callback_data="menu_tasks")],
            [InlineKeyboardButton("💸 Личные",   callback_data="menu_personal")],
            [InlineKeyboardButton("➕ Добавить", callback_data="menu_add")],
            [InlineKeyboardButton("⚙️ Помощь",   callback_data="menu_help")],
        ]
    else:
        rows = [
            [InlineKeyboardButton("🏗️ Объекты",  callback_data="menu_objects")],
            [InlineKeyboardButton("📋 Задачи",   callback_data="menu_tasks")],
            [InlineKeyboardButton("💸 Личные",   callback_data="menu_personal")],
            [InlineKeyboardButton("⚙️ Помощь",   callback_data="menu_help")],
        ]
    return InlineKeyboardMarkup(rows)


def onboarding_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"setrole_{code}")]
         for code, label in ONBOARDING_ROLES]
    )


async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Привет! Я *Бо 7.7* — твой помощник по стройке.\n\n"
        "Выбери свою роль:\n\n"
        "🎨 *Дизайнер* — объекты, задачи, финансы, отчёты\n"
        "👷 *Прораб* — объекты, задачи, финансы, отчёты\n"
        "🔧 *Мастер* — задачи, объекты, личные расходы\n\n"
        "_Роль можно изменить у админа._"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=onboarding_keyboard(), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(
            text, reply_markup=onboarding_keyboard(), parse_mode=ParseMode.MARKDOWN)


async def handle_setrole(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    if not data.startswith("setrole_"):
        return
    role = data.replace("setrole_", "", 1)
    user = update.effective_user

    try:
        from modules.users import save_user, set_role, mark_onboarded
        save_user(user.id, user.first_name or "", user.username or "", role=role)
        set_role(user.id, role)
        mark_onboarded(user.id)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения роли: {e}")

    role_label = dict(ONBOARDING_ROLES).get(role, role)
    await query.edit_message_text(
        f"✅ Отлично! Твоя роль: *{role_label}*\n\n"
        f"Команды всегда доступны через /help.",
        reply_markup=role_menu_keyboard(role),
        parse_mode=ParseMode.MARKDOWN,
    )


def register_onboarding_handlers(app):
    app.add_handler(CallbackQueryHandler(handle_setrole, pattern=r"^setrole_"))
