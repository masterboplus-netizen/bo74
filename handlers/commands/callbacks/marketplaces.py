"""Роутер домена Маркетплейсы (импорт/экспорт прайсов)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def try_handle(data: str, query, context) -> bool:
    """Обработка callback'ов маркетплейсов."""
    if data == "est_import":
        from core.marketplaces import generate_csv_template
        try:
            path = generate_csv_template("/tmp/prices_template.csv")
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename="prices_template.csv",
                    caption=(
                        "📦 Шаблон прайса (CSV)" + chr(10) + chr(10) +
                        "Заполни и пришли обратно файл — импортирую цены." + chr(10) + chr(10) +
                        "Формат: component_type;rating;poles;brand;price;currency;market_url;market_sku"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅ К сметам", callback_data="menu_estimates")],
                    ])
                )
        except Exception as e:
            print("est_import: " + str(e), flush=True)
        return True

    return False
