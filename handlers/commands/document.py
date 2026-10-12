"""Обработка документов (импорт CSV-прайсов)."""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
import os
import tempfile


async def handle_document(update, context):
    """Обработчик документов (CSV-прайсы, PDF, Excel)."""
    print("📥 HANDLE_DOCUMENT ВЫЗВАН", flush=True)
    doc = update.message.document
    if not doc:
        print("📥 no doc", flush=True)
        return
    file_name = (doc.file_name or '').lower()
    print(f"📥 file_name={file_name!r}", flush=True)

    # Обработка CSV и XLSX
    is_xlsx = file_name.endswith('.xlsx') or file_name.endswith('.xls')
    is_csv = file_name.endswith('.csv')
    if not (is_csv or is_xlsx):
        await update.message.reply_text(
            "📄 Поддерживаются только CSV и Excel (.xlsx) файлы." + chr(10) + chr(10) +
            "Пришли прайс в формате CSV или Excel."
        )
        return

    # Скачать файл
    try:
        tg_file = await context.bot.get_file(doc.file_id)
        tmp_dir = tempfile.gettempdir()
        # Скачиваем с оригинальным расширением
        ext = '.xlsx' if is_xlsx else '.csv'
        raw_path = os.path.join(tmp_dir, 'import_' + str(doc.file_id) + ext)
        await tg_file.download_to_drive(raw_path)
    except Exception as e:
        await update.message.reply_text("❌ Не смог скачать файл: " + str(e))
        return

    # Если xlsx — конвертируем в csv
    if is_xlsx:
        try:
            import openpyxl
            import csv as _csv
            wb = openpyxl.load_workbook(raw_path, data_only=True)
            ws = wb.active
            target = os.path.join(tmp_dir, 'import_' + str(doc.file_id) + '.csv')
            with open(target, 'w', encoding='utf-8-sig', newline='') as f_out:
                writer = _csv.writer(f_out, delimiter=';')
                for row in ws.iter_rows(values_only=True):
                    writer.writerow([('' if v is None else v) for v in row])
            print(f"📥 xlsx -> csv: {target}", flush=True)
        except Exception as e:
            await update.message.reply_text("❌ Ошибка чтения Excel: " + str(e))
            return
    else:
        target = raw_path

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

