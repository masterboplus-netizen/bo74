"""Callbacks домена KPI — вынесено из _legacy.py (сессия 16)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode


async def try_handle(data: str, query, context) -> bool:
    """Обработка callback'ов KPI. Возвращает True если обработано."""

    # === menu_kpi : главное меню KPI ===
    if data == "menu_kpi":
        try:
            await query.edit_message_text(
                "📊 KPI\\n\\nВыбери отчёт:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👤 KPI мастеров (30 дн.)", callback_data="kpi_masters")],
                    [InlineKeyboardButton("🏗️ Здоровье объектов", callback_data="kpi_objects")],
                    [InlineKeyboardButton("⚠️ Красная зона", callback_data="kpi_red")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
                ])
            )
        except Exception:
            pass
        return True

    # === kpi_masters : KPI мастеров ===
    if data == "kpi_masters":
        from modules.kpi import get_master_kpi, format_master_kpi
        masters = get_master_kpi(30)
        text = format_master_kpi(masters, 30)
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К KPI", callback_data="menu_kpi")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return True

    # === kpi_objects : здоровье объектов ===
    if data == "kpi_objects":
        from modules.kpi import get_object_health, format_object_health
        items = get_object_health()
        text = format_object_health(items)
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К KPI", callback_data="menu_kpi")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return True

    # === kpi_red : красная зона ===
    if data == "kpi_red":
        from modules.kpi import get_red_zone, format_red_zone
        items = get_red_zone()
        text = format_red_zone(items)
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К KPI", callback_data="menu_kpi")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return True

    return False
