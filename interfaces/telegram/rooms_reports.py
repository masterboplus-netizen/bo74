"""interfaces/telegram/rooms_reports.py — отчёты и экспорт."""
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.rooms import get_rooms, get_room
from core.db import fetchone, fetchall, commit as db_commit
from core import spec as core_spec
from core.export.csv_export import save_csv, export_csv
from core.export.dxf import save_dxf, export_dxf
from core.export.json_export import save_json, export_json
async def handle_reports_callback(query, context, data):
    """Меню планов и отчётов."""
    if data.startswith("room_estimate_"):
        room_id = int(data.replace("room_estimate_", ""))
        from core.room_estimate import format_room_estimate
        text = format_room_estimate(room_id)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + chr(10) + "..."
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    if data.startswith("room_reports_"):
        room_id = int(data.replace("room_reports_", ""))
        room = get_room(room_id)
        name = room.get('name', '?') if room else '?'

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📐 Обмерный план", callback_data=f"room_plan_{room_id}")],
            [InlineKeyboardButton("⚡ Электрика", callback_data=f"room_report_electric_{room_id}")],
            [InlineKeyboardButton("🚿 Сантехника", callback_data=f"room_report_plumbing_{room_id}")],
            [InlineKeyboardButton("🧱 Плитка", callback_data=f"room_report_tiler_{room_id}")],
            [InlineKeyboardButton("🎨 Покраска", callback_data=f"room_report_painter_{room_id}")],
            [InlineKeyboardButton("📋 Ведомость", callback_data=f"room_report_spec_{room_id}")],
            [InlineKeyboardButton("📄 PDF-проект", callback_data=f"room_report_pdf_{room_id}")],
            [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
        ])

        try:
            await query.edit_message_text(
                f"📊 *Планы и отчёты* — «{name}»\n\nВыбери:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
        except Exception:
            pass
        return True

    if data.startswith("room_report_electric_"):
        room_id = int(data.replace("room_report_electric_", ""))
        await _do_report_electric(query, context, room_id)
        return True

    if data.startswith("room_report_plumbing_") or data.startswith("room_report_tiler_") or data.startswith("room_report_painter_") or data.startswith("room_report_spec_") or data.startswith("room_report_pdf_"):
        try:
            room_id = int(data.split("_")[-1])
        except ValueError:
            room_id = 0
        try:
            await query.edit_message_text(
                f"🚧 В разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К отчётам", callback_data=f"room_reports_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    return False



async def _do_report_electric(query, context, room_id):
    """ЭОМ — часть 1: план + таблица точек."""
    from core.comms import get_comms
    from core.rooms import get_room

    room = get_room(room_id)
    name = room.get('name', '?') if room else '?'

    elec_types = {
        'elec_socket': ('🔌', 'Розетки'),
        'elec_switch': ('💡', 'Выключатели'),
        'elec_panel': ('⚡', 'Щит'),
        'elec_cable': ('🔌', 'Выводы света'),
    }

    try:
        comms = get_comms(room_id)
    except Exception:
        comms = []

    groups = {t: [] for t in elec_types}
    for c in comms:
        t = c.get('comm_type')
        if t in elec_types:
            groups[t].append(c)

    lines = [f"⚡ *ЭОМ — Электрика «{name}»*\n"]

    total = 0
    for t, (icon, label) in elec_types.items():
        items = groups[t]
        if not items:
            lines.append(f"{icon} *{label}*: нет")
            continue
        lines.append(f"{icon} *{label}* ({len(items)}):")
        for c in items:
            wall = c.get('wall') or '?'
            ox = c.get('offset_x')
            oy = c.get('offset_y')
            parts = [f"стена «{wall}»"]
            if ox is not None:
                parts.append(f"{int(ox)} см от угла")
            if oy is not None:
                parts.append(f"{int(oy)} см от пола")
            lines.append("  • " + ", ".join(parts))
            total += 1

    lines.append(f"\n📊 *Всего точек: {total}*")
    text = "\n".join(lines)

    if render_room_plan is not None:
        try:
            path = render_room_plan(room_id)
            if path and os.path.exists(path):
                with open(path, "rb") as f:
                    await query.message.chat.send_photo(
                        photo=f,
                        caption=text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("⬅️ К отчётам", callback_data=f"room_reports_{room_id}")],
                        ])
                    )
                return
        except Exception as e:
            print(f"⚠️ _do_report_electric render: {e}", flush=True)

    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К отчётам", callback_data=f"room_reports_{room_id}")],
            ])
        )
    except Exception:
        pass



