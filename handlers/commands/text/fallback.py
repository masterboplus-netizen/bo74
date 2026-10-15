"""Fallback: умный поиск похожих объектов через rapidfuzz."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from modules.objects import get_all_objects


async def try_handle(update, context, text: str) -> bool:
    """Умный fallback: ищем похожие объекты. Возвращает True, если обработали."""
    context.user_data['unknown_text'] = text

    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
    all_objs = get_all_objects()
    text_lower = text.strip().lower()
    exact_match = None
    similar = []
    for o in all_objs:
        if (o.get('name') or '').lower() == text_lower:
            exact_match = o
            break
    if not exact_match and all_objs:
        names = [o.get('name') or '' for o in all_objs]
        matches = rf_process.extract(text, names, scorer=rf_fuzz.WRatio, limit=5)
        for name, score, idx in matches:
            if score >= 55:
                similar.append((all_objs[idx], score))

    if exact_match:
        context.user_data['unknown_text'] = None
        await update.message.reply_text(
            f"✅ *Нашёл объект!*\n\n"
            f"🏗{exact_match['name']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗Открыть объект", callback_data=f"obj_{exact_match['id']}")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return True

    buttons = []
    if similar:
        for o, score in similar:
            buttons.append([InlineKeyboardButton(
                f"🏗{o['name']} ({int(score)}%)",
                callback_data=f"obj_{o['id']}"
            )])
    buttons.append([InlineKeyboardButton(f"➕ Создать новый объект «{text[:40]}»",
                                          callback_data="unknown_as_object")])
    buttons.append([InlineKeyboardButton("👤 Это клиент", callback_data="unknown_as_client"),
                    InlineKeyboardButton("📋 Это задача", callback_data="unknown_as_task")])
    buttons.append([InlineKeyboardButton("💰 Расход на объект", callback_data="unknown_as_expense"),
                    InlineKeyboardButton("💸 Личный расход", callback_data="unknown_as_personal")])
    buttons.append([InlineKeyboardButton("❌ Ничего", callback_data="unknown_cancel")])

    header = f"🤔 Не распознал: «{text[:80]}»\n\n"
    if similar:
        header += f"🔍 Нашёл {len(similar)} похожих объектов.\nВыбери:"
    else:
        header += "Что с этим сделать?"

    await update.message.reply_text(
        header,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return True
