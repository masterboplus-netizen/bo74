"""Команды Telegram-бота БО 7.7"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from db import get_connection
from modules.objects import create_object, get_all_objects, get_object_by_name, get_object
from modules.tasks import create_task, get_active_tasks, close_task, get_tasks_by_object
from modules.finance import add_expense, get_finance_summary
from modules.parser import parse_message, parse_amount
from modules.personal import add_personal_expense
from config import ADMIN_IDS
from handlers.onboarding import ask_role, role_menu_keyboard
from handlers.commands.start import _help_text, help_command
from handlers.commands.personal import personal_command, format_personal_summary, personal_keyboard
from handlers.commands.receipt import (
    handle_recognize_receipt, handle_receipt_save, handle_receipt_object,
    handle_receipt_category, handle_receipt_show
)
from handlers.commands.photos import (
    photos_command, _show_photos_batch, handle_photo_filter, handle_photo_page,
    handle_photo, handle_photo_stage, handle_photo_task, handle_photo_save
)
from handlers.commands.crm import (
    clients_command, deals_command, handle_crm_menu, _finalize_new_client
)
from handlers.commands.finance import (
    finance_command, add_expense_command, finance_keyboard,
    format_finance_summary, show_finance_summary, format_money
)
from handlers.commands.objects import (
    add_object_command, objects_command, objects_keyboard, object_detail_keyboard,
    choose_object_for_task_keyboard, choose_object_for_expense_keyboard,
    choose_object_for_expense_keyboard_amount
)
from handlers.commands.tasks import (
    add_task_command, format_tasks_block, tasks_command, done_command,
    handle_skip_photo, tasks_keyboard, tasks_keyboard_by_object,
    task_card_keyboard, task_date_keyboard, task_priority_keyboard,
    show_task_card, handle_task_action, build_calendar,
    auto_confirm_date, handle_confirm_date
)
from handlers.commands.choose_expense import (
    handle_choose_object, make_choose_keyboard,
    expense_category_keyboard, handle_category
)
from handlers.commands.document import handle_document
from handlers.commands.keyboards import main_menu_keyboard
from handlers.commands.add_menu import handle_add_menu
from handlers.commands.utils import parse_date


_est_extra_pending = None



async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # === Домен: tasks (вынесено в callbacks/tasks.py, сессия 16) ===
    from handlers.commands.callbacks.tasks import try_handle as _try_tasks_cb
    if await _try_tasks_cb(data, query, context):
        return
    
    # === Домен: estimates (est_csv_*, est_period_*, est_per_*, est_rules_*, est_kpi_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_pdf_*, est_export_*, est_extra_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    if data.startswith("est_prices_"):
        try:
            object_id = int(data.replace("est_prices_", ""))
        except ValueError:
            return
        kb_rows = [
            [InlineKeyboardButton("🧱 Материалы", callback_data="est_prices_mat_" + str(object_id))],
            [InlineKeyboardButton("👷 Работы", callback_data="est_prices_work_" + str(object_id))],
            [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "✏️ Редактирование цен\n\nЧто править?",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_prices: " + str(e), flush=True)
        return

    if data.startswith("est_prices_mat_"):
        try:
            object_id = int(data.replace("est_prices_mat_", ""))
        except ValueError:
            return
        from core import spec
        kb_rows = []
        for code, info in list(spec.MATERIALS_DEFAULT.items())[:20]:
            kb_rows.append([InlineKeyboardButton(
                info[0][:30] + " — " + str(info[4]) + " ₽/" + str(info[2]),
                callback_data="est_price_edit_mat_" + str(object_id) + "_" + code
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="est_prices_" + str(object_id))])
        try:
            await query.edit_message_text(
                "🧱 Материалы (цены):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_prices_mat: " + str(e), flush=True)
        return

    if data.startswith("est_prices_work_"):
        try:
            object_id = int(data.replace("est_prices_work_", ""))
        except ValueError:
            return
        from core import spec
        kb_rows = []
        for code, info in list(spec.WORK_TYPES_DEFAULT.items())[:20]:
            kb_rows.append([InlineKeyboardButton(
                info[0][:30] + " — " + str(info[2]) + " ₽/" + str(info[1]),
                callback_data="est_price_edit_work_" + str(object_id) + "_" + code
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="est_prices_" + str(object_id))])
        try:
            await query.edit_message_text(
                "👷 Работы (цены):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_prices_work: " + str(e), flush=True)
        return

    if data.startswith("est_price_edit_mat_"):
        rest = data.replace("est_price_edit_mat_", "")
        try:
            object_id, code = rest.split("_", 1)
            object_id = int(object_id)
        except (ValueError, IndexError):
            return
        from core import spec
        info = spec.MATERIALS_DEFAULT.get(code)
        if not info:
            return
        try:
            await query.edit_message_text(
                "🧱 " + info[0] + "\n\nТекущая цена: " + str(info[4]) + " ₽/" + str(info[2]) + "\n\nВведи новую цену (число):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="est_prices_mat_" + str(object_id))],
                ])
            )
            from handlers import commands as _cmd
            _cmd._est_pending_price = {"object_id": object_id, "type": "mat", "code": code}
        except Exception as e:
            print("est_price_edit_mat: " + str(e), flush=True)
        return

    if data.startswith("est_price_edit_work_"):
        rest = data.replace("est_price_edit_work_", "")
        try:
            object_id, code = rest.split("_", 1)
            object_id = int(object_id)
        except (ValueError, IndexError):
            return
        from core import spec
        info = spec.WORK_TYPES_DEFAULT.get(code)
        if not info:
            return
        try:
            await query.edit_message_text(
                "👷 " + info[0] + "\n\nТекущая цена: " + str(info[2]) + " ₽/" + str(info[1]) + "\n\nВведи новую цену (число):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="est_prices_work_" + str(object_id))],
                ])
            )
            from handlers import commands as _cmd
            _cmd._est_pending_price = {"object_id": object_id, "type": "work", "code": code}
        except Exception as e:
            print("est_price_edit_work: " + str(e), flush=True)
        return

    if data.startswith("est_sched_"):
        try:
            object_id = int(data.replace("est_sched_", ""))
        except ValueError:
            return
        from core.report_schedule import format_schedules
        text = format_schedules(object_id).replace("*", "")
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Создать (еженедельно)", callback_data="est_sched_add_" + str(object_id) + "_weekly")],
                    [InlineKeyboardButton("➕ Создать (ежемесячно)", callback_data="est_sched_add_" + str(object_id) + "_monthly")],
                    [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                ])
            )
        except Exception as e:
            print("est_sched: " + str(e), flush=True)
        return

    if data.startswith("est_sched_add_"):
        rest = data.replace("est_sched_add_", "")
        try:
            object_id_s, freq = rest.rsplit("_", 1)
            object_id = int(object_id_s)
        except (ValueError, IndexError):
            return
        from core.report_schedule import create_schedule
        sid = create_schedule(object_id=object_id, frequency=freq, hour=9, minute=0)
        try:
            await query.edit_message_text(
                "✅ Расписание создано (" + freq + ", в 09:00)",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К расписаниям", callback_data="est_sched_" + str(object_id))],
                    [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                ])
            )
        except Exception as e:
            print("est_sched_add: " + str(e), flush=True)
        return

    # === Домен: estimates (est_month вынесено в callbacks/estimates.py, сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    if data.startswith("est_where_"):
        try:
            object_id = int(data.replace("est_where_", ""))
        except ValueError:
            return
        from core import spec
        kb_rows = []
        for code in list(spec.MATERIALS_DEFAULT.keys())[:15]:
            info = spec.MATERIALS_DEFAULT[code]
            kb_rows.append([InlineKeyboardButton(
                info[0][:35],
                callback_data="est_where_mat_" + str(object_id) + "_" + code
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))])
        try:
            await query.edit_message_text(
                "🔍 Где используется материал:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_where: " + str(e), flush=True)
        return

    if data.startswith("est_where_mat_"):
        rest = data.replace("est_where_mat_", "")
        try:
            object_id_s, code = rest.split("_", 1)
            object_id = int(object_id_s)
        except (ValueError, IndexError):
            return
        from core.room_estimate import calc_room_estimate
        from core.db import fetchall
        from core import spec
        rooms = fetchall("SELECT id, name FROM rooms WHERE object_id = ?", (object_id,))
        rows_use = []
        for r in rooms:
            est = calc_room_estimate(r["id"])
            if not est:
                continue
            for m in est.get("materials", []):
                if m["code"] == code:
                    rows_use.append((r["name"], m["qty"], m["unit"], m["cost"]))
        info = spec.MATERIALS_DEFAULT.get(code)
        lines = ["🔍 " + (info[0] if info else code), ""]
        if not rows_use:
            lines.append("   Нигде не используется.")
        else:
            for name, qty, unit, cost in rows_use:
                lines.append(f"   • {name}: {round(qty, 2)} {unit} = {round(cost, 2)} ₽")
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К материалам", callback_data="est_where_" + str(object_id))],
                    [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                ])
            )
        except Exception as e:
            print("est_where_mat: " + str(e), flush=True)
        return

    if data.startswith("est_buy_"):
        try:
            object_id = int(data.replace("est_buy_", ""))
        except ValueError:
            return
        from core.room_estimate import calc_room_estimate
        from core.db import fetchall
        rooms = fetchall("SELECT id, name FROM rooms WHERE object_id = ?", (object_id,))
        agg = {}
        for r in rooms:
            est = calc_room_estimate(r["id"])
            if not est:
                continue
            for m in est.get("materials", []):
                key = m["code"]
                if key not in agg:
                    agg[key] = {"name": m["name"], "unit": m["unit"], "qty": 0.0}
                agg[key]["qty"] += m["qty"]
        if not agg:
            try:
                await query.edit_message_text("🛒 Список закупки пуст.")
            except Exception:
                pass
            return
        import csv
        path = "/tmp/buy_" + str(object_id) + ".csv"
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Материал", "Кол-во", "Ед."])
            for code, info in sorted(agg.items()):
                w.writerow([info["name"], round(info["qty"], 2), info["unit"]])
        obj = get_object(object_id)
        name = obj.get("name") if obj else ("obj_" + str(object_id))
        try:
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_buy.csv",
                    caption="🛒 Список закупки материалов объекта «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("est_buy: " + str(e), flush=True)
        return

    if data.startswith("est_status_"):
        try:
            object_id = int(data.replace("est_status_", ""))
        except ValueError:
            return
        from core.db import fetchone, commit
        row = fetchone("SELECT key, value FROM system_settings WHERE key = ?", ("estimate_status_" + str(object_id),))
        cur = (dict(row).get("value") if row else "draft") or "draft"
        labels = {"draft": "📝 Черновик", "approved": "✅ Согласована", "invoiced": "📄 Выставлена", "paid": "💰 Оплачена"}
        lines = ["📊 Статус сметы объекта", "", "Сейчас: " + labels.get(cur, cur)]
        kb_rows = []
        for st, lab in labels.items():
            if st == cur:
                continue
            kb_rows.append([InlineKeyboardButton(lab, callback_data="est_setstatus_" + str(object_id) + "_" + st)])
        kb_rows.append([InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))])
        try:
            await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(kb_rows))
        except Exception as e:
            print("est_status: " + str(e), flush=True)
        return

    if data.startswith("est_setstatus_"):
        rest = data.replace("est_setstatus_", "")
        try:
            object_id_s, st = rest.rsplit("_", 1)
            object_id = int(object_id_s)
        except (ValueError, IndexError):
            return
        from core.db import fetchone, commit
        key = "estimate_status_" + str(object_id)
        existing = fetchone("SELECT key FROM system_settings WHERE key = ?", (key,))
        if existing:
            commit("UPDATE system_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?", (st, key))
        else:
            commit("INSERT INTO system_settings (key, value) VALUES (?, ?)", (key, st))
        try:
            await query.answer("✅ Статус изменён")
        except Exception:
            pass
        try:
            await query.edit_message_text(
                "✅ Статус сметы: " + st,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                ])
            )
        except Exception as e:
            print("est_setstatus: " + str(e), flush=True)
        return

    if data.startswith("est_allwork_"):
        try:
            object_id = int(data.replace("est_allwork_", ""))
        except ValueError:
            return
        from core.room_estimate import calc_room_estimate
        from core.db import fetchall
        rooms = fetchall("SELECT id FROM rooms WHERE object_id = ?", (object_id,))
        agg = {}
        total_h = 0.0
        for r in rooms:
            est = calc_room_estimate(r["id"])
            if not est:
                continue
            for w in est.get("works", []):
                key = w["code"]
                if key not in agg:
                    agg[key] = {"name": w["name"], "unit": w["unit"], "qty": 0.0, "cost": 0.0, "hours": 0.0}
                agg[key]["qty"] += w["qty"]
                agg[key]["cost"] += w["cost"]
                agg[key]["hours"] += w["hours"]
                total_h += w["hours"]
        if not agg:
            try:
                await query.edit_message_text(
                    "👷 Работы объекта\n\nРабот нет.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
            return
        lines = ["👷 Работы объекта (все комнаты):", ""]
        total = 0.0
        for code, info in sorted(agg.items(), key=lambda x: -x[1]["cost"]):
            lines.append(f"   • {info['name']}: {round(info['qty'], 2)} {info['unit']} = {round(info['cost'], 2)} ₽ ({round(info['hours'], 2)} ч)")
            total += info["cost"]
        lines.append("")
        lines.append(f"💰 Итого работы: {round(total, 2)} ₽ ({round(total_h, 2)} ч)")
        text = chr(10).join(lines)
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
            print("est_allwork: " + str(e), flush=True)
        return

    if data.startswith("est_allmat_"):
        try:
            object_id = int(data.replace("est_allmat_", ""))
        except ValueError:
            return
        from core.object_estimate import calc_object_estimate
        from core.room_estimate import calc_room_estimate
        from core.db import fetchall
        rooms = fetchall("SELECT id FROM rooms WHERE object_id = ?", (object_id,))
        agg = {}
        for r in rooms:
            est = calc_room_estimate(r["id"])
            if not est:
                continue
            for m in est.get("materials", []):
                key = m["code"]
                if key not in agg:
                    agg[key] = {"name": m["name"], "unit": m["unit"], "qty": 0.0, "cost": 0.0}
                agg[key]["qty"] += m["qty"]
                agg[key]["cost"] += m["cost"]
        if not agg:
            try:
                await query.edit_message_text(
                    "🧱 Материалы объекта\n\nМатериалов нет.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
            return
        lines = ["🧱 Материалы объекта (все комнаты):", ""]
        total = 0.0
        for code, info in sorted(agg.items(), key=lambda x: -x[1]["cost"]):
            lines.append(f"   • {info['name']}: {round(info['qty'], 2)} {info['unit']} = {round(info['cost'], 2)} ₽")
            total += info["cost"]
        lines.append("")
        lines.append(f"💰 Итого материалы: {round(total, 2)} ₽")
        text = chr(10).join(lines)
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
            print("est_allmat: " + str(e), flush=True)
        return

    if data.startswith("est_object_floors_"):
        try:
            object_id = int(data.replace("est_object_floors_", ""))
        except ValueError:
            return
        from core.db import fetchall
        floors = fetchall(
            "SELECT id, floor_name, floor_number, type FROM floors WHERE object_id = ? ORDER BY floor_number, id",
            (object_id,)
        )
        if not floors:
            try:
                await query.edit_message_text(
                    "🏢 По этажам\n\nПомещений нет.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
            return
        from core.floor_estimate import calc_floor_estimate
        kb_rows = []
        for fl in floors[:20]:
            fid = fl["id"]
            est = calc_floor_estimate(fid)
            total = est["total"] if est else 0
            name = fl.get("floor_name") or f"Этаж {fl.get('floor_number')}"
            kb_rows.append([InlineKeyboardButton(
                "🏢 " + str(name)[:25] + " — " + str(int(total)) + " ₽",
                callback_data="floor_estimate_" + str(fid)
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))])
        try:
            await query.edit_message_text(
                "🏢 Сметы по этажам:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_object_floors: " + str(e), flush=True)
        return

    if data.startswith("est_object_rooms_"):
        try:
            object_id = int(data.replace("est_object_rooms_", ""))
        except ValueError:
            return
        from core.object_estimate import calc_object_estimate
        data_est = calc_object_estimate(object_id)
        if not data_est or not data_est.get('rooms'):
            try:
                await query.edit_message_text(
                    "🏠 По комнатам\n\nПока комнат нет.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
            return
        kb_rows = []
        for r in data_est['rooms'][:20]:
            kb_rows.append([InlineKeyboardButton(
                "🏠 " + str(r['name'])[:30] + " — " + str(int(r['total'])) + " ₽",
                callback_data="est_room_" + str(r['room_id'])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К смете", callback_data="est_object_" + str(object_id))])
        try:
            await query.edit_message_text(
                "🏠 Сметы по комнатам объекта «" + str(data_est['object_name']) + "»:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return

    if data.startswith("est_room_per_"):
        try:
            room_id = int(data.replace("est_room_per_", ""))
        except ValueError:
            return
        from core.db import fetchone
        from core.rooms import get_room
        room = get_room(room_id)
        if not room:
            return
        object_id = room.get("object_id")
        sessions = __import__("core.sessions", fromlist=["list_sessions"]).list_sessions(room_id)
        if not sessions:
            try:
                await query.edit_message_text(
                    "📅 Сессий замеров нет.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К смете", callback_data="est_room_" + str(room_id))],
                    ])
                )
            except Exception:
                pass
            return
        kb_rows = []
        for s in sessions[:10]:
            st = s.get("session_type") or "?"
            lab = s.get("session_label") or st
            kb_rows.append([InlineKeyboardButton(
                "📅 " + str(lab)[:30] + " (" + str(s.get("created_at", ""))[:10] + ")",
                callback_data="est_room_sess_" + str(room_id) + "_" + str(s["id"])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К смете", callback_data="est_room_" + str(room_id))])
        try:
            await query.edit_message_text(
                "📅 Сессии замеров комнаты:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_room_per: " + str(e), flush=True)
        return

    if data.startswith("est_room_sess_"):
        parts = data.replace("est_room_sess_", "").split("_")
        try:
            room_id = int(parts[0])
            session_id = int(parts[1])
        except (ValueError, IndexError):
            return
        from core.room_estimate import calc_room_estimate
        est = calc_room_estimate(room_id, session_id=session_id)
        if not est:
            return
        lines = [
            "📅 Смета по сессии #" + str(session_id),
            "",
            f"🧱 Материалы: {est['total_materials']} ₽",
            f"👷 Работы:    {est['total_works']} ₽ ({est['total_hours']} ч)",
            f"💰 ВСЕГО:     {est['total']} ₽",
        ]
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К сессиям", callback_data="est_room_per_" + str(room_id))],
                    [InlineKeyboardButton("⬅️ К смете", callback_data="est_room_" + str(room_id))],
                ])
            )
        except Exception as e:
            print("est_room_sess: " + str(e), flush=True)
        return

    if data.startswith("est_room_mat_"):
        try:
            room_id = int(data.replace("est_room_mat_", ""))
        except ValueError:
            return
        from core.room_estimate import format_room_materials_only
        text = format_room_materials_only(room_id).replace("*", "")
        if len(text) > 4000:
            text = text[:3900] + chr(10) + chr(10) + "..."
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К смете комнаты", callback_data="est_room_" + str(room_id))],
                ])
            )
        except Exception as e:
            print("est_room_mat: " + str(e), flush=True)
        return

    if data.startswith("est_room_work_"):
        try:
            room_id = int(data.replace("est_room_work_", ""))
        except ValueError:
            return
        from core.room_estimate import format_room_works_only
        text = format_room_works_only(room_id).replace("*", "")
        if len(text) > 4000:
            text = text[:3900] + chr(10) + chr(10) + "..."
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К смете комнаты", callback_data="est_room_" + str(room_id))],
                ])
            )
        except Exception as e:
            print("est_room_work: " + str(e), flush=True)
        return

    # === Домен: estimates (est_room_*, est_object_* — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    if data == "menu_estimates":
        try:
            objs = get_all_objects()
        except Exception as e:
            print("menu_estimates objs: " + str(e), flush=True)
            objs = []
        if not objs:
            try:
                await query.edit_message_text(
                    "💰 Сметы\n\nПока нет объектов.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
                    ])
                )
            except Exception:
                pass
            return
        kb_rows = []
        for o in objs[:20]:
            kb_rows.append([InlineKeyboardButton(
                "🏗️ " + str(o.get('name') or '?')[:40],
                callback_data="est_object_" + str(o['id'])
            )])
        kb_rows.append([InlineKeyboardButton("📊 Дашборд смет", callback_data="est_dash")])
        kb_rows.append([InlineKeyboardButton("📤 Экспорт всех смет", callback_data="est_export_all")])
        kb_rows.append([InlineKeyboardButton("⚡ KPI мастеров", callback_data="est_kpi_masters")])
        kb_rows.append([InlineKeyboardButton("🏗️ Здоровье объектов", callback_data="est_kpi_objs")])
        kb_rows.append([InlineKeyboardButton("🚨 Красная зона", callback_data="est_kpi_red")])
        kb_rows.append([InlineKeyboardButton("📋 Все сметы (сводка)", callback_data="est_all")])
        kb_rows.append([InlineKeyboardButton("📥 Импорт прайса (CSV)", callback_data="est_import")])
        kb_rows.append([InlineKeyboardButton("🏷 По типу объекта", callback_data="est_bykind")])
        kb_rows.append([InlineKeyboardButton("⚖️ Сравнить объекты", callback_data="est_compare")])
        kb_rows.append([InlineKeyboardButton("🔍 Найти", callback_data="est_search")])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
        try:
            await query.edit_message_text(
                "💰 *Сметы*\n\nВыбери объект:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return

    if data == "est_compare":
        objs = get_all_objects()[:10]
        kb_rows = []
        for o in objs:
            kb_rows.append([InlineKeyboardButton(
                "🏗️ " + str(o.get("name"))[:40],
                callback_data="est_cmp_a_" + str(o["id"])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")])
        try:
            await query.edit_message_text(
                "⚖️ Сравнение смет объектов" + chr(10) + chr(10) + "Выбери первый объект:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_compare: " + str(e), flush=True)
        return

    if data.startswith("est_cmp_a_"):
        a_id = int(data.replace("est_cmp_a_", ""))
        objs = get_all_objects()[:10]
        kb_rows = []
        for o in objs:
            if o["id"] == a_id:
                continue
            kb_rows.append([InlineKeyboardButton(
                "🏗️ " + str(o.get("name"))[:40],
                callback_data="est_cmp_b_" + str(a_id) + "_" + str(o["id"])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="est_compare")])
        try:
            await query.edit_message_text(
                "⚖️ Теперь выбери второй объект:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_cmp_a: " + str(e), flush=True)
        return

    if data.startswith("est_cmp_b_"):
        parts = data.replace("est_cmp_b_", "").split("_")
        a_id, b_id = int(parts[0]), int(parts[1])
        from core.object_estimate import calc_object_estimate
        a = calc_object_estimate(a_id)
        b = calc_object_estimate(b_id)
        an = get_object(a_id)
        bn = get_object(b_id)
        aname = an.get("name") if an else "?"
        bname = bn.get("name") if bn else "?"
        lines = ["⚖️ Сравнение смет", ""]
        lines.append("🏗️ " + str(aname)[:30])
        lines.append("   Материалы: " + str(a.get("total_materials", 0)))
        lines.append("   Работы:    " + str(a.get("total_works", 0)))
        lines.append("   ЭОМ:       " + str(a.get("elec", 0)))
        lines.append("   Сантехника:" + str(a.get("plumbing", 0)))
        lines.append("   ВСЕГО:     " + str(a.get("total", 0)))
        lines.append("")
        lines.append("🏗️ " + str(bname)[:30])
        lines.append("   Материалы: " + str(b.get("total_materials", 0)))
        lines.append("   Работы:    " + str(b.get("total_works", 0)))
        lines.append("   ЭОМ:       " + str(b.get("elec", 0)))
        lines.append("   Сантехника:" + str(b.get("plumbing", 0)))
        lines.append("   ВСЕГО:     " + str(b.get("total", 0)))
        lines.append("")
        diff = b.get("total", 0) - a.get("total", 0)
        lines.append("📊 Разница: " + str(round(diff, 2)) + " ₽")
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К сравнению", callback_data="est_compare")],
                    [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
                ])
            )
        except Exception as e:
            print("est_cmp_b: " + str(e), flush=True)
        return

    if data == "est_bykind":
        objs = get_all_objects()
        groups = {}
        for o in objs:
            k = (o.get("object_kind") or o.get("status") or "прочее").lower()
            groups.setdefault(k, []).append(o)
        lines = ["🏷 Объекты по типу:", ""]
        for kind, items in groups.items():
            lines.append(f"   ▸ {kind}: {len(items)} шт.")
        lines.append("")
        lines.append("Выбери тип:")
        kb_rows = []
        for kind, items in list(groups.items())[:8]:
            kb_rows.append([InlineKeyboardButton(
                "🏷 " + str(kind)[:30] + " (" + str(len(items)) + ")",
                callback_data="est_kind_" + kind[:30]
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_bykind: " + str(e), flush=True)
        return

    if data.startswith("est_kind_"):
        kind = data.replace("est_kind_", "")
        objs = get_all_objects()
        matched = [o for o in objs if ((o.get("object_kind") or o.get("status") or "прочее").lower()[:30] == kind)]
        kb_rows = []
        for o in matched[:20]:
            kb_rows.append([InlineKeyboardButton(
                "🏗️ " + str(o.get("name"))[:40],
                callback_data="est_object_" + str(o["id"])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="est_bykind")])
        try:
            await query.edit_message_text(
                "🏷 " + kind + " (" + str(len(matched)) + "):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("est_kind: " + str(e), flush=True)
        return

    if data == "est_import":
        from core.marketplaces import generate_csv_template
        try:
            path = generate_csv_template("/tmp/prices_template.csv")
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename="prices_template.csv",
                    caption=(
                        "📥 Шаблон прайса (CSV)" + chr(10) + chr(10) +
                        "Заполни и пришли обратно файл — импортирую цены." + chr(10) + chr(10) +
                        "Формат: component_type;rating;poles;brand;price;currency;market_url;market_sku"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
                    ])
                )
        except Exception as e:
            print("est_import: " + str(e), flush=True)
        return

    # === Домен: estimates (est_kpi_* вынесено в callbacks/estimates.py, сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    # === Домен: estimates (est_export_all, est_dash, est_all, est_search — сессия 16) ===
    from handlers.commands.callbacks.estimates import try_handle as _try_estimates_cb
    if await _try_estimates_cb(data, query, context):
        return
    
    if data == "menu_objects":
        objs = get_all_objects()
        if not objs:
            await query.edit_message_text("🏗️ Объектов пока нет")
            return
        await query.edit_message_text(
            f"🏗️ **Объекты ({len(objs)}):**\n\nНажми на объект:",
            reply_markup=objects_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "menu_tasks":
        from datetime import datetime, date, timedelta
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT t.id, t.title, t.deadline, o.name as object_name
            FROM tasks t
            LEFT JOIN objects o ON t.object_id = o.id
            WHERE t.status IN ('open', 'in_progress')
            ORDER BY t.deadline IS NULL, t.deadline ASC
        """)
        rows = c.fetchall()
        conn.close()

        if not rows:
            await query.edit_message_text("Нет активных задач")
            return

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Группируем по датам
        sections = []
        today_tasks = [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() == today]
        tomorrow_tasks = [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() == tomorrow]
        later_tasks = sorted(
            [r for r in rows if r['deadline'] and datetime.strptime(r['deadline'], '%Y-%m-%d').date() > tomorrow],
            key=lambda x: x['deadline']
        )
        no_deadline = [r for r in rows if not r['deadline']]

        if today_tasks:
            sections.append(format_tasks_block(f"СЕГОДНЯ — {today.strftime('%d.%m.%Y')}", today_tasks, '🔥'))
        if tomorrow_tasks:
            sections.append(format_tasks_block(f"ЗАВТРА — {tomorrow.strftime('%d.%m.%Y')}", tomorrow_tasks, '📅'))
        if later_tasks:
            sections.append(format_tasks_block("ПОЗЖЕ", later_tasks, '🗓'))
        if no_deadline:
            sections.append(format_tasks_block("БЕЗ СРОКА", no_deadline, '📋'))

        text = "📋 ЗАДАЧИ\n\n" + "\n\n".join(sections)
        if len(text) > 4000:
            text = text[:3900] + "\n\n..."

        # Кнопки задач (макс 20), по порядку важности
        buttons = []
        task_order = today_tasks + tomorrow_tasks + later_tasks + no_deadline
        for i, r in enumerate(task_order[:20], start=1):
            buttons.append([InlineKeyboardButton(
                f"{i}. {r['title'][:40]}",
                callback_data=f"task_{r['id']}"
            )])
        buttons.append([InlineKeyboardButton("👤 Мои задачи", callback_data="my_tasks"),
                        InlineKeyboardButton("👥 По исполнителям", callback_data="by_assignee")])
        try:
            from modules import tasks as _t_arch
            _arch_n = len(_t_arch.get_archived_tasks())
        except Exception:
            _arch_n = 0
        if _arch_n:
            buttons.append([InlineKeyboardButton("🗑 Архив (" + str(_arch_n) + ")", callback_data="tasks_archive_list")])
        buttons.append([InlineKeyboardButton("🏗️ По объектам", callback_data="tasks_byobj")])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
        await query.edit_message_text(
            text + "\n\nВыбери задачу:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data == "my_tasks":
        from modules.tasks import get_tasks_by_assignee
        user_id = update.effective_user.id
        my = get_tasks_by_assignee(user_id)
        if not my:
            await query.edit_message_text(
                "👤 У тебя нет назначенных задач.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data="menu_tasks")],
                ])
            )
            return
        text = f"👤 МОИ ЗАДАЧИ ({len(my)}):\n\n"
        buttons = []
        for i, t in enumerate(my[:20], start=1):
            d = ''
            if t['deadline']:
                d = f" ({t['deadline'][:10]})"
            obj = t['object_name'] or 'без объекта'
            text += f"#{t['id']} {t['title']}{d} — {obj}\n"
            buttons.append([InlineKeyboardButton(f"{i}. {t['title'][:40]}", callback_data=f"task_{t['id']}")])
        buttons.append([InlineKeyboardButton("⬅️ К задачам", callback_data="menu_tasks")])
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return
    if data == "by_assignee":
        from modules.users import get_all_users
        from modules.tasks import get_tasks_by_assignee
        users = get_all_users()
        users = [u for u in users if u.get('role') in ('master', 'prorab', 'designer', 'admin')]
        buttons = []
        for u in users:
            cnt = len(get_tasks_by_assignee(u['tg_id']))
            label = f"👤 {u.get('name', '—')[:30]} ({cnt})"
            buttons.append([InlineKeyboardButton(label, callback_data=f"byassignee_{u['tg_id']}")])
        buttons.append([InlineKeyboardButton("⬅️ К задачам", callback_data="menu_tasks")])
        try:
            await query.edit_message_text(
                "👥 Задачи по исполнителям:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return

    if data.startswith("byassignee_"):
        from modules.tasks import get_tasks_by_assignee
        from modules.users import get_user
        tg_id = int(data.replace("byassignee_", ""))
        tasks = get_tasks_by_assignee(tg_id)
        u = get_user(tg_id)
        uname = u.get('name') if u else f'id{tg_id}'
        if not tasks:
            try:
                await query.edit_message_text(
                    f"👤 {uname}\n\nНет активных задач.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data="by_assignee")],
                    ])
                )
            except Exception as e:
                if 'not modified' not in str(e).lower():
                    raise
            return
        text = f"👤 {uname} — {len(tasks)} задач:\n\n"
        buttons = []
        for i, t in enumerate(tasks[:20], start=1):
            d = ''
            if t['deadline']:
                d = f" ({t['deadline'][:10]})"
            obj = t['object_name'] or 'без объекта'
            text += f"#{t['id']} {t['title']}{d} — {obj}\n"
            buttons.append([InlineKeyboardButton(f"{i}. {t['title'][:40]}", callback_data=f"task_{t['id']}")])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="by_assignee")])
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            if 'not modified' not in str(e).lower():
                raise
        return

    if data == "menu_kpi":
        await query.edit_message_text(
            "📊 KPI И АНАЛИТИКА\n\n"
            "Выбери отчёт:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 KPI мастеров (30 дн.)", callback_data="kpi_masters")],
                [InlineKeyboardButton("🏗️ Здоровье объектов", callback_data="kpi_objects")],
                [InlineKeyboardButton("⚠️ Красная зона", callback_data="kpi_red")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
            ])
        )
        return

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
        return

    if data == "kpi_objects":
        from modules.kpi import get_object_health, format_object_health
        objects = get_object_health()
        text = format_object_health(objects)
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
        return

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
        return

    if data == "menu_finance":
        await query.edit_message_text(
            format_finance_summary(),
            reply_markup=finance_keyboard()
        )
        return

    if data.startswith("finobj_"):
        object_id = int(data.split("_")[1])
        obj = get_object(object_id)
        if not obj:
            await query.edit_message_text("❌ Объект не найден")
            return
        f = get_finance_summary(object_id)
        await query.edit_message_text(
            f"💰 **{obj['name']}**\n\n"
            f"Доход: {format_money(f['income'])} ₽\n"
            f"Расход: {format_money(f['expense'])} ₽\n"
            f"Баланс: {format_money(f['balance'])} ₽",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К финансам", callback_data="menu_finance")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data == "menu_personal":
        await query.edit_message_text(
            format_personal_summary('month'),
            reply_markup=personal_keyboard()
        )
        return

    if data == "personal_today":
        try:
            await query.edit_message_text(
                format_personal_summary('today'),
                reply_markup=personal_keyboard()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"personal_today: {_e}", flush=True)
        return

    if data == "personal_week":
        try:
            await query.edit_message_text(
                format_personal_summary('week'),
                reply_markup=personal_keyboard()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"personal_week: {_e}", flush=True)
        return

    if data == "personal_month":
        try:
            await query.edit_message_text(
                format_personal_summary('month'),
                reply_markup=personal_keyboard()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"personal_month: {_e}", flush=True)
        return

    if data == "personal_all":
        try:
            await query.edit_message_text(
                format_personal_summary('all'),
                reply_markup=personal_keyboard()
            )
        except Exception as _e:
            if "Message is not modified" not in str(_e):
                print(f"personal_all: {_e}", flush=True)
        return

    if data == "personal_add":
        context.user_data['waiting_for'] = 'personal_expense_text'
        await query.edit_message_text(
            "💸 Новый личный расход\n\nНапиши сумму и категорию. Например:\n"
            "«300 еда»\n«1500 инструмент»\n«200 такси»",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_personal")]
            ])
        )
        return

    # === ВЫБОР: ЛИЧНЫЙ ИЛИ ПО ОБЪЕКТУ ===
    if data.startswith("exp_type_personal_"):
        amount = int(data.replace("exp_type_personal_", ""))
        context.user_data['pending_personal_expense'] = amount
        context.user_data['waiting_for'] = 'personal_expense_category'
        await query.edit_message_text(
            f"💸 Личный расход {amount} ₽\n\nЗа что?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🍔 Еда", callback_data=f"personal_cat_{amount}_еда")],
                [InlineKeyboardButton("🚕 Транспорт", callback_data=f"personal_cat_{amount}_транспорт")],
                [InlineKeyboardButton("🏠 Жильё", callback_data=f"personal_cat_{amount}_жильё")],
                [InlineKeyboardButton("💊 Медицина", callback_data=f"personal_cat_{amount}_медицина")],
                [InlineKeyboardButton("👕 Одежда", callback_data=f"personal_cat_{amount}_одежда")],
                [InlineKeyboardButton("📱 Связь", callback_data=f"personal_cat_{amount}_связь")],
                [InlineKeyboardButton("📦 Прочее", callback_data=f"personal_cat_{amount}_прочее")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_back")],
            ])
        )
        return

    if data.startswith("exp_type_object_"):
        amount = int(data.replace("exp_type_object_", ""))
        context.user_data['pending_object_expense_amount'] = amount
        await query.edit_message_text(
            f"🏗️ Расход {amount} ₽\n\nВыбери объект:",
            reply_markup=choose_object_for_expense_keyboard_amount(amount)
        )
        return

    if data.startswith("personal_cat_"):
        parts = data.replace("personal_cat_", "").split("_", 1)
        amount = int(parts[0])
        category = parts[1]
        add_personal_expense(amount, category)
        context.user_data['pending_personal_expense'] = None
        context.user_data['waiting_for'] = None
        await query.edit_message_text(
            f"✅ Личный расход {amount} ₽ ({category}) записан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 К личным", callback_data="menu_personal")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    if data.startswith("objexp_obj_"):
        # objexp_obj_<amount>_<obj_id>
        parts = data.replace("objexp_obj_", "").split("_")
        amount = int(parts[0])
        obj_id = int(parts[1])
        obj = get_object(obj_id)
        context.user_data['pending_obj_expense'] = {'amount': amount, 'obj_id': obj_id, 'obj_name': obj['name']}
        await query.edit_message_text(
            f"💰 {amount} ₽ в «{obj['name']}»\n\nЗа что?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧱 Материалы", callback_data=f"objexp_cat_{amount}_{obj_id}_материалы")],
                [InlineKeyboardButton("🔧 Инструмент", callback_data=f"objexp_cat_{amount}_{obj_id}_инструмент")],
                [InlineKeyboardButton("🚕 Транспорт", callback_data=f"objexp_cat_{amount}_{obj_id}_транспорт")],
                [InlineKeyboardButton("🍔 Еда", callback_data=f"objexp_cat_{amount}_{obj_id}_еда")],
                [InlineKeyboardButton("📦 Прочее", callback_data=f"objexp_cat_{amount}_{obj_id}_прочее")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_back")],
            ])
        )
        return

    if data.startswith("objexp_cat_"):
        # objexp_cat_<amount>_<obj_id>_<category>
        parts = data.replace("objexp_cat_", "").split("_", 2)
        amount = int(parts[0])
        obj_id = int(parts[1])
        category = parts[2] if len(parts) > 2 else 'прочее'
        obj = get_object(obj_id)
        add_expense(obj_id, amount, category)
        context.user_data['pending_object_expense_amount'] = None
        await query.edit_message_text(
            f"✅ Расход {amount} ₽ ({category}) в «{obj['name']}»",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ К объекту", callback_data=f"obj_{obj_id}")],
                [InlineKeyboardButton("💰 К финансам", callback_data="menu_finance")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    # === ОТЧЁТЫ ===
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
                [InlineKeyboardButton("🏗️ Отчёт по объекту", callback_data="report_choose_object")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")],
            ])
        )
        return

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
        return

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
        return

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
        return

    if data == "report_choose_object":
        objs = get_all_objects()
        buttons = []
        for o in objs:
            buttons.append([InlineKeyboardButton(
                f"🏗️ {o['name']}",
                callback_data=f"report_obj_{o['id']}_month"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_reports")])
        await query.edit_message_text(
            "📊 Выбери объект для отчёта (за месяц):",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

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
                [InlineKeyboardButton("📸 Фото объекта", callback_data=f"objphotos_{obj_id}")],
                [InlineKeyboardButton("⬅️ К отчётам", callback_data="menu_reports")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    if data == "menu_dashboard":
        from modules.dashboard_link import get_dashboard_url
        url = get_dashboard_url()
        await query.edit_message_text(
            f"🌐 Дашборд Бо 7.7\n\n"
            f"Нажми кнопку ниже, чтобы открыть:\n\n"
            f"📱 Совет: добавь на главный экран телефона",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 Открыть дашборд", url=url)],
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")]
            ])
        )
        return

    if data == "menu_help":
        await query.edit_message_text(
            _help_text(),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Задачи без объекта
    if data == "objtasks_none":
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, title, status FROM tasks WHERE object_id IS NULL AND status IN ('open', 'in_progress') ORDER BY id")
        _no_obj_tasks = c.fetchall()
        conn.close()
        if not _no_obj_tasks:
            await query.edit_message_text("📋 Задач без объекта нет", reply_markup=tasks_keyboard_by_object())
            return
        text = "🚫 **Задачи без объекта:**\n\n"
        for t in _no_obj_tasks[:20]:
            icon = "✅" if t['status'] == 'done' else "🔵"
            text += f"{icon} {t['id']}. {t['title']}\n"
        await query.edit_message_text(text, reply_markup=tasks_keyboard_by_object())
        return
    
    if data.startswith("objtasks_"):
        object_id = int(data.split("_")[1])
        tasks = get_tasks_by_object(object_id)
        if not tasks:
            await query.edit_message_text("📋 Задач нет", reply_markup=object_detail_keyboard(object_id))
            return
        text = "📋 **Задачи объекта:**\n\n"
        for t in tasks[:20]:
            icon = "✅" if t['status'] == 'done' else "🔵"
            text += f"{icon} {t['id']}. {t['title']}\n"
        await query.edit_message_text(text, reply_markup=object_detail_keyboard(object_id), parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("objfin_"):
        object_id = int(data.split("_")[1])
        f = get_finance_summary(object_id)
        await query.edit_message_text(
            f"💰 **Финансы**\n\nДоход: {f['income']} ₽\nРасход: {f['expense']} ₽\nБаланс: {f['balance']} ₽",
            reply_markup=object_detail_keyboard(object_id),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("objphotos_"):
        object_id = int(data.split("_")[1])
        obj = get_object(object_id)
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM photos WHERE object_id = ?", (object_id,))
        total = c.fetchone()[0] or 0
        conn.close()

        if total == 0:
            await query.edit_message_text(
                f"📸 Фото объекта «{obj['name']}»\n\nПока нет фото.\n\n"
                f"Отправь боту фото, чтобы добавить.",
                reply_markup=object_detail_keyboard(object_id)
            )
            return

        await query.edit_message_text(
            f"📸 *Фото «{obj['name']}»*\n"
            f"Всего: {total}\n\n"
            f"Выбери фильтр:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆕 Последние (3 задачи)", callback_data=f"photofilt_last_{object_id}_0")],
                [InlineKeyboardButton("📋 По задачам", callback_data=f"photofilt_tasks_{object_id}")],
                [InlineKeyboardButton("📅 По датам", callback_data=f"photofilt_dates_{object_id}")],
                [InlineKeyboardButton("👤 Кто загрузил", callback_data=f"photofilt_uploaders_{object_id}")],
                [InlineKeyboardButton("🛠 Кто делал задачу", callback_data=f"photofilt_assignees_{object_id}")],
                [InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")],
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if data.startswith("obj_"):
        object_id = int(data.split("_")[1])
        obj = get_object(object_id)
        if not obj:
            await query.edit_message_text("❌ Объект не найден")
            return
        tasks = get_tasks_by_object(object_id)
        open_tasks = len([t for t in tasks if t['status'] == 'open'])
        f = get_finance_summary(object_id)
        text = (
            f"🏗️ **{obj['name']}**\n\n"
            f"**Статус:** {obj['status']}\n"
            f"**Бюджет:** {obj['budget']} ₽\n"
            f"**Задачи:** {open_tasks} открытых\n"
            f"**Доход:** {f['income']} ₽\n"
            f"**Расход:** {f['expense']} ₽\n"
            f"**Баланс:** {f['balance']} ₽"
        )
        await query.edit_message_text(text, reply_markup=object_detail_keyboard(object_id), parse_mode=ParseMode.MARKDOWN)
        return




async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # --- ПОИСК ПО СМЕТАМ ---
    if getattr(__import__('handlers.commands', fromlist=['_est_search_pending']), '_est_search_pending', False):
        import handlers.commands as _cmd
        _cmd._est_search_pending = False
        q = text.strip().lower()
        if not q:
            await update.message.reply_text("❌ Пустой запрос")
            return
        objs = get_all_objects()
        matched = [o for o in objs if q in (o.get('name') or '').lower()]
        if not matched:
            await update.message.reply_text(
                "🔍 Не найдено: " + text.strip(),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")],
                ])
            )
            return
        kb_rows = []
        for o in matched[:10]:
            kb_rows.append([InlineKeyboardButton(
                "🏗️ " + str(o.get('name'))[:40],
                callback_data="est_object_" + str(o['id'])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К сметам", callback_data="menu_estimates")])
        await update.message.reply_text(
            "🔍 Найдено: " + str(len(matched)),
            reply_markup=InlineKeyboardMarkup(kb_rows)
        )
        return

    # --- ОТДЕЛЬНЫЕ РАБОТЫ ---
    _pend = getattr(__import__('handlers.commands', fromlist=['_est_extra_pending']), '_est_extra_pending', None)
    if _pend and isinstance(_pend, dict):
        step = _pend.get('step')
        object_id = _pend.get('object_id')
        if step == 'title':
            _pend['title'] = text.strip()
            _pend['step'] = 'qty'
            await update.message.reply_text(
                "🔨 " + text.strip() + "\n\nКоличество (число):"
            )
            return
        elif step == 'qty':
            try:
                q = float(text.replace(',', '.'))
            except ValueError:
                await update.message.reply_text("❌ Нужно число")
                return
            _pend['qty'] = q
            _pend['step'] = 'price'
            await update.message.reply_text(
                "🔨 " + _pend['title'] + "\nКол-во: " + str(q) + "\n\nЦена за единицу (₽):"
            )
            return
        elif step == 'price':
            try:
                p = float(text.replace(',', '.'))
            except ValueError:
                await update.message.reply_text("❌ Нужно число")
                return
            from core.extra_works import add_extra_work
            wid = add_extra_work(
                object_id=object_id,
                title=_pend['title'],
                qty=_pend['qty'],
                price=p,
                unit='шт',
            )
            import handlers.commands as _cmd
            _cmd._est_extra_pending = None
            await update.message.reply_text(
                "✅ Работа добавлена!\n\n🔨 " + _pend['title'] + "\nКол-во: " + str(_pend['qty']) + " × " + str(p) + " ₽",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К работам", callback_data="est_extra_" + str(object_id))],
                ])
            )
            return
    # DEBUG: печатаем всё, что приходит
    try:
        with open('/tmp/handle_text.log', 'a') as _f:
            _f.write(f"HANDLE_TEXT: text={text!r}, waiting_for={context.user_data.get('waiting_for')!r}\n")
    except Exception:
        pass
    print(f"🔵 HANDLE_TEXT: text={text!r}, waiting_for={context.user_data.get('waiting_for')!r}", flush=True)
    if not text or text.startswith('/'):
        print(f"⚠️ RETURN на строке 2283", flush=True)
        return

    # Размеры комнаты
    # room_rename — переименование комнаты
    if context.user_data.get('waiting_for') == 'room_rename':
        room_id = context.user_data.get('room_rename_id')
        new_name = text.strip()
        if room_id and new_name:
            from core.db import commit
            commit("UPDATE rooms SET name = ? WHERE id = ?", (new_name, room_id))
            context.user_data['waiting_for'] = None
            context.user_data['room_rename_id'] = None
            await update.message.reply_text(
                f"✅ Имя комнаты изменено на «{new_name}»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
            return

    if context.user_data.get('waiting_for') == 'obj_rename':
        object_id = context.user_data.get('obj_rename_id')
        new_name = text.strip()
        if object_id and new_name:
            from modules.objects import update_object
            update_object(object_id, name=new_name)
            context.user_data['waiting_for'] = None
            context.user_data['obj_rename_id'] = None
            await update.message.reply_text(
                f"✅ Имя объекта изменено на «{new_name}»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏗️ К объекту", callback_data=f"obj_{object_id}")],
                ])
            )
            return

    if context.user_data.get("waiting_for") == "panel_comp_rating":
        from core import elec_panels as core_elec_panels
        panel_id = context.user_data.get("panel_comp_panel_id")
        ctype = context.user_data.get("panel_comp_type")
        text_in = text.strip()
        if not panel_id or not ctype:
            await update.message.reply_text("Потерялись данные. Начни заново.")
            context.user_data["waiting_for"] = None
            return
        try:
                import re as _re
                _m = _re.search(r"[0-9]+", text_in)
                if _m is None:
                    await update.message.reply_text("Не нашёл число. Введи номинал, например 16:")
                    return
                rating = int(_m.group())
        except ValueError:
            await update.message.reply_text("Нужно число, например 16. Попробуй ещё раз.")
            return
        try:
            core_elec_panels.add_component(panel_id, component_type=ctype, rating=rating, is_manual=1)
        except Exception as e:
            print("panel comp add: " + str(e), flush=True)
        for k in ["panel_comp_panel_id", "panel_comp_type", "waiting_for"]:
            context.user_data[k] = None
        await update.message.reply_text("✅ Компонент добавлен", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ К щиту", callback_data="panel_" + str(panel_id))],
            [InlineKeyboardButton("📦 К компонентам", callback_data="panel_comp_" + str(panel_id))],
        ]))
        return

    # Дневник работ — шаг 1: часы
    if context.user_data.get("waiting_for") == "task_progress_hours":
        try:
            _h = float((text or "").strip().replace(",", "."))
        except ValueError:
            await update.message.reply_text("⚠️ Нужно число. Сколько часов? Например: 8")
            return
        context.user_data["task_progress_h"] = _h
        context.user_data["waiting_for"] = "task_progress_desc"
        try:
            await update.message.reply_text(
                "📝 Что делал? (одно предложение, можно коротко)",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏭ Пропустить", callback_data=f"taskaddprogskip_{context.user_data.get("task_progress_id",0)}")],
                ])
            )
        except Exception:
            pass
        return

    # Дневник работ — шаг 2: описание
    if context.user_data.get("waiting_for") == "task_progress_desc":
        _tid = context.user_data.get("task_progress_id")
        _h = context.user_data.get("task_progress_h")
        _desc = (text or "").strip()
        if _tid and _h:
            try:
                from modules import tasks as _tasks
                _tasks.add_progress(_tid, hours=_h, description=_desc, source="text")
            except Exception as _e:
                print("add_progress fail: " + str(_e), flush=True)
        for _k in ("task_progress_id", "task_progress_h", "waiting_for"):
            context.user_data.pop(_k, None)
        await update.message.reply_text(
            "✅ Записано: " + str(_h) + "ч — " + (_desc or "без описания"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📓 Дневник", callback_data=f"taskjournal_{_tid}")],
                [InlineKeyboardButton("⬅️ К задаче", callback_data=f"task_{_tid}")],
            ])
        )
        try:
            from handlers.commands import handle_task_action
            # Показать дневник заново
            from modules import tasks as _tasks2
            _rows = _tasks2.get_task_progress(_tid)
            _hrs = _tasks2.calc_task_hours(_tid)
            await update.message.reply_text("📓 Часов всего: " + str(_hrs) + "\n" + _tasks2.format_task_progress(_tid))
        except Exception:
            pass
        return

    if context.user_data.get('waiting_for') in ('floor_new_name', 'panel_new_name', 'child_panel_name', 'component_price', 'route_length', 'plumb_new_name', 'plumb_route_length', 'work_new_qty', 'work_edit_value', 'task_progress_hours', 'task_progress_desc', 'group_load_watt', 'measure_first_dim', 'measure_second_dim', 'wall_angle_value', 'wall_niche_width', 'wall_niche_depth', 'wall_niche_height', 'room_height_point', 'room_height_same', 'wall_round_length', 'wall_round_angle_val', 'wall_round_plane_bottom', 'wall_round_plane_middle', 'wall_round_plane_top', 'opening_width', 'opening_height', 'opening_sill', 'opening_offset', 'opening_edit_value', 'comm_offset_x', 'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_edit_value', 'comm_size', 'comm_size_w', 'comm_size_h', 'comm_size_d', 'comm_edit_size_part', 'wall_round_opening_width', 'wall_round_opening_height', 'comm_offset_x', 'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_edit_value',
                                                  'wall_round_length', 'wall_round_angle_val', 'wall_round_plane_bottom', 'wall_round_plane_middle', 'wall_round_plane_top'):
        from interfaces.telegram.rooms import handle_measure_input
        await handle_measure_input(update, context)
        print(f"⚠️ RETURN на строке 2289", flush=True)
        return

    # Новая комната — просим тип (черновая/чистовая/промежуточная)
    if context.user_data.get('waiting_for') == 'room_name':
        name = text.strip()
        object_id = context.user_data.get('room_object_id')
        context.user_data['room_name_pending'] = name
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"📦 *Новая комната «{name}»*\n\nКакой тип помещения?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧱 Черновая", callback_data=f"room_type_{object_id}_rough")],
                [InlineKeyboardButton("✨ Чистовая", callback_data=f"room_type_{object_id}_finish")],
                [InlineKeyboardButton("🔶 Промежуточная", callback_data=f"room_type_{object_id}_mid")],
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"rooms_list_obj_{object_id}")],
            ])
        )
        print(f"⚠️ RETURN на строке 2307", flush=True)
        return

    # Стена выбрана, но ровная/закругление не нажато → показать кнопки заново
    if context.user_data.get('wall_pos') and context.user_data.get('wall_rounded') is None:
        from interfaces.telegram.rooms import reask_wall_question
        shown = await reask_wall_question(update, context)
        if shown:
            print(f"⚠️ RETURN на строке 2314", flush=True)
            return

    # === ВСЕ CRM-ОЖИДАНИЯ — В САМОМ НАЧАЛЕ, ДО ПАРСЕРА ===

    # CRM: ждём имя нового клиента (для сделки)
    if context.user_data.get('waiting_for') == 'crm_deal_new_client_name':
        name = text.strip()
        context.user_data['crm_new_client_name'] = name
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"👤 Создать клиента «{name}»?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Создать и продолжить сделку", callback_data="crm_new_client_for_deal")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_crm")],
            ])
        )
        print(f"⚠️ RETURN на строке 2330", flush=True)
        return

    # CRM: ждём имя клиента (обычный сценарий)
    if context.user_data.get('waiting_for') == 'crm_client_name':
        context.user_data['crm_new_client_name'] = text.strip()
        context.user_data['waiting_for'] = 'crm_client_phone'
        await update.message.reply_text(
            f"👤 Имя: «{text.strip()}»\n\n📞 Теперь телефон (или Пропустить):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_phone")],
            ])
        )
        print(f"⚠️ RETURN на строке 2342", flush=True)
        return

    if context.user_data.get('waiting_for') == 'crm_client_phone':
        from modules.phone_utils import parse_phone, get_country_label
        raw = text.strip()
        result = parse_phone(raw)
        status = result.get('status')

        if status == 'ok':
            normalized = result['phone']
            country = get_country_label(normalized)
            context.user_data['crm_new_client_phone'] = normalized
            context.user_data['waiting_for'] = 'crm_client_address'
            await update.message.reply_text(
                f"✅ Телефон распознан: {normalized}\n"
                f"{country}\n\n"
                f"📍 Теперь адрес (или Пропустить):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Изменить телефон", callback_data="crm_phone_edit")],
                    [InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_address")],
                ])
            )
            print(f"⚠️ RETURN на строке 2364", flush=True)
            return

        if status == 'suggest':
            variants = result.get('variants', [])
            context.user_data['phone_variants'] = variants
            buttons = []
            for v in variants:
                label = f"📞 {v}"
                buttons.append([InlineKeyboardButton(label, callback_data=f"crm_phone_pick_{v}")])
            buttons.append([InlineKeyboardButton("✏️ Ввести заново", callback_data="crm_phone_edit")])
            buttons.append([InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_phone")])
            await update.message.reply_text(
                f"🤔 Номер «{raw}» нестандартный.\n\n"
                f"Выбери подходящий вариант:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            print(f"⚠️ RETURN на строке 2380", flush=True)
            return

        # invalid
        await update.message.reply_text(
            f"❌ Номер «{raw}» слишком короткий или не распознан.\n\n"
            f"Введи в формате:\n"
            f"• +79991234567 (Россия)\n"
            f"• 89991234567 (Россия)\n"
            f"• 9991234567 (Россия, 10 цифр)\n"
            f"• +491234567890 (Европа)\n\n"
            f"Или нажми «Пропустить».",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Ввести заново", callback_data="crm_phone_edit")],
                [InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_phone")],
            ])
        )
        print(f"⚠️ RETURN на строке 2396", flush=True)
        return

    if context.user_data.get('waiting_for') == 'crm_client_address':
        context.user_data['crm_new_client_address'] = text.strip()
        context.user_data['waiting_for'] = 'crm_client_source'
        phone = context.user_data.get('crm_new_client_phone')
        phone_line = f"📞 Телефон: {phone}\n" if phone else "📞 Телефон: —\n"
        await update.message.reply_text(
            f"📍 Адрес: {text.strip()}\n\n"
            f"{phone_line}\n"
            f"🔗 Откуда узнал? Или Пропустить:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Изменить телефон", callback_data="crm_phone_edit")],
                [InlineKeyboardButton("⏭️ Пропустить", callback_data="crm_skip_source")],
            ])
        )
        print(f"⚠️ RETURN на строке 2412", flush=True)
        return

    if context.user_data.get('waiting_for') == 'crm_client_source':
        context.user_data['crm_new_client_source'] = text.strip()
        await _finalize_new_client(update, context)
        print(f"⚠️ RETURN на строке 2417", flush=True)
        return

    # CRM: ждём бюджет сделки — ВАЖНО до парсера
    if context.user_data.get('waiting_for') == 'crm_deal_budget':
        try:
            budget = parse_amount(text) or 0
        except Exception:
            budget = 0
        client_id = context.user_data.get('crm_deal_client_id')
        if not client_id:
            await update.message.reply_text("❌ Клиент потерялся. Начни заново.")
            context.user_data['waiting_for'] = None
            print(f"⚠️ RETURN на строке 2430", flush=True)
            return
        from modules.crm import add_deal, get_client
        deal_id = add_deal(client_id=client_id, object_id=None, status='new', budget=budget)
        c = get_client(client_id)
        context.user_data['waiting_for'] = None
        context.user_data['crm_deal_client_id'] = None
        await update.message.reply_text(
            f"✅ Сделка #{deal_id} создана!\n\n"
            f"👤 Клиент: {c['name'] if c else '—'}\n"
            f"💼 Бюджет: {budget} ₽\n"
            f"📊 Статус: 🆕 Новая",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 К клиентам", callback_data="crm_clients")],
                [InlineKeyboardButton("💼 К сделкам", callback_data="crm_deals")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        print(f"⚠️ RETURN на строке 2447", flush=True)
        return

    # CRM: пользователь ввёл имя в режиме выбора клиента
    if context.user_data.get('waiting_for') == 'crm_deal_pick_client':
        name = text.strip()
        from modules.crm import get_clients
        clients = get_clients()
        found = None
        for c in clients:
            if c['name'].lower().strip() == name.lower():
                found = c
                break
        if found:
            context.user_data['crm_deal_client_id'] = found['id']
            context.user_data['waiting_for'] = 'crm_deal_budget'
            await update.message.reply_text(
                f"💼 Клиент: «{found['name']}»\n\nНапиши сумму бюджета сделки (₽):"
            )
            print(f"⚠️ RETURN на строке 2465", flush=True)
            return
        else:
            context.user_data['crm_new_client_name'] = name
            context.user_data['waiting_for'] = None
            await update.message.reply_text(
                f"👤 Клиента «{name}» нет в списке.\n\nСоздать нового и продолжить сделку?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Создать и продолжить", callback_data="crm_new_client_for_deal")],
                    [InlineKeyboardButton("⬅️ К списку", callback_data="crm_deal_add")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="menu_crm")],
                ])
            )
            print(f"⚠️ RETURN на строке 2477", flush=True)
            return

    # === ЗАПЛАНИРОВАННЫЙ ЗВОНОК ===
    if context.user_data.get('waiting_for') == 'activity_plan_datetime':
        from modules.crm import add_activity, get_client
        client_id = context.user_data.get('activity_client_id')
        if not client_id:
            context.user_data['waiting_for'] = None
            await update.message.reply_text('❌ Клиент потерялся.')
            print(f"⚠️ RETURN на строке 2487", flush=True)
            return
        # Парсим дату и время из текста
        parsed = parse_date(text)
        due_str = None
        if parsed:
            due_str = parsed.strftime('%Y-%m-%d')
        add_activity(
            client_id=client_id,
            user_id=update.effective_user.id,
            type_='call',
            description=text.strip(),
            due_date=due_str
        )
        cl = get_client(client_id)
        context.user_data['waiting_for'] = None
        context.user_data['activity_client_id'] = None
        context.user_data['activity_type'] = None
        due_display = parsed.strftime('%d.%m.%Y') if parsed else 'без даты'
        await update.message.reply_text(
            f'✅ Звонок запланирован: {due_display}\n👤 {cl["name"] if cl else "—"}',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('👤 К клиенту', callback_data=f'client_{client_id}')],
                [InlineKeyboardButton('📋 Активности', callback_data=f'activity_list_{client_id}')],
            ])
        )
        print(f"⚠️ RETURN на строке 2512", flush=True)
        return

    # === ДИАПАЗОН СРОКА (обработка ввода) ===
    if context.user_data.get('range_step') == 'start':
        d = parse_date(text)
        if not d:
            await update.message.reply_text('❌ Не понял дату начала. Попробуй: «завтра», «1.10», «пн», «10.10.2025»')
            print(f"⚠️ RETURN на строке 2519", flush=True)
            return
        context.user_data['range_start'] = d.strftime('%Y-%m-%d')
        context.user_data['range_step'] = 'end'
        await update.message.reply_text(
            f"📆 Старт: {d.strftime('%d.%m.%Y')}\n\n"
            f"Теперь дата конца:"
        )
        print(f"⚠️ RETURN на строке 2526", flush=True)
        return

    if context.user_data.get('range_step') == 'end':
        d_end = parse_date(text)
        if not d_end:
            await update.message.reply_text('❌ Не понял дату конца. Попробуй: «8.10», «+5», «пятница»')
            print(f"⚠️ RETURN на строке 2532", flush=True)
            return
        task_id = context.user_data.get('range_task')
        start = context.user_data.get('range_start')
        from modules.tasks import set_task_range
        from datetime import datetime as _dt
        d_start = _dt.strptime(start, '%Y-%m-%d').date()
        if d_end < d_start:
            await update.message.reply_text('❌ Конец раньше старта. Введи ещё раз.')
            print(f"⚠️ RETURN на строке 2540", flush=True)
            return
        set_task_range(task_id, start, d_end.strftime('%Y-%m-%d'))
        days = (d_end - d_start).days + 1
        context.user_data['range_step'] = None
        context.user_data['range_task'] = None
        context.user_data['range_start'] = None
        await update.message.reply_text(
            f"✅ Срок: {d_start.strftime('%d.%m.%Y')} — {d_end.strftime('%d.%m.%Y')} ({days} дн.)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('📋 К задаче', callback_data=f'task_{task_id}')],
                [InlineKeyboardButton('🏠 Меню', callback_data='menu_back')],
            ])
        )
        print(f"⚠️ RETURN на строке 2553", flush=True)
        return

    # === ДЛИТЕЛЬНОСТЬ (обработка ввода) ===
    if context.user_data.get('duration_step') == 'start':
        d = parse_date(text)
        if not d:
            await update.message.reply_text('❌ Не понял дату старта. Попробуй: «завтра», «1.10»')
            print(f"⚠️ RETURN на строке 2560", flush=True)
            return
        context.user_data['duration_start'] = d.strftime('%Y-%m-%d')
        context.user_data['duration_step'] = 'days'
        await update.message.reply_text(
            f"⏳ Старт: {d.strftime('%d.%m.%Y')}\n\n"
            f"Сколько дней? Напиши число (например, 3):"
        )
        print(f"⚠️ RETURN на строке 2567", flush=True)
        return

    if context.user_data.get('duration_step') == 'days':
        try:
            n = int(text.strip())
        except ValueError:
            await update.message.reply_text('❌ Нужно число. Напиши, сколько дней.')
            print(f"⚠️ RETURN на строке 2574", flush=True)
            return
        if n < 1 or n > 365:
            await update.message.reply_text('❌ От 1 до 365 дней.')
            print(f"⚠️ RETURN на строке 2577", flush=True)
            return
        task_id = context.user_data.get('duration_task')
        start = context.user_data.get('duration_start')
        from modules.tasks import set_task_range
        from datetime import datetime as _dt, timedelta
        d_start = _dt.strptime(start, '%Y-%m-%d').date()
        d_end = d_start + timedelta(days=n - 1)
        set_task_range(task_id, start, d_end.strftime('%Y-%m-%d'))
        context.user_data['duration_step'] = None
        context.user_data['duration_task'] = None
        context.user_data['duration_start'] = None
        await update.message.reply_text(
            f"✅ Срок: {d_start.strftime('%d.%m.%Y')} — {d_end.strftime('%d.%m.%Y')} ({n} дн.)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('📋 К задаче', callback_data=f'task_{task_id}')],
                [InlineKeyboardButton('🏠 Меню', callback_data='menu_back')],
            ])
        )
        print(f"⚠️ RETURN на строке 2595", flush=True)
        return

    # === АКТИВНОСТИ КЛИЕНТА ===
    if context.user_data.get('waiting_for') == 'activity_text':
        from modules.crm import add_activity, get_client
        client_id = context.user_data.get('activity_client_id')
        atype = context.user_data.get('activity_type')
        if not client_id or not atype:
            context.user_data['waiting_for'] = None
            await update.message.reply_text('❌ Клиент потерялся. Начни заново.')
            print(f"⚠️ RETURN на строке 2605", flush=True)
            return
        add_activity(client_id=client_id, user_id=update.effective_user.id, type_=atype, description=text.strip())
        cl = get_client(client_id)
        context.user_data['waiting_for'] = None
        context.user_data['activity_client_id'] = None
        context.user_data['activity_type'] = None
        type_names = {'call': '📞 Звонок', 'meeting': '🤝 Встреча', 'note': '📝 Заметка'}
        await update.message.reply_text(
            f'✅ {type_names.get(atype, atype)} записан клиенту «{cl["name"] if cl else "—"}»',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('👤 К клиенту', callback_data=f'client_{client_id}')],
                [InlineKeyboardButton('🏠 Меню', callback_data='menu_back')],
            ])
        )
        print(f"⚠️ RETURN на строке 2619", flush=True)
        return

    # === ДАЛЬШЕ — СТАРАЯ ЛОГИКА (новые задачи, расходы и т.д.) ===

    # === ПРИВЕТСТВИЯ ===
    greetings = ['привет', 'здравствуй', 'здравствуйте', 'хай', 'hi', 'hello', 'ку', 'добрый день', 'доброе утро', 'добрый вечер']
    text_low = text.lower().strip()
    if text_low in greetings or any(text_low.startswith(g) for g in greetings):
        user_name = update.effective_user.first_name or ''
        await update.message.reply_text(
            f"👋 Привет{', ' + user_name if user_name else ''}!\n\n"
            f"Я *Бо 7.7* — помощник по стройке.\n\n"
            f"Что умею:\n"
            f"• «потратил 5000 на материалы Переделкино-2»\n"
            f"• «добавь в Арбат положить паркет»\n"
            f"• «500» — спрошу личный/объект\n"
            f"• /objects, /tasks, /finance — списки\n"
            f"• /help — все команды",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                [InlineKeyboardButton("⚙️ Помощь", callback_data="menu_help")],
            ])
        )
        print(f"⚠️ RETURN на строке 2643", flush=True)
        return

    # Обработка создания новой задачи
    if context.user_data.get('waiting_for') == 'new_task_text':
        obj = context.user_data.get('pending_task_object')
        if obj:
            tid = create_task(obj['id'], text)
            context.user_data['waiting_for'] = None
            context.user_data['pending_task_object'] = None
            await update.message.reply_text(
                f"✅ Задача «{text}» добавлена в «{obj['name']}»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 К задаче", callback_data=f"task_{tid}")],
                    [InlineKeyboardButton("📋 К задачам", callback_data="menu_tasks")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
            print(f"⚠️ RETURN на строке 2660", flush=True)
            return

    # Обработка создания нового расхода
    if context.user_data.get('waiting_for') == 'new_expense_text':
        obj = context.user_data.get('pending_expense_object')
        if not obj:
            context.user_data['waiting_for'] = None
            await update.message.reply_text(
                "❌ Объект потерялся. Начни заново: «➕ Добавить» → «💰 Расход»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить", callback_data="menu_add")],
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
            print(f"⚠️ RETURN на строке 2674", flush=True)
            return
        if obj:
            amount = parse_amount(text)
            if amount:
                category = None
                _tl = text.lower()
                for _c in ["материалы", "еда", "транспорт", "инструмент"]:
                    if _c in _tl:
                        category = _c
                        break
                if category:
                    add_expense(obj['id'], amount, category)
                    context.user_data['waiting_for'] = None
                    context.user_data['pending_expense_object'] = None
                    await update.message.reply_text(
                        f"\u2705 Расход {amount} \u20bd ({category}) добавлен в \u00ab{obj['name']}\u00bb",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("\U0001F4B0 К финансам", callback_data="menu_finance")],
                            [InlineKeyboardButton("\U0001F3E0 Меню", callback_data="menu_back")],
                        ])
                    )
                    print(f"⚠️ RETURN на строке 2695", flush=True)
                    return
                else:
                    context.user_data['pending_expense'] = {
                        'object_id': obj['id'],
                        'object_name': obj['name'],
                        'amount': amount
                    }
                    context.user_data['waiting_for'] = 'new_expense_category'
                    await update.message.reply_text(
                        f"\U0001F4B0 {amount} \u20bd в \u00ab{obj['name']}\u00bb. За что?",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("\U0001F9F1 Материалы", callback_data="cat_материалы")],
                            [InlineKeyboardButton("\U0001F354 Еда", callback_data="cat_еда")],
                            [InlineKeyboardButton("\U0001F697 Транспорт", callback_data="cat_транспорт")],
                            [InlineKeyboardButton("\U0001F527 Инструмент", callback_data="cat_инструмент")],
                            [InlineKeyboardButton("\U0001F4E6 Прочее", callback_data="cat_прочее")],
                        ])
                    )
                    print(f"⚠️ RETURN на строке 2713", flush=True)
                    return
            else:
                await update.message.reply_text(
                    "\u274c Не понял сумму. Попробуй: \u00ab500\u00bb"
                )
                print(f"⚠️ RETURN на строке 2718", flush=True)
                return

    # Обработка личного расхода
    if context.user_data.get('waiting_for') == 'personal_expense_text':
        # Разбираем: "300 еда" или "1500 инструмент"
        parts = text.strip().split(maxsplit=1)
        amount_str = parts[0] if parts else ''
        category = parts[1].strip() if len(parts) > 1 else 'прочее'
        # Убираем лишние символы
        amount_str = amount_str.replace('₽', '').replace('р', '').replace('руб', '').strip()
        try:
            amount = int(amount_str)
        except ValueError:
            amount = parse_amount(text)
            if not amount:
                await update.message.reply_text(
                    "❌ Не понял сумму. Попробуй: «300 еда»"
                )
                print(f"⚠️ RETURN на строке 2736", flush=True)
                return
        add_personal_expense(amount, category)
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"✅ Личный расход {amount} ₽ ({category}) записан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 К личным", callback_data="menu_personal")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        print(f"⚠️ RETURN на строке 2746", flush=True)
        return

    # Обработка создания нового объекта
    if context.user_data.get('waiting_for') == 'new_object':
        object_id = create_object(text, user_id=update.effective_user.id)
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            f"✅ Объект «{text}» создан",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ К объекту", callback_data=f"obj_{object_id}")],
                [InlineKeyboardButton("🏗️ К объектам", callback_data="menu_objects")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        print(f"⚠️ RETURN на строке 2760", flush=True)
        return

    # Обработка ввода даты для задачи
    setdate_task = context.user_data.get('setdate_task')
    if setdate_task:
        d = parse_date(text)
        if d:
            # Сохраняем во временное хранилище, ждём подтверждения
            context.user_data['confirm_date'] = {
                'task_id': setdate_task,
                'date': d.strftime('%Y-%m-%d'),
                'date_str': d.strftime('%d.%m.%Y')
            }
            context.user_data['setdate_task'] = None
            # Получаем задачу
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT t.title, o.name as obj FROM tasks t LEFT JOIN objects o ON t.object_id = o.id WHERE t.id = ?", (setdate_task,))
            row = c.fetchone()
            conn.close()
            title = row['title'] if row else '?'
            obj = row['obj'] if row and row['obj'] else 'Без объекта'
            await update.message.reply_text(
                f"📋 {title}\n{obj}\n\n📅 Дата: {d.strftime('%d.%m.%Y')}\n\nПодтверди:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да", callback_data=f"confirmdate_yes_{setdate_task}_{d.strftime('%Y-%m-%d')}")],
                    [InlineKeyboardButton("❌ Нет", callback_data=f"confirmdate_no_{setdate_task}")],
                ])
            )
            # Автоподтверждение через 30 секунд
            context.job_queue.run_once(
                auto_confirm_date,
                30,
                data={
                    'chat_id': update.effective_chat.id,
                    'task_id': setdate_task,
                    'date': d.strftime('%Y-%m-%d'),
                    'date_str': d.strftime('%d.%m.%Y')
                },
                name=f"confirm_{setdate_task}"
            )
            print(f"⚠️ RETURN на строке 2801", flush=True)
            return
        else:
            await update.message.reply_text(
                "❌ Не понял дату. Попробуй: «завтра», «20.09», «пн», «+3»"
            )
            print(f"⚠️ RETURN на строке 2806", flush=True)
            return

    # Обработка переименования задачи
    rename_task = context.user_data.get('rename_task')
    if rename_task:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE tasks SET title = ? WHERE id = ?", (text, rename_task))
        conn.commit()
        conn.close()
        context.user_data['rename_task'] = None
        await update.message.reply_text(f"✅ Задача переименована: «{text}»")
        print(f"⚠️ RETURN на строке 2818", flush=True)
        return

    result = parse_message(text)
    action = result.get('action')

    if action == 'ask_expense_type':
        amount = result['amount']
        context.user_data['ask_expense_amount'] = amount
        await update.message.reply_text(
            f"💰 {amount} ₽ — куда записать?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Личный расход", callback_data=f"exp_type_personal_{amount}")],
                [InlineKeyboardButton("🏗️ Расход по объекту", callback_data=f"exp_type_object_{amount}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="menu_back")],
            ])
        )
        print(f"⚠️ RETURN на строке 2834", flush=True)
        return

    if action == 'income':
        obj = result['object']
        amount = result['amount']
        category = result.get('category', 'доход')
        add_income(obj['id'], amount, category)
        await update.message.reply_text(
            f"💰 Доход {amount} ₽ ({category}) добавлен в «{obj['name']}»"
        )
        print(f"⚠️ RETURN на строке 2845", flush=True)
        return

    if action == 'expense':
        obj = result['object']
        amount = result['amount']
        category = result['category']
        # Известные категории
        known_categories = ['материалы', 'еда', 'транспорт', 'инструмент', 'сантехника', 'электрика', 'покраска']
        # Если категория явно из списка — записываем сразу
        if category and category in known_categories:
            add_expense(obj['id'], amount, category)
            await update.message.reply_text(
                f"✅ Расход {amount} ₽ ({category}) добавлен в «{obj['name']}»"
            )
            print(f"⚠️ RETURN на строке 2859", flush=True)
            return
        # Иначе — спрашиваем категорию
        context.user_data['pending_expense'] = {
            'object_id': obj['id'],
            'object_name': obj['name'],
            'amount': amount
        }
        await update.message.reply_text(
            f"💰 Расход {amount} ₽ в «{obj['name']}»\n\nЗа что?",
            reply_markup=expense_category_keyboard()
        )
        print(f"⚠️ RETURN на строке 2870", flush=True)
        return

    if action == 'add_task':
        obj = result['object']
        title = result['title']
        tid = create_task(obj['id'], title)
        await update.message.reply_text(
            f"✅ Задача «{title}» добавлена в «{obj['name']}». ID: {tid}"
        )
        print(f"⚠️ RETURN на строке 2879", flush=True)
        return

    if action == 'done_task':
        obj = result['object']
        task = result['task']
        close_task(task['id'], user_id=update.effective_user.id)
        await update.message.reply_text(
            f"✅ Задача «{task['title']}» в «{obj['name']}» выполнена!"
        )
        print(f"⚠️ RETURN на строке 2888", flush=True)
        return

    if action == 'done_task_not_found':
        obj = result['object']
        await update.message.reply_text(
            f"❌ В «{obj['name']}» не нашёл задачу с «{result['query']}». Посмотри /tasks"
        )
        print(f"⚠️ RETURN на строке 2895", flush=True)
        return

    if action == 'finance':
        obj = result['object']
        f = get_finance_summary(obj['id'])
        await update.message.reply_text(
            f"💰 {obj['name']}\n\nДоход: {f['income']} ₽\nРасход: {f['expense']} ₽\nБаланс: {f['balance']} ₽"
        )
        print(f"⚠️ RETURN на строке 2903", flush=True)
        return

    if action == 'list_tasks':
        tasks = get_active_tasks()
        if not tasks:
            await update.message.reply_text("✅ Нет активных задач")
            print(f"⚠️ RETURN на строке 2909", flush=True)
            return
        text_out = f"📋 Активные задачи ({len(tasks)}):\n\n"
        for t in tasks[:15]:
            text_out += f"• #{t['id']} {t['title']}\n"
        await update.message.reply_text(text_out)
        print(f"⚠️ RETURN на строке 2914", flush=True)
        return

    if action == 'list_objects':
        objs = get_all_objects()
        text_out = f"🏗️ Объекты ({len(objs)}):\n\n"
        for o in objs:
            text_out += f"• {o['name']}\n"
        await update.message.reply_text(text_out)
        print(f"⚠️ RETURN на строке 2922", flush=True)
        return

    if action == 'choose_object':
        objects = result['objects']
        intent = result.get('intent', 'expense')
        amount = result.get('amount')
        category = result.get('category', 'прочее')
        if intent == 'add_task':
            context.user_data['pending_task_title'] = result.get('title') or result.get('original_text', '')
        await update.message.reply_text(
            f"🤔 Нашёл несколько объектов. Какой именно?",
            reply_markup=make_choose_keyboard(objects, intent, amount, category)
        )
        print(f"⚠️ RETURN на строке 2935", flush=True)
        return

    # === CRM: ожидаем бюджет сделки ===

    # === УМНЫЙ FALLBACK: сразу ищем похожие объекты ===
    context.user_data['unknown_text'] = text

    # Ищем похожие объекты через rapidfuzz
    print(f"🔍 UNKNOWN: text={text!r}", flush=True)
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
    all_objs = get_all_objects()
    print(f"🔍 UNKNOWN: all_objs={len(all_objs)}", flush=True)
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
            f"🏗️ {exact_match['name']}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏗️ Открыть объект", callback_data=f"obj_{exact_match['id']}")],
                [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
            ])
        )
        return

    buttons = []
    if similar:
        for o, score in similar:
            buttons.append([InlineKeyboardButton(
                f"🏗️ {o['name']} ({int(score)}%)",
                callback_data=f"obj_{o['id']}"
            )])
    buttons.append([InlineKeyboardButton(f"➕ Создать новый объект «{text[:40]}»", callback_data="unknown_as_object")])
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


# === УТОЧНЕНИЕ ОБЪЕКТА ===