async def _do_export_dxf(query, context, room_id):
    """Генерирует DXF и отправляет."""
    kb_err = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Попробовать снова", callback_data=f"room_export_dxf_{room_id}")],
        [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
    ])

    if save_dxf is None:
        try:
            await query.edit_message_text(
                "❌ Модуль DXF не загружен",
                reply_markup=kb_err
            )
        except Exception:
            pass
        return

    # --- Проверка: есть ли замеры? ---
    from core.measures import get_walls_ordered
    try:
        walls = get_walls_ordered(room_id)
    except Exception:
        walls = []
    if not walls:
        try:
            await query.edit_message_text(
                "⚠️ *В комнате нет замеров*\n\n"
                "Сначала пройди мастер замеров: высота + обход стен.\n"
                "После этого DXF будет содержать контур комнаты.",
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
        # Правильный путь — используем os.path
        import tempfile
        tmp_dir = tempfile.gettempdir()
        target_path = os.path.join(tmp_dir, f"export_room_{room_id}.dxf")
        path = save_dxf(room_id, path=target_path)
        if not path or not os.path.exists(path):
            # Fallback — дефолтный путь от save_dxf
            path = save_dxf(room_id)
        if not path or not os.path.exists(path):
            raise Exception(f"Файл не создан (save_dxf вернул {path})")

        room = get_room(room_id)
        name = room.get('name', f'room_{room_id}') if room else f'room_{room_id}'
        with open(path, "rb") as f:
            await query.message.chat.send_document(
                document=f,
                filename=f"{name}.dxf",
                caption=f"📐 DXF-экспорт комнаты «{name}»\n\nОткрой в: SketchUp, ArchiCAD, AutoCAD",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
    except Exception as e:
        print(f"⚠️ _do_export_dxf: {e}", flush=True)
        try:
            await query.edit_message_text(
                f"❌ Ошибка DXF: {e}",
                reply_markup=kb_err
            )
        except Exception:
            pass



async def _do_export_csv(query, context, room_id):
    """Генерирует CSV и отправляет."""
    if save_csv is None:
        try:
            await query.edit_message_text("❌ Модуль CSV не загружен")
        except Exception:
            pass
        return
    try:
        import tempfile
        tmp_dir = tempfile.gettempdir()
        target_path = os.path.join(tmp_dir, f"export_room_{room_id}.csv")
        path = save_csv(room_id, path=target_path)
        if not path or not os.path.exists(path):
            path = save_csv(room_id)
        if not path or not os.path.exists(path):
            raise Exception("Файл не создан")
        room = get_room(room_id)
        name = room.get('name', f'room_{room_id}') if room else f'room_{room_id}'
        with open(path, "rb") as f:
            await query.message.chat.send_document(
                document=f,
                filename=f"{name}.csv",
                caption=f"📊 CSV-экспорт комнаты «{name}»\n\nОткрой в Excel или Google Sheets",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
    except Exception as e:
        print(f"⚠️ _do_export_csv: {e}", flush=True)
        try:
            await query.edit_message_text(
                f"❌ Ошибка CSV: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 Попробовать снова", callback_data=f"room_export_csv_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass



async def _do_export_json(query, context, room_id):
    """Генерирует JSON и отправляет."""
    # --- Проверка: есть ли замеры? ---
    from core.measures import get_walls_ordered
    try:
        walls = get_walls_ordered(room_id)
    except Exception:
        walls = []
    if not walls:
        try:
            await query.edit_message_text(
                "⚠️ *В комнате нет замеров*\n\n"
                "Сначала пройди мастер замеров.\nJSON будет содержать пустую модель.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать замер", callback_data=f"room_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    if save_json is None:
        try:
            await query.edit_message_text("❌ Модуль JSON не загружен")
        except Exception:
            pass
        return

    try:
        import tempfile
        tmp_dir = tempfile.gettempdir()
        target_path = os.path.join(tmp_dir, f"export_room_{room_id}.json")
        path = save_json(room_id, path=target_path)
        if not path or not os.path.exists(path):
            path = save_json(room_id)
        if not path or not os.path.exists(path):
            raise Exception("Файл не создан")
        room = get_room(room_id)
        name = room.get('name', f'room_{room_id}') if room else f'room_{room_id}'
        with open(path, "rb") as f:
            await query.message.chat.send_document(
                document=f,
                filename=f"{name}.json",
                caption=f"📦 JSON-экспорт комнаты «{name}»\n\nЦифровой двойник: геометрия + замеры + проёмы + ниши",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
    except Exception as e:
        print(f"⚠️ _do_export_json: {e}", flush=True)
        try:
            await query.edit_message_text(
                f"❌ Ошибка JSON: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 Попробовать снова", callback_data=f"room_export_json_{room_id}")],
                    [InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass


# ============================================================
# ГЛАВНЫЙ РОУТЕР CALLBACK'ОВ
# ============================================================

