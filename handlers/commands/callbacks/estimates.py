"""Callbacks домена «Сметы» — вынесено из _legacy.py (сессия 16)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from db import get_connection
from modules.objects import get_object
from modules.finance import get_finance_summary


async def try_handle(data: str, query, context) -> bool:
    """Обработка callback'ов домена Сметы."""

    # Быстрый выход для не-estimates
    if not data.startswith("est_"):
        return False

    # === est_month_* : PDF отчёт по объекту за месяц ===
    if data.startswith("est_month_"):
        try:
            object_id = int(data.replace("est_month_", ""))
        except ValueError:
            return True
        from core.export.pdf_export import export_object_monthly_report_pdf
        path = export_object_monthly_report_pdf(object_id)
        if not path:
            try:
                await query.edit_message_text("❌ Отчёт не создан")
            except Exception:
                pass
            return True
        obj = get_object(object_id)
        name = obj.get("name") if obj else ("obj_" + str(object_id))
        try:
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_monthly.pdf",
                    caption="📅 Отчёт по объекту «" + str(name) + "» за месяц",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("est_month: " + str(e), flush=True)
        return True

    # === est_kpi_objs : здоровье объектов ===
    if data == "est_kpi_objs":
        from modules.kpi import get_object_health, format_object_health
        try:
            text = format_object_health(get_object_health()).replace("*", "")
            if len(text) > 4000:
                text = text[:3900] + "\n\n..."
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data="menu_kpi")],
                ])
            )
        except Exception as e:
            print("est_kpi_objs: " + str(e), flush=True)
        return True

    # === est_kpi_red : красная зона ===
    if data == "est_kpi_red":
        from modules.kpi import get_red_zone, format_red_zone
        try:
            text = format_red_zone(get_red_zone()).replace("*", "")
            if len(text) > 4000:
                text = text[:3900] + "\n\n..."
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data="menu_kpi")],
                ])
            )
        except Exception as e:
            print("est_kpi_red: " + str(e), flush=True)
        return True

    # === est_kpi_masters : KPI мастеров ===
    if data == "est_kpi_masters":
        from modules.kpi import get_master_kpi, format_master_kpi
        try:
            text = format_master_kpi(get_master_kpi()).replace("*", "")
            if len(text) > 4000:
                text = text[:3900] + "\n\n..."
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data="menu_kpi")],
                ])
            )
        except Exception as e:
            print("est_kpi_masters: " + str(e), flush=True)
        return True

    return False
