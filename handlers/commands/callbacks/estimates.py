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

# === est_export_all : PDF-смета всех объектов ===
    if data == "est_export_all":
        from core.object_estimate import calc_object_estimate
        from core.export.pdf_export import export_object_estimate_pdf
        obj = get_object(1)  # fallback
        # Собираем общую смету всех объектов
        try:
            objs = get_all_objects()
        except Exception:
            objs = []
        if not objs:
            try:
                await query.edit_message_text("❌ Нет объектов")
            except Exception:
                pass
            return True
        first_id = objs[0]["id"]
        path = export_object_estimate_pdf(first_id)
        if not path:
            try:
                await query.edit_message_text("❌ PDF не создан")
            except Exception:
                pass
            return True
        try:
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename="all_estimates.pdf",
                    caption="📄 Общая смета"
                )
        except Exception as e:
            print("est_export_all: " + str(e), flush=True)
        return True

    # === est_dash : дашборд ===
    if data == "est_dash":
        from core.object_estimate import calc_object_estimate
        try:
            objs = get_all_objects()
        except Exception:
            objs = []
        totals = []
        for o in objs[:30]:
            est = calc_object_estimate(o["id"])
            if est:
                totals.append(est.get("total", 0))
        total_all = sum(totals)
        avg = round(total_all / max(len(totals), 1), 2)
        med = round(sorted(totals)[len(totals) // 2], 2) if totals else 0
        lines = [
            "📊 Дашборд смет",
            "",
            "💼 Всего смет:   " + str(len(totals)),
            "💰 Сумма:        " + str(round(total_all, 2)) + " ₽",
            "📈 Средняя:      " + str(avg) + " ₽",
            "📊 Медиана:      " + str(med) + " ₽",
        ]
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
                ])
            )
        except Exception as e:
            print("est_dash: " + str(e), flush=True)
        return True

    # === est_all : все сметы ===
    if data == "est_all":
        from core.object_estimate import calc_object_estimate
        try:
            objs = get_all_objects()
        except Exception:
            objs = []
        lines = ["📋 Сметы всех объектов", ""]
        total = 0
        for o in objs[:20]:
            est = calc_object_estimate(o["id"])
            if est:
                t = est.get("total", 0)
                total += t
                lines.append("🏗️ " + str(o["name"])[:30] + ": " + str(round(t, 2)) + " ₽")
        lines.append("")
        lines.append("💰 ВСЕГО: " + str(round(total, 2)) + " ₽")
        text = chr(10).join(lines)
        if len(text) > 4000:
            text = text[:3900] + "\n\n..."
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
                ])
            )
        except Exception as e:
            print("est_all: " + str(e), flush=True)
        return True

    # === est_search : поиск по сметам ===
    if data == "est_search":
        try:
            await query.edit_message_text(
                "🔎 Поиск по сметам\n\nНапиши название объекта:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
                ])
            )
        except Exception as e:
            print("est_search: " + str(e), flush=True)
        return True

