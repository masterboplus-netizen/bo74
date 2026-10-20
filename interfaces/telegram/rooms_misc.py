"""interfaces/telegram/rooms_misc.py — объекты, планы, экспорт, ЭОМ объекта."""
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from core.export.csv_export import save_csv, export_csv
from core.export.json_export import save_json, export_json
from core.export.dxf import save_dxf, export_dxf

from core.rooms import get_rooms, get_room
from core.db import fetchone, fetchall, commit as db_commit
from core import spec as core_spec
from modules.objects import get_object
try:
    from core import elec as core_elec
except Exception:
    core_elec = None
try:
    from core import elec_panels as core_elec_panels
except Exception:
    core_elec_panels = None
try:
    from core.visualize import render_room_plan
except Exception:
    render_room_plan = None
async def handle_obj_elec_callback(query, context, data):
    """ЭОМ объекта — основной экран."""
    print(f"🟠 handle_obj_elec_callback: data={data!r}, core_elec={core_elec is not None}", flush=True)
    if not core_elec:
        try:
            await query.edit_message_text("❌ Модуль ЭОМ не загружен")
        except Exception:
            pass
        return True

    # --- ОСНОВНОЙ ЭКРАН ЭОМ ---
    if data.startswith("obj_elec_setup_"):
        object_id = int(data.replace("obj_elec_setup_", ""))
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1-фазное (220В)", callback_data=f"obj_elec_set_{object_id}_1")],
            [InlineKeyboardButton("3-фазное (380В)", callback_data=f"obj_elec_set_{object_id}_3")],
            [InlineKeyboardButton("⬅️ К ЭОМ", callback_data=f"obj_elec_{object_id}")],
        ])
        try:
            await query.edit_message_text(
                "⚡ *Тип электроснабжения объекта*\n\nВыбери:",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            pass
        return True

    if data.startswith("obj_elec_set_"):
        parts = data.replace("obj_elec_set_", "").rsplit("_", 1)
        object_id = int(parts[0])
        phase = int(parts[1])
        voltage = 380 if phase == 3 else 220
        try:
            core_elec.set_supply(object_id, phase_count=phase, voltage=voltage,
                                 meter_type='трёхфазный' if phase == 3 else 'однофазный')
        except Exception as e:
            print(f"⚠️ set_supply: {e}", flush=True)
        await _show_obj_elec(query, object_id)
        return True

    if data.startswith("obj_elec_labor_"):
        object_id = int(data.replace("obj_elec_labor_", ""))
        try:
            from core import object_works as core_works
            text = core_works.format_object_labor(object_id, prefix="elec_")
        except Exception as e:
            print("elec labor: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К электрике", callback_data="obj_elec_" + str(object_id))],
            ]))
        return True

    if data.startswith("obj_elec_") and not data.startswith(("obj_elec_cost_", "obj_elec_pdf_", "obj_elec_labor_")):
        object_id = int(data.replace("obj_elec_", ""))
        await _show_obj_elec(query, object_id)
        return True

    return False



async def handle_plan_callback(query, context, data):
    """Обработчик плана комнаты."""
    if data.startswith("room_plan_"):
        room_id = int(data.replace("room_plan_", ""))
        await _do_render_plan(query, context, room_id)
        return True
    return False



