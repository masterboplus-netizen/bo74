"""Личные расходы."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes


async def personal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /personal — личные расходы за месяц."""
    await update.message.reply_text(
        format_personal_summary('month'),
        reply_markup=personal_keyboard()
    )

# === CRM: КЛИЕНТЫ И СДЕЛКИ ===



def format_personal_summary(period='month'):
    """Формирует текст сводки личных расходов"""
    from modules.personal import get_personal_summary
    data = get_personal_summary(period)
    period_names = {
        'today': 'сегодня',
        'week': 'за 7 дней',
        'month': 'за месяц',
        'all': 'за всё время'
    }
    text = f"💸 ЛИЧНЫЕ РАСХОДЫ ({period_names.get(period, period)})\n\n"
    text += f"Потрачено: {data['total']} ₽\n"
    text += f"Записей: {data['count']}\n\n"
    if data['by_category']:
        text += "📊 По категориям:\n"
        for item in data['by_category'][:10]:
            text += f"• {item['category']}: {item['amount']} ₽\n"
    else:
        text += "Пока нет записей за этот период."
    return text




def personal_keyboard():
    """Клавиатура для экрана личных расходов"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить расход", callback_data="personal_add")],
        [InlineKeyboardButton("📅 За сегодня", callback_data="personal_today"),
         InlineKeyboardButton("📅 За неделю", callback_data="personal_week")],
        [InlineKeyboardButton("📅 За месяц", callback_data="personal_month"),
         InlineKeyboardButton("📅 За всё время", callback_data="personal_all")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
    ])