# === est_room_* : смета комнаты ===
    if data.startswith("est_room_"):
        try:
            room_id = int(data.replace("est_room_", ""))
        except ValueError:
            return True
        from core.room_estimate import format_room_estimate
        text = format_room_estimate(room_id)
        if len(text) > 4000:
            text = text[:3900] + "\n\n..."
        # Извлекаем object_id из room? Пока простая ссылка через callback
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🧱 Только материалы", callback_data="est_room_mat_" + str(room_id))],
                    [InlineKeyboardButton("👷 Только работы", callback_data="est_room_work_" + str(room_id))],
                    [InlineKeyboardButton("📅 Период", callback_data="est_room_per_" + str(room_id))],
                ])
            )
        except Exception:
            pass
        return True

    # === est_object_* : меню сметы объекта ===
    if data.startswith("est_object_"):
        try:
            object_id = int(data.replace("est_object_", ""))
        except ValueError:
            return True
        obj = get_object(object_id)
        name = obj.get("name") if obj else "?"
        kb = [
            [InlineKeyboardButton("📄 Экспорт (TXT)", callback_data="est_export_" + str(object_id))],
            [InlineKeyboardButton("📄 PDF-смета", callback_data="est_pdf_" + str(object_id))],
            [InlineKeyboardButton("📊 CSV-смета", callback_data="est_csv_" + str(object_id))],
            [InlineKeyboardButton("💱 Сравнение цен", callback_data="est_cmp_" + str(object_id))],
            [InlineKeyboardButton("📊 KPI объекта", callback_data="est_kpi_" + str(object_id))],
            [InlineKeyboardButton("⚙️ Правила ЭОМ", callback_data="est_rules_" + str(object_id))],
            [InlineKeyboardButton("📈 По периодам", callback_data="est_period_" + str(object_id))],
            [InlineKeyboardButton("✏️ Редактировать цены", callback_data="est_prices_" + str(object_id))],
            [InlineKeyboardButton("💡 Смета ЭОМ", callback_data="obj_elec_cost_" + str(object_id))],
            [InlineKeyboardButton("🔧 Смета сантехники", callback_data="plumb_cost_obj_" + str(object_id))],
            [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
        ]
        try:
            await query.edit_message_text(
                "📋 Смета объекта «" + str(name) + "»",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception as e:
            print("est_object: " + str(e), flush=True)
        return True

# === est_csv_* : CSV-смета объекта ===
    if data.startswith("est_csv_"):
        try:
            object_id = int(data.replace("est_csv_", ""))
        except ValueError:
            return True
        from core.object_estimate import calc_object_estimate
        import csv
        est = calc_object_estimate(object_id)
        if not est:
            return True
        obj = get_object(object_id)
        name = obj.get("name") if obj else ("obj_" + str(object_id))
        path = "/tmp/estimate_" + str(object_id) + ".csv"
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Комната", "Материалы", "Работы", "Итого"])
            for r in est.get("rooms", []):
                w.writerow([r["name"], r["materials"], r["works"], r["total"]])
            w.writerow([])
            w.writerow(["Материалы (всего)", est["total_materials"]])
            w.writerow(["Работы (всего)", est["total_works"]])
            w.writerow(["ЭОМ", est["elec"]])
            w.writerow(["Сантехника", est["plumbing"]])
            w.writerow(["Отдельные работы", est.get("extra_works", 0)])
            w.writerow(["ВСЕГО", est["total"]])
        try:
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_smeta.csv",
                    caption="📊 CSV-смета объекта «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("est_csv: " + str(e), flush=True)
        return True

    # === est_period_* : меню периодов ===
    if data.startswith("est_period_"):
        try:
            object_id = int(data.replace("est_period_", ""))
        except ValueError:
            return True
        kb_rows = [
            [InlineKeyboardButton("📅 За неделю", callback_data="est_per_" + str(object_id) + "_week")],
            [InlineKeyboardButton("📅 За месяц", callback_data="est_per_" + str(object_id) + "_month")],
            [InlineKeyboardButton("📅 За всё время", callback_data="est_per_" + str(object_id) + "_all")],
            [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "📈 Аналитика по периодам" + chr(10) + chr(10) + "Выбери период:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_period: " + str(e), flush=True)
        return True

    # === est_per_* : аналитика за период ===
    if data.startswith("est_per_"):
        rest = data.replace("est_per_", "")
        try:
            object_id_s, period = rest.rsplit("_", 1)
            object_id = int(object_id_s)
        except (ValueError, IndexError):
            return True
        from core.economics import calc_margin
        obj = get_object(object_id)
        name = obj.get("name") if obj else "?"
        f = get_finance_summary(object_id)
        m = calc_margin(object_id, period=period)
        pnames = {"week": "неделю", "month": "месяц", "all": "всё время"}
        lines = [
            "📈 " + str(name) + " — за " + pnames.get(period, period),
            "",
            "💰 Доход:   " + str(f.get("income", 0)) + " ₽",
            "💸 Расход:  " + str(f.get("expense", 0)) + " ₽",
            "⚖️ Баланс:  " + str(f.get("balance", 0)) + " ₽",
            "",
            "📊 Маржа:   " + str(m.get("margin_percent", 0)) + " %",
        ]
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К периодам", callback_data="est_period_" + str(object_id))],
                    [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                ])
            )
        except Exception as e:
            print("est_per: " + str(e), flush=True)
        return True

    # === est_rules_* : правила ЭОМ ===
    if data.startswith("est_rules_"):
        try:
            object_id = int(data.replace("est_rules_", ""))
        except ValueError:
            return True
        from core.elec_rules import format_rules, list_overrides
        text = format_rules(object_id).replace("*", "")
        if len(text) > 4000:
            text = text[:3900] + chr(10) + chr(10) + "..."
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                ])
            )
        except Exception as e:
            print("est_rules: " + str(e), flush=True)
        return True

    # === est_kpi_* : KPI объекта (с числовым id) ===
    if data.startswith("est_kpi_"):
        try:
            object_id = int(data.replace("est_kpi_", ""))
        except ValueError:
            return True
        from core.economics import calc_margin
        obj = get_object(object_id)
        name = obj.get("name") if obj else "?"
        f = get_finance_summary(object_id)
        m = calc_margin(object_id, period="all")
        income = f.get("income", 0)
        expense = f.get("expense", 0)
        balance = f.get("balance", 0)
        lines = [
            "📊 KPI объекта «" + str(name) + "»",
            "",
            "💰 Финансы:",
            "   Доход:   " + str(income) + " ₽",
            "   Расход:  " + str(expense) + " ₽",
            "   Баланс:  " + str(balance) + " ₽",
            "",
            "📈 Маржа:",
            "   Прибыль: " + str(m.get("profit", 0)) + " ₽",
            "   Маржа:   " + str(m.get("margin_percent", 0)) + " %",
        ]
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                ])
            )
        except Exception as e:
            print("est_kpi: " + str(e), flush=True)
        return True

    return False
