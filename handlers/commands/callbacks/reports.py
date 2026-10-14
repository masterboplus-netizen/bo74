"""Callback-хендлеры домена «отчёты» (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_callback).
Блоки: report_summary_*, report_closed_week/month, report_open,
report_choose_object, report_obj_*.

Роутер try_handle(data, query, context) -> bool.
True = обработано, вызывающий делает return.

Точка входа: menu_reports — добавлена 2026-10-14 (восстановлена из
бэкапа bak_allwork_20261013_221253:993 после случайной потери в сессии 16).

Замечание: импорты из modules.reports — локальные внутри каждой ветки
(как было в _legacy.py). При отдельном рефакторинге поднять в шапку.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from modules.objects import get_all_objects


async def try_handle(data: str, query, context) -> bool:
    """Обрабатывает reports-callback-и. True = обработано."""

    # === Точка входа: меню отчётов ===
    if data == "menu_reports":
        await query.edit_message_text(
            "📊 ОТЧЁТЫ\n\nВыбери тип:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Что сделано (неделя)", callback_data="report_closed_week")],
                [InlineKeyboardButton("✅ Что сделано (месяц)", callback_data="report_closed_month")],
                [InlineKeyboardButton("🔄 Что в работе", callback_data="report_open")],
                [InlineKeyboardButton("📈 Финансы за месяц", callback_data="report_summary_month")],
                [InlineKeyboardButton("📈 Финансы за неделю", callback_data="report_summary_week")],
                [InlineKeyboardButton("📈 Финансы за всё время", callback_data="report_summary_all")],
                [InlineKeyboardButton("🏗️Отчёт по объекту", callback_data="report_choose_object")],
                [InlineKeyboardButton("⬅️Назад", callback_data="menu_back")],
            ])
        )
        return True

    if data.startswith("report_summary_"):
        period = data.replace("report_summary_", "")
        from modules.reports import get_summary_report, format_summary_report
        report = get_summary_report(period)
        text = format_summary_report(report)
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К отчётам", callback_data="menu_reports")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    if data == "report_closed_week" or data == "report_closed_month":
        period = 'week' if data == "report_closed_week" else 'month'
        from modules.reports import get_closed_tasks_report, format_closed_tasks_report
        report = get_closed_tasks_report(period)
        text = format_closed_tasks_report(report)
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К отчётам", callback_data="menu_reports")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    if data == "report_open":
        from modules.reports import get_open_tasks_report, format_open_tasks_report
        report = get_open_tasks_report()
        text = format_open_tasks_report(report)
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К отчётам", callback_data="menu_reports")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    if data == "report_choose_object":
        objs = get_all_objects()
        buttons = []
        for o in objs:
            buttons.append([InlineKeyboardButton(
                f"🏗️{o['name']}",
                callback_data=f"report_obj_{o['id']}_month"
            )])
        buttons.append([InlineKeyboardButton("⬅️Назад", callback_data="menu_reports")])
        await query.edit_message_text(
            "📊 Выбери объект для отчёта (за месяц):",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return True

    if data.startswith("report_obj_"):
        # report_obj_<obj_id>_<period>
        parts = data.replace("report_obj_", "").split("_")
        obj_id = int(parts[0])
        period = parts[1] if len(parts) > 1 else 'month'
        from modules.reports import get_object_report, format_object_report
        report = get_object_report(obj_id, period)
        text = format_object_report(report)
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 За неделю", callback_data=f"report_obj_{obj_id}_week")],
                [InlineKeyboardButton("📅 За месяц", callback_data=f"report_obj_{obj_id}_month")],
                [InlineKeyboardButton("📅 За всё время", callback_data=f"report_obj_{obj_id}_all")],
                [InlineKeyboardButton("📷 Фото объекта", callback_data=f"objphotos_{obj_id}")],
                [InlineKeyboardButton("⬅️ К отчётам", callback_data="menu_reports")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    return False
