            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_spec_"):
        panel_id = int(data.replace("panel_spec_", ""))
        print("panel_spec handler: panel_id=" + str(panel_id), flush=True)
        if save_panel_spec is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            tmp_dir = tempfile.gettempdir()
            target = os.path.join(tmp_dir, "panel_spec_" + str(panel_id) + ".txt")
            path = save_panel_spec(panel_id, path=target)
            if not path or not os.path.exists(path):
                raise Exception("Файл не создан")
            try:
                p = core_elec_panels.get_panel(panel_id)
                name = (p.get('name') if p else 'panel') or 'panel'
            except Exception:
                name = 'panel'
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=name + "_spec.txt",
                    caption="📄 Спецификация щита «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("panel spec export: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка экспорта: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("panel_pdf_"):
        panel_id = int(data.replace("panel_pdf_", ""))
        try:
            from core.export import pdf_export as _pp
            path = _pp.export_panel_spec_pdf(panel_id)
            if not path:
                raise Exception("PDF не создан")
            p = core_elec_panels.get_panel(panel_id)
            name = (p.get("name") if p else "panel") or "panel"
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_spec.pdf",
                    caption="📄 PDF-спецификация щита «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("panel_pdf: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка PDF: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("obj_elec_pdf_"):
        object_id = int(data.replace("obj_elec_pdf_", ""))
        try:
            from core.export import pdf_export as _pp
            from modules.objects import get_object
            path = _pp.export_object_elec_pdf(object_id)
            if not path:
                raise Exception("PDF не создан")
            o = get_object(object_id)
            name = o["name"] if o else ("obj_" + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_elec.pdf",
                    caption="📄 PDF-смета ЭОМ «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("obj_elec_pdf: " + str(e), flush=True)
        return True

    if data.startswith("plumb_pdf_obj_"):
        object_id = int(data.replace("plumb_pdf_obj_", ""))
        try:
            from core.export import pdf_export as _pp
            from modules.objects import get_object
            path = _pp.export_plumbing_estimate_pdf(object_id)
            if not path:
                raise Exception("PDF не создан")
            o = get_object(object_id)
            name = o["name"] if o else ("obj_" + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_plumb.pdf",
                    caption="📄 PDF-смета сантехники «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("plumb_pdf_obj: " + str(e), flush=True)
        return True

    if data.startswith("panel_est_csv_"):
        panel_id = int(data.replace("panel_est_csv_", ""))
        if save_estimate_csv is None or export_panel_estimate_csv is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_panel_estimate_csv(panel_id)
            if not content:
                raise Exception("Пустая смета")
            target = os.path.join(tempfile.gettempdir(), "panel_est_" + str(panel_id) + ".csv")
            path = save_estimate_csv(content, path=target, prefix="panel_est")
            if not path or not os.path.exists(path):
                raise Exception("Файл не создан")
            try:
                p = core_elec_panels.get_panel(panel_id)
                name = (p.get('name') if p else 'panel') or 'panel'
            except Exception:
                name = 'panel'
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=name + "_smeta.csv",
                    caption="📊 Смета щита «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("panel est csv: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка экспорта: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("obj_est_csv_"):
        object_id = int(data.replace("obj_est_csv_", ""))
        if save_estimate_csv is None or export_object_estimate_csv is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_object_estimate_csv(object_id)
            if not content:
                raise Exception("Пустая смета")
            target = os.path.join(tempfile.gettempdir(), "obj_est_" + str(object_id) + ".csv")
            path = save_estimate_csv(content, path=target, prefix="obj_est")
            if not path or not os.path.exists(path):
                raise Exception("Файл не создан")
            from modules.objects import get_object
            o = get_object(object_id)
            name = o['name'] if o else ('obj_' + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_smeta.csv",
                    caption="📊 Смета ЭОМ объекта «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("obj est csv: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка экспорта: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    # ============ ЦЕНЫ ============
    if data.startswith("prices_import_"):
        object_id = int(data.replace("prices_import_", ""))
        if core_marketplaces is None:
            try:
                await query.edit_message_text("Модуль цен не загружен")
            except Exception:
                pass
            return True
        # Сгенерировать шаблон
        try:
            import tempfile, os
            tpl_path = os.path.join(tempfile.gettempdir(), 'prices_template.csv')
            core_marketplaces.generate_csv_template(tpl_path)
            context.user_data['price_csv_object_id'] = object_id
            context.user_data['waiting_for'] = 'price_csv'
            with open(tpl_path, 'rb') as f:
                await query.message.chat.send_document(
                    document=f,
                    filename='prices_template.csv',
                    caption=(
                        "💱 Шаблон прайса (CSV)" + chr(10) + chr(10) +
                        "Заполни и пришли обратно файл — я импортирую цены." + chr(10) + chr(10) +
                        "Формат: component_type;rating;poles;brand;price;currency;market_url;market_sku"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 История импортов", callback_data="prices_history_" + str(object_id))],
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("prices_import: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("prices_history_"):
        object_id = int(data.replace("prices_history_", ""))
        try:
            text = core_marketplaces.format_imports(object_id) if core_marketplaces else "Модуль не загружен"
        except Exception as e:
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К ценам", callback_data="prices_import_" + str(object_id))],
            [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
        ]))
        return True

    # ============ РАБОТЫ ============
    if data.startswith("works_list_"):
        object_id = int(data.replace("works_list_", ""))
        if not core_works:
            try:
                await query.edit_message_text("Модуль работ не загружен")
            except Exception:
                pass
            return True
        try:
            text = core_works.format_object_works(object_id)
        except Exception as e:
            print("works list: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        kb_rows = [
            [InlineKeyboardButton("➕ Добавить работу", callback_data="works_add_" + str(object_id))],
            [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
        ]
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("works_add_type_"):
        parts = data.replace("works_add_type_", "").rsplit("_", 1)
        object_id = int(parts[0])
        wtype = parts[1]
        context.user_data['work_new_object_id'] = object_id
        context.user_data['work_new_type'] = wtype
