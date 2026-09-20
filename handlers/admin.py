# -*- coding: utf-8 -*-
"""Бо 7.5 — Админ-команды."""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ParseMode
from handlers.onboarding import MAIN_ADMIN_TG_ID


def _is_admin(update: Update) -> bool:
    return update.effective_user.id == MAIN_ADMIN_TG_ID


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("⛔ Только для админа.")
        return
    from modules.users import get_all_users
    users = get_all_users()
    if not users:
        await update.message.reply_text("Юзеров нет.")
        return
    lines = ["👥 *Пользователи:*\n"]
    for u in users:
        uid  = u.get("tg_id") if isinstance(u, dict) else u[1]
        name = u.get("name")  if isinstance(u, dict) else u[2]
        role = u.get("role")  if isinstance(u, dict) else u[3]
        lines.append(f"• `{uid}` — {name} ({role})")
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        await update.message.reply_text("⛔ Только для админа.")
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: /set_role <tg_id> <role>\n"
            "Роли: admin, designer, prorab, master, guest")
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await update.message.reply_text("tg_id должен быть числом")
        return
    role = args[1].lower()
    valid = {"admin", "designer", "prorab", "master", "client", "guest"}
    if role not in valid:
        await update.message.reply_text(f"Недопустимая роль. Доступно: {', '.join(sorted(valid))}")
        return
    from modules.users import set_role, mark_onboarded
    set_role(tg_id, role)
    try:
        mark_onboarded(tg_id)
    except Exception:
        pass
    await update.message.reply_text(
        f"✅ Юзеру `{tg_id}` назначена роль: *{role}*",
        parse_mode=ParseMode.MARKDOWN)


def register_admin_handlers(app):
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("set_role", cmd_set_role))
