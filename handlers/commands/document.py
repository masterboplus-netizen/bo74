"""Обработка документов (импорт CSV-прайсов)."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton


async def handle_document(update, context):
    """Обработчик документов (CSV-прайсы, PDF, Excel)."""
    doc = update.message.document
    if not doc:
        return
    file_name = (doc.file_name or '').lower()

    # Обработка только CSV
    if not file_name.endswith('.csv'):
        await update.message.reply_text(
            "📄 Поддерживаются только CSV-файлы." + chr(10) + chr(10) +
            "Пришли прайс в формате CSV (шаблон — через 💱 Импорт цен)."
        )
        return

    # Скачать файл
    try:
        tg_file = await context.bot.get_file(doc.file_id)
        import tempfile, os
        tmp_dir = tempfile.gettempdir()
        target = os.path.join(tmp_dir, 'import_' + str(doc.file_id) + '.csv')
        await tg_file.download_to_drive(target)
    except Exception as e:
        await update.message.reply_text("❌ Не смог скачать файл: " + str(e))
        return

    # Импорт
    try:
        from core import marketplaces as mp
        object_id = context.user_data.get('price_csv_object_id')
        res = mp.import_prices_csv(target, source='csv', object_id=object_id)
    except Exception as e:
        await update.message.reply_text("❌ Ошибка импорта: " + str(e))
        return

    if res.get('ok'):
        text = (
            "✅ Импорт завершён" + chr(10) + chr(10) +
            "Импортировано: " + str(res.get('imported', 0)) + chr(10) +
            "Пропущено: " + str(res.get('skipped', 0))
        )
        if res.get('errors'):
            text += chr(10) + chr(10) + "Ошибки:" + chr(10) + chr(10)
            for err in res['errors'][:3]:
                text += "• " + str(err) + chr(10)
        kb_rows = []
        if object_id:
            kb_rows.append([InlineKeyboardButton("⬅️ К ценам", callback_data="prices_import_" + str(object_id))])
            kb_rows.append([InlineKeyboardButton("📋 История", callback_data="prices_history_" + str(object_id))])
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb_rows) if kb_rows else None)
    else:
        await update.message.reply_text("❌ Ошибка импорта: " + str(res.get('error', '?')))

    context.user_data['price_csv_object_id'] = None
    context.user_data['waiting_for'] = None