async def _do_render_plan(query, context, room_id):
    """Рендерит план комнаты и отправляет PNG."""
    if render_room_plan is None:
        try:
            await query.edit_message_text(
                "❌ Модуль визуализации не загружен",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    # Проверка: есть ли замеры
    from core.measures import get_walls_ordered
    try:
        walls = get_walls_ordered(room_id)
    except Exception:
        walls = []
    if not walls:
        try:
            await query.edit_message_text(
                "⚠️ *В комнате нет замеров*\n\n"
                "Сначала пройди мастер замеров.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать замер", callback_data=f"room_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    try:
        path = render_room_plan(room_id)
        if not path or not os.path.exists(path):
            raise Exception("PNG не создан")

        room = get_room(room_id)
        name = room.get('name', f'Комната {room_id}') if room else f'Комната {room_id}'
        with open(path, "rb") as f:
            await query.message.chat.send_photo(
                photo=f,
                caption=f"🧊 *План комнаты* «{name}»",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Обновить", callback_data=f"room_plan_{room_id}")],
                    [InlineKeyboardButton("📤 Экспорт", callback_data=f"room_export_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
    except Exception as e:
        print(f"⚠️ _do_render_plan: {e}", flush=True)
        try:
            await query.edit_message_text(
                f"❌ Ошибка рендера: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 Попробовать", callback_data=f"room_plan_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass


# ============================================================
# ЭКСПОРТ КОМНАТЫ
# ============================================================


async def handle_export_callback(query, context, data):
    from core.export.csv_export import save_csv
    from core.export.dxf import save_dxf
    from core.export.json_export import save_json
    """Обработчик экспорта."""
    # --- Специфичные форматы (СНАЧАЛА!) ---
    if data.startswith("room_export_dxf_"):
        room_id = int(data.replace("room_export_dxf_", ""))
        await _do_export_dxf(query, context, room_id)
        return True

    if data.startswith("room_export_json_"):
        room_id = int(data.replace("room_export_json_", ""))
        await _do_export_json(query, context, room_id)
        return True

    if data.startswith("room_export_csv_"):
        room_id = int(data.replace("room_export_csv_", ""))
        await _do_export_csv(query, context, room_id)
        return True

    if data.startswith("room_export_pdf_"):
        suffix = data.split("_")[-1]
        try:
            rid = int(suffix)
        except ValueError:
            rid = 0
        try:
            await query.edit_message_text(
                "🚧 PDF в разработке. Пока доступны DXF, JSON, CSV.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_export_{rid}")],
                ])
            )
        except Exception:
            pass
        return True

    # --- Общий вызов меню: room_export_<id> (только если id — цифры) ---
    if data.startswith("room_export_"):
        suffix = data.replace("room_export_", "")
        if suffix.isdigit():
            room_id = int(suffix)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 DXF (CAD)", callback_data=f"room_export_dxf_{room_id}")],
                [InlineKeyboardButton("📦 JSON (данные)", callback_data=f"room_export_json_{room_id}")],
                [InlineKeyboardButton("📄 PDF (отчёт)", callback_data=f"room_export_pdf_{room_id}")],
                [InlineKeyboardButton("📊 CSV (смета)", callback_data=f"room_export_csv_{room_id}")],
                [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
            ])
            try:
                await query.edit_message_text(
                    "📤 *Экспорт комнаты*\n\nВыбери формат:",
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            except Exception:
                pass
            return True

    return False




async def handle_object_callback(update, context, data):
    """Обработчик obj_* — вызывается из handle_rooms_callback."""
    from modules.objects import get_object, delete_object

    if data.startswith("obj_del_"):
        object_id = int(data.replace("obj_del_", ""))
        obj = get_object(object_id)
        name = obj['name'] if obj else '?'
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"obj_delok_{object_id}")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"obj_{object_id}")],
        ])
        try:
            await update.callback_query.edit_message_text(
                f"🗑 *Удалить объект «{name}»?*\n\n"
                f"Будут удалены: комнаты, замеры, проёмы, коммуникации.\n"
                f"Задачи и финансы — отвязаны (не удалены).",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            pass
        return True

    if data.startswith("obj_delok_"):
        object_id = int(data.replace("obj_delok_", ""))
        delete_object(object_id)
        try:
            await update.callback_query.edit_message_text(
                "✅ Объект удалён",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Меню", callback_data="menu_back")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("obj_rename_"):
        object_id = int(data.replace("obj_rename_", ""))
        context.user_data['waiting_for'] = 'obj_rename'
        context.user_data['obj_rename_id'] = object_id
        try:
            await update.callback_query.edit_message_text(
                "✏️ *Новое имя объекта:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"obj_{object_id}")],
                ])
            )
        except Exception:
            pass
        return True

    return False

# ============================================================
# КУХОННЫЕ ШАБЛОНЫ (кафе/рестораны) — UI
# ============================================================


from .rooms_reports import _do_export_csv, _do_export_dxf, _do_export_json

