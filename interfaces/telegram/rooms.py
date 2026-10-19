"""interfaces.telegram.rooms — UI комнат в Telegram (v3, переписан с нуля).

Версия: 3.0
Дата: 2026-10-03
Ключевое отличие от v2:
  - Единый state wall_state вместо россыпи ключей в user_data
  - _save_wall_draft / _load_wall_draft работают со всем state целиком
  - wall_round_start_ обрабатывает ВСЕ step_name, включая niche_width
  - session_id используется везде (ensure_session)
  - Тексты из core.spec, картинки из docs/images
"""
import os
import json
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from .rooms_walls import (
    _wall_round_start, _get_wall_state, _reset_wall_state, _save_wall_draft,
    _load_wall_draft, _clear_wall_draft, _current_wall_pos, _wall_flags_list,
    _show_wall_step, _show_wall_plane, _show_wall_length, _show_wall_openings,
    _show_wall_angle, _show_niche_count, _show_niche_width, _show_niche_depth,
    _show_niche_height, _show_niche_plane, _show_niche_top_width, _show_niche_top_depth,
    _wall_save_and_next, _wall_finish, handle_wall_round_callback,
    _after_angle, _wall_round_open_start, _handle_wall_round_input,
    _after_angle_from_update, _wall_save_and_next_from_update,
    _show_wall_openings_from_update, _show_niche_depth_from_update,
    _show_niche_height_from_update, _show_niche_plane_from_update,
    _show_niche_top_depth_from_update, _show_wall_length_from_update,
    _handle_wall_round_opening_input,
)

# --- Ядро: комнаты ---
from core.rooms import get_rooms, get_room, create_room, delete_room, update_room
from core.rooms_ui import format_room_card, format_rooms_list

# --- Ядро: замеры ---
from core.measures import (
    get_measures, calculate_room_areas, format_measure, get_walls_ordered,
    add_measure, delete_measure,
    start_walls_round, complete_walls_round, get_walls_progress,
)

# --- Ядро: проёмы ---
from core.openings import (
    add_opening, get_opening, get_openings, get_openings_by_wall,
    update_opening, delete_opening, format_opening, OPENING_TYPES,
)

# --- Ядро: ниши ---
from core.niches import (
    add_niche, get_niches, get_niches_by_room,
    update_niche, delete_niche, format_niche,
)

# --- Ядро: коммуникации ---
from core.comms import (
    get_comms, format_comm, get_comm_type_label, get_comm,
    add_comm, update_comm, delete_comm, COMM_TYPES,
)

# --- Ядро: сессии, геометрия, БД, spec ---
from core.sessions import ensure_session, get_active_session
from core.geometry import calc_wall_coords, check_closure
from core.db import fetchone, fetchall, commit as db_commit
from core import spec
try:
    from core import spec as core_spec
except Exception:
    core_spec = spec

# --- Объекты комнат ---
from core.room_objects import get_room_objects, format_room_object

# --- Экспорт ---
try:
    from core.export.dxf import save_dxf, export_dxf
except Exception:
    save_dxf = export_dxf = None

# --- Визуализация ---
try:
    from core.visualize import render_room_plan
except Exception:
    render_room_plan = None

# --- ЭОМ ---
try:
    from core import elec as core_elec
except Exception:
    core_elec = None

try:
    from core import elec_panels as core_elec_panels
except Exception:
    core_elec_panels = None

try:
    from core import elec_routes as core_elec_routes
except Exception:
    core_elec_routes = None

try:
    from core import elec_prices as core_elec_prices
except Exception:
    core_elec_prices = None

try:
    from core.export.spec_export import (
        save_panel_spec, export_panel_spec, export_object_spec
    )
except Exception:
    save_panel_spec = export_panel_spec = None
    export_object_spec = None

try:
    from core.export.estimate_export import (
        export_panel_estimate_csv, export_object_estimate_csv, save_estimate_csv,
        export_plumbing_object_csv
    )
except Exception:
    export_panel_estimate_csv = export_object_estimate_csv = save_estimate_csv = None
    export_plumbing_object_csv = None

try:
    from core.export.spec_export import export_plumbing_panel_spec
except Exception:
    export_plumbing_panel_spec = None

try:
    from core import marketplaces as core_marketplaces
except Exception:
    core_marketplaces = None

try:
    from core import plumbing_panels as core_plumbing
except Exception:
    core_plumbing = None

try:
    from core import object_works as core_works
except Exception:
    core_works = None

# --- Помещения (этажи / зоны) ---
try:
    from core import floors as core_floors
except Exception:
    core_floors = None
try:
    from core.export.json_export import save_json, export_json
except Exception:
    save_json = export_json = None
try:
    from core.export.csv_export import save_csv, export_csv
except Exception:
    save_csv = export_csv = None


# ============================================================
# БЕЗОПАСНЫЙ EDIT
# ============================================================

async def _safe_edit(query, text, kb=None):
    """Универсальный edit: text -> caption -> delete+send.

    Используется для надёжного обновления сообщения независимо от того,
    текст это или фото."""
    is_photo = bool(getattr(query.message, "photo", None))
    try:
        if is_photo:
            await query.edit_message_caption(caption=text, parse_mode=None, reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode=None, reply_markup=kb)
        return True
    except Exception as e1:
        err = str(e1).lower()
        if "message is not modified" in err:
            return True
        print("_safe_edit edit failed: " + str(e1), flush=True)
    try:
        await query.message.delete()
    except Exception:
        pass
    try:
        await query.get_bot().send_message(
            chat_id=query.message.chat_id, text=text, reply_markup=kb
        )
        print("_safe_edit send_message OK", flush=True)
        return True
    except Exception as e2:
        print("_safe_edit send failed: " + str(e2), flush=True)
        return False



# ============================================================
# КОНСТАНТЫ
# ============================================================

WALL_NAMES = core_spec.WALL_NAMES
WALL_NAMES_REVERSE = {v: k for k, v in WALL_NAMES.items()}

DEFAULT_FLAGS = {"niche": False, "rounded": False, "wavy": False, "hidden": False}


# ============================================================
# ЕДИНЫЙ STATE СТЕНЫ
# ============================================================

def rooms_list_keyboard(object_id):
    """Клавиатура списка комнат объекта."""
    rooms = get_rooms(object_id)
    buttons = []
    for r in rooms:
        mark = "🏠" if r.get('is_default') else "📦"
        buttons.append([InlineKeyboardButton(f"{mark} {r['name']}", callback_data=f"room_{r['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить комнату", callback_data=f"room_add_{object_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")])
    return InlineKeyboardMarkup(buttons)


def room_card_keyboard(room_id):
    """Клавиатура карточки комнаты."""
    room = get_room(room_id)
    object_id = room['object_id'] if room else 0
    walls = get_walls_ordered(room_id)
    height_ok = bool(room.get('height_bottom') and room.get('height_middle') and room.get('height_top'))
    walls_ok = len(walls) >= core_spec.get_total_walls()

    if not height_ok and not walls:
        start_btn = InlineKeyboardButton("🚀 Начать замер", callback_data=f"room_start_{room_id}")
    elif height_ok and walls_ok:
        start_btn = InlineKeyboardButton("✅ Замер завершён", callback_data=f"room_start_{room_id}")
    else:
        start_btn = InlineKeyboardButton("▶️ Продолжить замер", callback_data=f"room_start_{room_id}")

    return InlineKeyboardMarkup([
        [start_btn],
        [InlineKeyboardButton("📐 Размеры", callback_data=f"room_measures_{room_id}"),
         InlineKeyboardButton("👁 Что замерено", callback_data=f"room_progress_{room_id}")],
        [InlineKeyboardButton("🚪 Проёмы", callback_data=f"openings_list_{room_id}"),
         InlineKeyboardButton("🔧 Коммуникации", callback_data=f"room_comms_{room_id}")],
        [InlineKeyboardButton("🪑 Мебель", callback_data=f"room_objects_{room_id}")],
        [InlineKeyboardButton("📋 Задачи", callback_data=f"room_tasks_{room_id}"),
         InlineKeyboardButton("📸 Фото", callback_data=f"room_photos_{room_id}")],
        [InlineKeyboardButton("💰 Смета комнаты", callback_data=f"room_estimate_{room_id}")],
        [InlineKeyboardButton("📊 Отчёты", callback_data=f"room_reports_{room_id}"),
         InlineKeyboardButton("📤 Экспорт", callback_data=f"room_export_{room_id}")],
        [InlineKeyboardButton("⚡ Группы ЭОМ", callback_data=f"room_groups_{room_id}")],
        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"room_rename_{room_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"room_del_{room_id}")],
        [InlineKeyboardButton("⬅️ К комнатам", callback_data=f"rooms_list_obj_{object_id}")],
    ])


# ============================================================
# ПОКАЗ КОМНАТ
# ============================================================

async def show_rooms_list(update, context, object_id):
    """Показ списка комнат объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else '—'
    text = f"📦 *Комнаты «{obj_name}»*\n\n{format_rooms_list(object_id)}"
    kb = rooms_list_keyboard(object_id)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
        except Exception:
            try:
                await update.callback_query.message.delete()
            except Exception:
                pass
            await update.callback_query.message.chat.send_message(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )


async def show_room_card(update, context, room_id):
    """Показ карточки комнаты."""
    room = get_room(room_id)
    if not room:
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Комната не найдена")
        else:
            await update.message.reply_text("❌ Комната не найдена")
        return
    text = format_room_card(room_id)
    kb = room_card_keyboard(room_id)

    if update.callback_query:
        query = update.callback_query
        has_photo = bool(getattr(query.message, "photo", None))
        if has_photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(
                text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
            )
        else:
            try:
                await query.edit_message_text(
                    text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                if "message is not modified" in str(e).lower():
                    return
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await query.message.chat.send_message(
                    text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
                )
    else:
        await update.message.reply_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )


# ============================================================
# МАСТЕР ВЫСОТЫ (3 точки)
# ============================================================

async def _send_height_scheme(message, context, room_id, step, caption, kb_extra=None):
    """Отправка PNG-схемы высоты."""
    kb_rows = list(kb_extra or [])
    kb_rows.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")])
    kb = InlineKeyboardMarkup(kb_rows)
    png = _image_path(f"height_scheme_step{step}.png")
    if png and os.path.exists(png):
        try:
            with open(png, "rb") as f:
                await message.reply_photo(
                    photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            return
        except Exception as e:
            print(f"⚠️ height scheme: {e}", flush=True)
    await message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_height_step(target, context, room_id, method=None, step=1):
    """Экран шага высоты.

    target — Update или CallbackQuery. Если CallbackQuery — сначала
    пытаемся edit, при неудаче — новое сообщение.
    """
    captions = {
        1: (
            "📏 *Высота — шаг 1*\n\n"
            "📍 *Точка 1 — ЦЕНТР комнаты*\n\n"
            "Встань в центре комнаты, приложи дальномер к полу, наведи на потолок.\n\n"
            "Введи результат в СМ:\n\n_Например: 305_"
        ),
        2: (
            "📏 *Высота — шаг 2*\n\n"
            "📍 *Точка 2 — у ЛЕВОГО угла*\n\n"
            "Введи результат в СМ:\n\n_Например: 304_"
        ),
        3: (
            "📏 *Высота — шаг 3*\n\n"
            "📍 *Точка 3 — у ПРАВОГО угла*\n\n"
            "Введи результат в СМ:\n\n_Например: 306_"
        ),
    }
    caption = captions.get(step, captions[1])
    kb_extra = [
        [InlineKeyboardButton("✅ Все три одинаковые", callback_data=f"room_height_same_{room_id}")],
    ]
    context.user_data['waiting_for'] = 'room_height_point'
    context.user_data['height_room_id'] = room_id
    context.user_data['height_step'] = step

    # target — callback (query) или Update
    if hasattr(target, 'message') and hasattr(target, 'edit_message_text'):
        # Это CallbackQuery
        try:
            await target.message.delete()
        except Exception:
            pass
        await _send_height_scheme(target.message, context, room_id, step, caption, kb_extra)
    elif hasattr(target, 'message'):
        # Это Update
        await _send_height_scheme(target.message, context, room_id, step, caption, kb_extra)


# ============================================================
# ОБХОД СТЕН: ПОКАЗ ЭКРАНОВ
# ============================================================

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


async def _show_obj_elec(query, object_id):
    """Показ основного экрана ЭОМ объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else f'Объект {object_id}'

    text = f"🏢 *{obj_name}*\n\n" + core_elec.format_elec_full(object_id)

    # Расчётный вводной автомат
    try:
        _sb = core_elec.calc_supply_breaker(object_id)
        if _sb and _sb.get('breaker_type'):
            text += (
                f"\n\n🔌 *Расчётный вводной автомат:*\n"
                f"   {_sb['breaker_type']} (ток: {_sb['current_a']} А)\n"
                f"   Σ мощность: {int(_sb['total_watt'])} Вт"
            )
    except Exception as e:
        print(f"⚠️ calc_supply_breaker: {e}", flush=True)

    # Распределение по фазам (если 3ф)
    try:
        _sup = core_elec.get_supply(object_id) or {}
        if _sup.get('phase_count') == 3:
            _phase_text = core_elec.format_phase_distribution(object_id)
            if _phase_text:
                text += "\n\n" + _phase_text
    except Exception as e:
        print(f"⚠️ obj phase distribution: {e}", flush=True)

    supply = core_elec.get_supply(object_id)
    supply_btn = "⚙️ Настроить питание" if not supply else "⚙️ Изменить питание"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(supply_btn, callback_data=f"obj_elec_setup_{object_id}")],
        [InlineKeyboardButton("📋 Кабельный журнал", callback_data=f"cables_list_{object_id}")],
        [InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")],
    ])

    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception as e:
        print(f"⚠️ _show_obj_elec: {e}", flush=True)
        try:
            await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            pass


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



async def handle_rooms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер всех callback'ов комнат."""
    query = update.callback_query
    print(f"🔴 HANDLE_ROOMS_CALLBACK ВЫЗВАН: {query.data!r}", flush=True)
    await query.answer()
    data = query.data
    print(f"🔍 ROOMS: data={data!r}", flush=True)
    if data.startswith("room_total_walls_"):
        parts = data.replace("room_total_walls_", "").split("_")
        try:
            room_id = int(parts[0])
            val = parts[1]
        except (ValueError, IndexError):
            return
        if val != "other":
            n = int(val)
            core_spec.set_total_walls(n)
            context.user_data["waiting_for"] = None
            # Запускаем обход
            try:
                await query.message.chat.send_message(f"✅ Стён: {n}. Начинаем обход.")
            except Exception:
                pass
            print(f"🚀 ВЫЗОВ _wall_round_start: room_id={room_id}", flush=True)
            await _wall_round_start(query, context, room_id)
        return True


    # ─── УНИВЕРСАЛЬНОЕ ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ───
    import re as _re_del
    _m_del = _re_del.match(r"^(room|works|plumb|plumb_route|panel_comp|panel|comm|opening)_del_(\d+)$", data)
    if _m_del:
        _prefix = _m_del.group(1)
        _item_id = int(_m_del.group(2))
        _spec = None
        try:
            if _prefix == "room":
                from core import rooms as core_rooms_mod ; _o = core_rooms_mod.get_room(_item_id)
                if _o:
                    _name = "комнату «" + str(_o.get("name") or "?") + "»"
                    _cancel_cb = "room_" + str(_item_id)
                    _spec = ("комнату", _name, _cancel_cb, "room_delok_")
            elif _prefix == "works":
                from core import object_works as _ow_del
                _o = _ow_del.get_work(_item_id)
                if _o:
                    _name = "работу «" + str(_o.get("work_label") or _o.get("work_type") or "?") + "»"
                    _cancel_cb = "works_list_" + str(_o.get("object_id"))
                    _spec = ("работу", _name, _cancel_cb, "works_delok_")
            elif _prefix == "plumb":
                _o = core_plumbing.get_panel(_item_id)
                if _o:
                    _name = "коллектор «" + str(_o.get("name") or "?") + "»"
                    _cancel_cb = "plumb_" + str(_item_id)
                    _spec = ("коллектор", _name, _cancel_cb, "plumb_delok_")
            elif _prefix == "plumb_route":
                _o = core_plumbing.get_route(_item_id)
                if _o:
                    _name = "трассу"
                    _cancel_cb = "plumb_route_" + str(_item_id)
                    _spec = ("трассу", _name, _cancel_cb, "plumb_route_delok_")
            elif _prefix == "panel_comp":
                _o = core_elec_panels.get_component(_item_id)
                if _o:
                    _pid = _o.get("panel_id")
                    _name = "компонент"
                    _cancel_cb = "panel_comp_item_" + str(_item_id)
                    _spec = ("компонент", _name, _cancel_cb, "panel_comp_delok_")
            elif _prefix == "panel":
                _o = core_elec_panels.get_panel(_item_id)
                if _o:
                    _name = "щит «" + str(_o.get("name") or "?") + "»"
                    _cancel_cb = "panel_" + str(_item_id)
                    _spec = ("щит", _name, _cancel_cb, "panel_delok_")
        except Exception as _e:
            print("del interceptor: " + str(_e), flush=True)
            _spec = None
        if _spec:
            _, _name, _cancel_cb, _ok_prefix = _spec
            try:
                await _safe_edit(query, "🗑 *Удалить " + _name + "?*\n\nДействие нельзя отменить.", InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚠️ Да, удалить", callback_data=_ok_prefix + str(_item_id))],
                    [InlineKeyboardButton("❌ Отмена", callback_data=_cancel_cb)],
                ]))
            except Exception:
                pass
            return

    # --- Объекты ---
    if data == "obj_archive_list":
        try:
            from modules.objects import get_archived_objects
            arch = get_archived_objects()
        except Exception as e:
            print("arch list: " + str(e), flush=True)
            arch = []
        if not arch:
            await _safe_edit(query, "📦 Архив пуст", InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="menu_objects")],
            ]))
            return True
        kb_rows = []
        for o in arch:
            kb_rows.append([InlineKeyboardButton("📦 " + str(o.get("name") or "?"), callback_data="obj_" + str(o["id"]))])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_objects")])
        await _safe_edit(query, "📦 Архив (" + str(len(arch)) + "):", InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("obj_archive_"):
        object_id = int(data.replace("obj_archive_", ""))
        try:
            from modules.objects import update_object
            update_object(object_id, status="archived")
        except Exception as e:
            print("archive: " + str(e), flush=True)
        await _safe_edit(query, "📦 Объект в архиве", InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К объектам", callback_data="menu_objects")],
        ]))
        return True

    if data.startswith("obj_unarchive_"):
        object_id = int(data.replace("obj_unarchive_", ""))
        try:
            from modules.objects import update_object
            update_object(object_id, status="active")
        except Exception as e:
            print("unarchive: " + str(e), flush=True)
        await _safe_edit(query, "✅ Объект восстановлен", InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 К архиву", callback_data="obj_archive_list")],
            [InlineKeyboardButton("⬅️ К объектам", callback_data="menu_objects")],
        ]))
        return True

    if data.startswith(("obj_del_", "obj_delok_", "obj_rename_")):
        handled = await handle_object_callback(update, context, data)
        if handled:
            return

    # --- obj_<id> — карточка объекта ---
    # --- Помещения ---
    if data.startswith("obj_floors_"):
        handled = await handle_floors_callback(query, context, data)
        if handled:
            return

    # --- ЭОМ объекта ---
    if data.startswith("obj_elec_") and not data.startswith(("obj_elec_cost_", "obj_elec_pdf_", "obj_elec_labor_")):
        handled = await handle_obj_elec_callback(query, context, data)
        if handled:
            return

    # --- СПЕЦИФИКАЦИЯ ОБЪЕКТА ---
    if data.startswith("obj_spec_"):
        object_id = int(data.replace("obj_spec_", ""))
        if export_object_spec is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_object_spec(object_id)
            if not content:
                raise Exception("Пустая спецификация")
            target = os.path.join(tempfile.gettempdir(), "obj_spec_" + str(object_id) + ".txt")
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            from modules.objects import get_object
            o = get_object(object_id)
            name = o['name'] if o else ('obj_' + str(object_id))
            with open(target, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_spec.txt",
                    caption="📄 Спецификация ЭОМ объекта «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("obj spec: " + str(e), flush=True)
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

    # --- СМЕТА ЭОМ ОБЪЕКТА ---
    if data.startswith("obj_elec_cost_"):
        try:
            object_id = int(data.replace("obj_elec_cost_", ""))
        except ValueError:
            return
        try:
            if core_elec_prices:
                text = core_elec_prices.format_object_elec_total(object_id)
            else:
                text = "Модуль цен не загружен"
        except Exception as e:
            print("obj elec cost: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))],
        ]))
        return

    if data.startswith("obj_") and not data.startswith(("obj_del_", "obj_delok_", "obj_rename_", "obj_floor_", "obj_floors_", "obj_elec_")):
        try:
            object_id = int(data.replace("obj_", ""))
        except ValueError:
            return
        from modules.objects import get_object
        from handlers.commands import object_detail_keyboard
        obj = get_object(object_id)
        if not obj:
            try:
                await query.edit_message_text("❌ Объект не найден")
            except Exception:
                pass
            return
        text = (
            f"🏗️ *{obj['name']}*\n\n"
            f"📍 {obj.get('address') or '—'}\n"
            f"📊 Статус: {obj.get('status') or '—'}"
        )
        try:
            kb = object_detail_keyboard(object_id)
        except Exception as e:
            print(f"⚠️ object_detail_keyboard: {e}", flush=True)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К объектам", callback_data="menu_objects")]])
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return

    # --- Переименование комнаты ---
    if data.startswith("room_rename_"):
        room_id = int(data.replace("room_rename_", ""))
        context.user_data['waiting_for'] = 'room_rename'
        context.user_data['room_rename_id'] = room_id
        try:
            await query.edit_message_text(
                "✏️ *Новое имя комнаты:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    # --- Список комнат объекта ---
    if data.startswith("rooms_list_obj_"):
        object_id = int(data.replace("rooms_list_obj_", ""))
        await show_rooms_list(update, context, object_id)
        return

    # --- Добавление комнаты ---
    if data.startswith("room_add_"):
        tail = data.replace("room_add_", "")
        floor_id = None
        object_id = None
        try:
            from core import floors as _core_floors
            _fl = _core_floors.get_floor(int(tail))
            if _fl:
                floor_id = _fl["id"]
                object_id = _fl["object_id"]
        except Exception:
            pass
        if object_id is None:
            object_id = int(tail)
        context.user_data["room_floor_id"] = floor_id
        context.user_data["room_object_id"] = object_id
        context.user_data["waiting_for"] = "room_name"
        try:
            await query.edit_message_text(
                "📦 *Новая комната*\n\nНапиши название:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"rooms_list_obj_{object_id}")]
                ])
            )
        except Exception:
            pass
        return

    if data.startswith("room_type_"):
        parts = data.replace("room_type_", "").split("_", 1)
        object_id = int(parts[0])
        room_type = parts[1] if len(parts) > 1 else 'rough'
        name = context.user_data.get('room_name_pending') or 'Комната'
        # Привязка к этажу (если известен)
        _fid = context.user_data.get("room_floor_id")
        new_room_id = create_room(object_id, name, room_type=room_type, floor_id=_fid)
        if new_room_id:
            context.user_data['room_name_pending'] = None
            context.user_data['waiting_for'] = None
            await show_room_card(update, context, new_room_id)
        else:
            try:
                await query.edit_message_text("❌ Не удалось создать комнату")
            except Exception:
                pass
        return

    # --- Удаление комнаты ---
    if data.startswith("room_del_"):
        room_id = int(data.replace("room_del_", ""))
        room = get_room(room_id)
        if not room:
            return
        try:
            await query.edit_message_text(
                f"🗑 *Удалить «{room['name']}»?*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"room_delok_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    if data.startswith("room_delok_"):
        room_id = int(data.replace("room_delok_", ""))
        room = get_room(room_id)
        if room:
            object_id = room['object_id']
            delete_room(room_id)
            await show_rooms_list(update, context, object_id)
        return

    # --- Прогресс / размеры / комм / мебель / задачи / фото ---
    if data.startswith("room_progress_"):
        room_id = int(data.replace("room_progress_", ""))
        await _show_room_progress(query, context, room_id)
        return

    if data.startswith("room_measures_"):
        room_id = int(data.replace("room_measures_", ""))
        await _show_room_measures(query, context, room_id)
        return

    if data.startswith("room_objects_"):
        room_id = int(data.replace("room_objects_", ""))
        await _show_room_objects(query, context, room_id)
        return

    if data.startswith("room_tasks_"):
        room_id = int(data.replace("room_tasks_", ""))
        try:
            await query.edit_message_text(
                "📋 Задачи комнаты — в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return

    if data.startswith("room_photos_"):
        room_id = int(data.replace("room_photos_", ""))
        try:
            await query.edit_message_text(
                "📸 Фото комнаты — в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return

    # --- План комнаты (PNG) ---    # --- Помещения ---
    # --- ЩИТЫ ЭОМ ---
    if data.startswith("panels_") or data.startswith("panel_"):
        handled = await handle_panels_callback(query, context, data)
        if handled:
            return

    # --- ЦЕНЫ / МАРКЕТПЛЕЙСЫ ---
    if data.startswith("prices_"):
        handled = await handle_panels_callback(query, context, data)
        if handled:
            return

    # --- САНТЕХНИКА ---
    if data.startswith("plumb_"):
        handled = await handle_panels_callback(query, context, data)
        if handled:
            return

    # --- КАБЕЛЬНЫЙ ЖУРНАЛ ---
    if data.startswith("cables_"):
        handled = await handle_cables_callback(query, context, data)
        if handled:
            return

    # --- КУХОННЫЕ ШАБЛОНЫ (кафе/рестораны) ---
    if data.startswith("floor_kitchen_"):
        handled = await handle_kitchen_callback(query, context, data)
        if handled:
            return

    if data.startswith("obj_floors_") or data.startswith("obj_floor_") or data.startswith("floor_"):
        handled = await handle_floors_callback(query, context, data)
        if handled:
            return

    # --- ЭОМ объекта ---
    if data.startswith("obj_elec_"):
        handled = await handle_obj_elec_callback(query, context, data)
        if handled:
            return

    if data.startswith(("obj_elec_pdf_", "plumb_pdf_obj_", "plumb_labor_obj_")):
        handled = await handle_panels_callback(query, context, data)
        if handled:
            return

    # --- Помещения ---

    if data.startswith("obj_floors_") or data.startswith("floor_"):

        handled = await handle_floors_callback(query, context, data)

        if handled:

            return


    # --- ЭОМ объекта ---

    if data.startswith("obj_elec_"):

        handled = await handle_obj_elec_callback(query, context, data)

        if handled:

            return


    if data.startswith("room_groups_") or data.startswith("group_"):
        handled = await handle_groups_callback(query, context, data)
        if handled:
            return

    if data.startswith("room_reports_") or data.startswith("room_report_"):
        handled = await handle_reports_callback(query, context, data)
        if handled:
            return

    if data.startswith("room_plan_"):
        handled = await handle_plan_callback(query, context, data)
        if handled:
            return

    # --- Экспорт ---
    if data.startswith("room_export_"):
        handled = await handle_export_callback(query, context, data)
        if handled:
            return

    # --- Коммуникации ---
    if data.startswith("comm_") or data.startswith("room_comms_"):
        handled = await handle_comm_callback(query, context, data)
        if handled:
            return

    # --- Проёмы (отдельные) ---
    if data.startswith("openings_") or data.startswith("opening_"):
        handled = await handle_openings_callback(query, context, data)
        if handled:
            return

    # --- Обход стен ---
    if (data.startswith("wall_round_") or data.startswith("wall_niche_")):
        handled = await handle_wall_round_callback(query, context, data)
        if handled:
            return

    # --- room_start / высота ---
    if data.startswith("room_start_"):
        room_id = int(data.replace("room_start_", ""))
        await _handle_room_start(query, context, room_id)
        return

    if data.startswith("room_height_"):
        handled = await _handle_height_callback(query, context, data)
        if handled:
            return

    # --- room_<id> — карточка комнаты ---
    _exclude = ("room_add_", "room_del_", "room_delok_", "room_tasks_",
                "room_measures_", "room_comms_", "room_objects_", "room_photos_",
                "room_type_", "room_method_", "room_height_", "room_start_",
                "room_progress_", "room_rename_", "rooms_list_obj_")
    if data.startswith("room_") and not data.startswith(_exclude):
        try:
            room_id = int(data.replace("room_", ""))
        except ValueError:
            return
        await show_room_card(update, context, room_id)
        return


# ============================================================
# ХЕЛПЕРЫ ЭКРАНОВ КОМНАТ
# ============================================================

async def _show_room_progress(query, context, room_id):
    room = get_room(room_id)
    if not room:
        return
    walls = get_walls_ordered(room_id)
    h_bottom = room.get('height_bottom')
    h_avg = room.get('height')
    height_ok = bool(h_bottom and room.get('height_middle') and room.get('height_top'))
    walls_ok = len(walls) >= core_spec.get_total_walls()
    try:
        r = fetchone("SELECT COUNT(*) as cnt FROM openings WHERE room_id = ?", (room_id,))
        openings_count = r['cnt'] if r else 0
    except Exception:
        openings_count = 0
    try:
        r = fetchone("SELECT COUNT(*) as cnt FROM room_comms WHERE room_id = ?", (room_id,))
        comms_count = r['cnt'] if r else 0
    except Exception:
        comms_count = 0
    text = f"👁 *Что замерено в комнате «{room['name']}»*\n\n"
    if height_ok:
        text += f"📏 Высота: ✅ {int(h_avg) if h_avg == int(h_avg) else round(h_avg, 1)} см\n"
    elif h_bottom:
        text += f"📏 Высота: ⚠️ частично\n"
    else:
        text += f"📏 Высота: ❌ не замерена\n"
    if walls_ok:
        text += f"🧱 Стены: ✅ {len(walls)} шт.\n"
    elif walls:
        text += f"🧱 Стены: ⚠️ {len(walls)} из 4\n"
    else:
        text += f"🧱 Стены: ❌ не замерены\n"
    text += f"🚪 Проёмы: {'✅ ' + str(openings_count) + ' шт.' if openings_count > 0 else '❌ не замерены'}\n"
    text += f"🔧 Коммуникации: {'✅ ' + str(comms_count) + ' шт.' if comms_count > 0 else '❌ не замерены'}\n"
    text += "\n*Что дальше?*"
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Продолжить замер", callback_data=f"room_start_{room_id}")],
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
    except Exception:
        pass


async def _show_room_measures(query, context, room_id):
    measures = get_measures(room_id)
    if not measures:
        try:
            await query.edit_message_text(
                "📐 Размеров пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return
    lines = [f"📐 *Размеры комнаты* ({len(measures)}):\n"]
    for m in measures:
        lines.append(format_measure(m, show_area=True))
    areas = calculate_room_areas(room_id)
    lines.append("")
    if areas.get('walls_net') is not None:
        lines.append(f"Стены: {areas['walls_net']} м²")
    lines.append(f"Пол: {areas['floor']} м²")
    try:
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
    except Exception:
        pass


async def _show_room_objects(query, context, room_id):
    objects = get_room_objects(room_id)
    if not objects:
        try:
            await query.edit_message_text(
                "🪑 Мебели/техники пока нет.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
                ])
            )
        except Exception:
            pass
        return
    lines = [f"🪑 *Мебель/техника* ({len(objects)}):\n"]
    for o in objects:
        lines.append(format_room_object(o))
    try:
        await query.edit_message_text(
            "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data=f"room_{room_id}")]
            ])
        )
    except Exception:
        pass


# ============================================================
# ROOM_START И ВЫСОТА
# ============================================================

async def _handle_room_start(query, context, room_id):
    """Начало/продолжение замера комнаты."""
    print(f"🟣 _handle_room_start: room_id={room_id}", flush=True)
    room = get_room(room_id)
    if not room:
        try:
            await query.edit_message_text("❌ Комната не найдена")
        except Exception:
            pass
        return

    h_bottom = room.get('height_bottom')
    h_middle = room.get('height_middle')
    h_top = room.get('height_top')
    height_ok = bool(h_bottom and h_middle and h_top)
    walls = get_walls_ordered(room_id)
    walls_ok = len(walls) >= core_spec.get_total_walls()

    # === ПРОВЕРКА: Сколько стен? ===
    if height_ok and not walls_ok and not context.user_data.get('total_walls_asked'):
        context.user_data['total_walls_asked'] = True
        context.user_data['wall_room_id'] = room_id
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("3", callback_data=f"room_total_walls_{room_id}_3"),
             InlineKeyboardButton("4", callback_data=f"room_total_walls_{room_id}_4")],
            [InlineKeyboardButton("5", callback_data=f"room_total_walls_{room_id}_5"),
             InlineKeyboardButton("6", callback_data=f"room_total_walls_{room_id}_6")],
            [InlineKeyboardButton("7", callback_data=f"room_total_walls_{room_id}_7"),
             InlineKeyboardButton("8", callback_data=f"room_total_walls_{room_id}_8")],
            [InlineKeyboardButton("✏️ Другое", callback_data=f"room_total_walls_{room_id}_other")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        try:
            await query.edit_message_text("📐 *Сколько стен в комнате?*\n\n_Например: 4_", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            pass
        return

    # === ЭТАП ВЫСОТЫ ===
    if not height_ok:
        if h_bottom and not (h_middle and h_top):
            context.user_data['height_room_id'] = room_id
            context.user_data['height_step'] = 2 if not h_middle else 3
            context.user_data['height_bottom'] = h_bottom
            context.user_data['height_middle'] = h_middle
            context.user_data['height_top'] = h_top
            context.user_data['waiting_for'] = 'room_height_point'
            try:
                await query.edit_message_text(
                    f"🚀 *Продолжаем замер*\n\n📏 Шаг 1: Высота\n✅ Точка 1 (центр): {h_bottom} см",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Продолжить", callback_data=f"room_height_three_start_{room_id}")],
                        [InlineKeyboardButton("🔄 Заново", callback_data=f"room_height_ask_{room_id}")],
                    ])
                )
            except Exception:
                pass
            return
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        try:
            await query.edit_message_text(
                f"🚀 *Мастер замеров*\n\n📏 *Шаг 1 из 3: Высота потолка*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Начать", callback_data=f"room_height_ask_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return

    # === ЭТАП ОБХОДА СТЕН ===
    if not walls_ok:
        # Спросить количество стен (если ещё не задано в этом сеансе)
        if not context.user_data.get('total_walls_asked'):
            context.user_data['total_walls_asked'] = True
            context.user_data['waiting_for'] = 'total_walls'
            try:
                await query.edit_message_text(
                    "📐 Сколько стен в комнате?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("3", callback_data=f"room_total_walls_{room_id}_3")],
                        [InlineKeyboardButton("4", callback_data=f"room_total_walls_{room_id}_4")],
                        [InlineKeyboardButton("5", callback_data=f"room_total_walls_{room_id}_5")],
                        [InlineKeyboardButton("6", callback_data=f"room_total_walls_{room_id}_6")],
                        [InlineKeyboardButton("Другое", callback_data=f"room_total_walls_{room_id}_other")],
                        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                    ])
                )
            except Exception as e:
                print("total_walls ask: " + str(e), flush=True)
            return
        # ⬇⬇⬇ ГЛАВНЫЙ ФИКС ⬇⬇⬇
        # Проверяем черновик — если есть незавершённая стена, восстанавливаем её
        try:
            draft = fetchone("SELECT step_name, step_num FROM wall_drafts WHERE room_id = ?", (room_id,))
        except Exception as e:
            print(f"⚠️ чтение wall_drafts: {e}", flush=True)
            draft = None

        # sqlite3.Row не поддерживает .get() — конвертируем в dict
        if draft:
            try:
                draft = dict(draft)
            except Exception:
                pass

        if draft and draft.get('step_name'):
            print(f"🟢 _handle_room_start: НАЙДЕН ЧЕРНОВИК step_name={draft['step_name']!r}, step_num={draft['step_num']!r} — восстанавливаем", flush=True)
            context.user_data['wall_room_id'] = room_id
            start_walls_round(room_id)
            await _wall_round_start(query, context, room_id)
            return

        # Черновика нет — начинаем с начала
        print(f"🟠 _handle_room_start: черновика нет, начинаем с галочек стены 1", flush=True)
        _reset_wall_state(context, keep_step_num=1)
        state = _get_wall_state(context)
        state['step_num'] = 1
        state['step_name'] = 'flags'
        context.user_data['wall_room_id'] = room_id
        start_walls_round(room_id)
        await _show_wall_step(query, context, room_id, 1, phase='flags', use_photo=True)
        return

    # === ФИНИШ (все стены) ===
    areas = calculate_room_areas(room_id)
    total_length = sum((w['length'] if w['length'] else 0) for w in walls)
    text = (
        f"🎉 *Замер комнаты завершён!*\n\n"
        f"📏 Высота: {room.get('height') or '—'} см\n"
        f"🧱 Стены: {len(walls)} шт.\n"
        f"📐 Сумма длин: {total_length:.0f} см\n"
    )
    if areas.get('walls_net') is not None:
        text += f"📊 Площадь стен: {areas['walls_net']} м²\n"
    if areas.get('floor'):
        text += f"📊 Площадь пола: {areas['floor']} м²\n"
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
    except Exception:
        pass



async def _handle_height_callback(query, context, data):
    """Обработка callback'ов высоты."""
    if data.startswith("room_height_ask_"):
        room_id = int(data.replace("room_height_ask_", ""))
        context.user_data['height_room_id'] = room_id
        try:
            await query.edit_message_text(
                "📏 *Высота потолка*\n\nВысота одинаковая во всей комнате\nили отличается в разных точках?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Одинаковая (1 замер)", callback_data=f"room_height_same_start_{room_id}")],
                    [InlineKeyboardButton("📏 Разная (3 замера)", callback_data=f"room_height_three_start_{room_id}")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("room_height_same_start_"):
        room_id = int(data.replace("room_height_same_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_mode'] = 'same'
        context.user_data['waiting_for'] = 'room_height_same'
        try:
            await query.message.delete()
        except Exception:
            pass
        caption = (
            "📏 *Высота потолка*\n\n"
            "Введи ОДНУ цифру в СМ — она применится ко всем точкам:\n\n"
            "_Например: 305_"
        )
        png = _image_path("height_scheme_step1.png")
        if png and os.path.exists(png):
            try:
                with open(png, "rb") as f:
                    await query.message.chat.send_photo(
                        photo=f, caption=caption, parse_mode=ParseMode.MARKDOWN
                    )
                return True
            except Exception:
                pass
        await query.message.chat.send_message(caption, parse_mode=ParseMode.MARKDOWN)
        return True

    if data.startswith("room_height_three_start_"):
        room_id = int(data.replace("room_height_three_start_", ""))
        context.user_data['height_room_id'] = room_id
        context.user_data['height_step'] = 1
        context.user_data['height_bottom'] = None
        context.user_data['height_middle'] = None
        context.user_data['height_top'] = None
        context.user_data['waiting_for'] = 'room_height_point'
        context.user_data['height_mode'] = 'three'
        await _show_height_step(query, context, room_id, step=1)
        return True

    if data.startswith("room_height_same_"):
        # Старое — уже обрабатывается вводом
        return True

    return False


# ============================================================
# ОБРАБОТЧИК ВВОДА (главный)
# ============================================================

async def _handle_group_load_input(update, context):
    """Обработка ввода мощности группы ЭОМ."""
    if not core_elec:
        await update.message.reply_text("❌ Модуль ЭОМ не загружен")
        context.user_data['waiting_for'] = None
        return

    floor_id = context.user_data.get('group_floor_id')
    room_id = context.user_data.get('group_room_id')
    purpose = context.user_data.get('group_purpose')
    phase = context.user_data.get('group_phase') or 1

    object_id = None
    if floor_id:
        try:
            from core.floors import get_floor
            floor = get_floor(floor_id)
            object_id = floor.get('object_id') if floor else None
        except Exception:
            pass
    if not object_id and room_id:
        try:
            from core.rooms import get_room
            room = get_room(room_id)
            object_id = room.get('object_id') if room else None
            if not floor_id and room:
                floor_id = room.get('floor_id')
        except Exception:
            pass

    if not (object_id and purpose):
        await update.message.reply_text("❌ Потерялись данные группы")
        context.user_data['waiting_for'] = None
        return

    text_val = (update.message.text or '').strip().replace(',', '.')
    try:
        load_watt = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Нужно число (Вт)")
        return

    if load_watt <= 0 or load_watt > 100000:
        await update.message.reply_text("❌ Мощность от 1 до 100 000 Вт")
        return

    supply = core_elec.get_supply(object_id)
    if not supply:
        core_elec.set_supply(object_id, phase_count=1, voltage=220)

    voltage = 380 if phase == 3 else 220
    current = core_elec.calc_current(load_watt, phase, voltage)
    rating, curve = core_elec.pick_breaker(load_watt, phase, 'C')
    cable = core_elec.pick_cable(load_watt, phase, voltage)
    breaker_type = f"{'3P' if phase == 3 else '1P'} {curve}{rating}"

    purpose_label = core_spec.PURPOSE_TYPES.get(purpose, purpose).split(' ', 1)[-1]
    name = f"{purpose_label} {int(load_watt)}Вт"

    try:
        group_id = core_elec.create_group(
            object_id=object_id,
            room_id=None,
            name=name,
            phase=phase,
            purpose=purpose,
            cable_type=cable,
            load_watt=load_watt,
            breaker_type=breaker_type,
            breaker_curve=curve,
            floor_id=floor_id,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка создания группы: {e}")
        context.user_data['waiting_for'] = None
        return

    for k in ['group_room_id', 'group_floor_id', 'group_purpose', 'group_phase']:
        context.user_data[k] = None
    context.user_data['waiting_for'] = None

    _object_panels = []
    try:
        if core_elec_panels:
            _object_panels = core_elec_panels.get_panels(object_id)
            if len(_object_panels) == 1:
                core_elec_panels.assign_group_to_panel(group_id, _object_panels[0]["id"])
                core_elec_panels.recalc_panel_safe(_object_panels[0]["id"])
    except Exception as _e:
        print("auto assign: " + str(_e), flush=True)

    text = (
        f"✅ *Группа создана*\n\n"
        f"⚡ *{name}*\n"
        f"Фаза: {phase}ф ({voltage}В)\n"
        f"Мощность: {int(load_watt)} Вт\n"
        f"Ток: {current} А\n"
        f"Автомат: *{breaker_type}*\n"
        f"Кабель: *{core_spec.get_cable_label(cable)}*"
        f"Щит: " + (core_elec_panels.get_panel(_object_panels[0]["id"])["name"] if (_object_panels and len(_object_panels) == 1 and core_elec_panels) else "не привязан") + "\n"
    )

    # Кнопки — ведём к группам этажа
    kb_btns = []
    if floor_id:
        kb_btns.append([InlineKeyboardButton("➕ Ещё группу", callback_data=f"floor_group_new_{floor_id}")])
        kb_btns.append([InlineKeyboardButton("⚡ К группам этажа", callback_data=f"floor_groups_{floor_id}")])
    if room_id:
        kb_btns.append([InlineKeyboardButton("⚡ К группам комнаты", callback_data=f"room_groups_{room_id}")])

        if len(_object_panels) > 1:
            kb_btns.append([InlineKeyboardButton("⚡ Привязать к щиту", callback_data="group_panel_pick_" + str(group_id))])

    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb_btns) if kb_btns else None
    )


async def handle_measure_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер текстового ввода по waiting_for."""
    step = context.user_data.get('waiting_for')
    if not step:
        return

    # --- КАБЕЛЬНЫЙ ЖУРНАЛ ---
    if step == 'cable_from_point':
        val = (update.message.text or '').strip()
        if not val:
            await update.message.reply_text("Введи текст")
            return
        context.user_data['cable_from_point'] = val
        context.user_data['waiting_for'] = 'cable_to_point'
        await update.message.reply_text("Куда кабель (к точке)?")
        return

    if step == 'cable_to_point':
        val = (update.message.text or '').strip()
        if not val:
            await update.message.reply_text("Введи текст")
            return
        context.user_data['cable_to_point'] = val
        context.user_data['waiting_for'] = 'cable_length'
        await update.message.reply_text("Длина кабеля (метры)?")
        return

    if step == 'cable_length':
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            length_m = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if length_m <= 0 or length_m > 1000:
            await update.message.reply_text("Длина от 0.1 до 1000 м")
            return
        object_id = context.user_data.get('cable_object_id')
        group_id = context.user_data.get('cable_group_id')
        frm = context.user_data.get('cable_from_point')
        to = context.user_data.get('cable_to_point')
        cable_type = None
        try:
            if group_id:
                _g = core_elec.get_group(group_id)
                cable_type = _g.get('cable_type') if _g else None
        except Exception:
            pass
        try:
            core_elec.add_cable(
                object_id=object_id,
                group_id=group_id,
                from_point=frm,
                to_point=to,
                cable_type=cable_type,
                length_m=length_m,
                route_type=None,
                note=None,
            )
        except Exception as e:
            print(f"add_cable: {e}", flush=True)
        for k in ['cable_object_id', 'cable_group_id', 'cable_from_point', 'cable_to_point', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            "Кабель добавлен!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("К журналу", callback_data="cables_list_" + str(object_id))],
            ])
        )
        return

    if step == 'route_length':
        route_id = context.user_data.get('route_edit_id')
        if not route_id:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            length = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if length <= 0 or length > 10000:
            await update.message.reply_text("Длина от 0.1 до 10 000 м")
            return
        try:
            core_elec_routes.update_route(route_id, length_m=length, is_manual=1)
        except Exception as e:
            print("route set len: " + str(e), flush=True)
        for k in ['route_edit_id', 'waiting_for']:
            context.user_data[k] = None
        try:
            r = core_elec_routes.get_route(route_id)
            gid = r.get('group_id') if r else None
        except Exception:
            gid = None
        kb = []
        if gid:
            kb.append([InlineKeyboardButton("📏 К трассам", callback_data="group_routes_" + str(gid))])
        kb.append([InlineKeyboardButton("⬅️ К трассе", callback_data="route_" + str(route_id))])
        await update.message.reply_text(
            "✅ Длина сохранена: " + str(length) + " м",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if step == 'plumb_route_length':
        panel_id = context.user_data.get('plumb_route_panel_id')
        pipe_type = context.user_data.get('plumb_route_pipe')
        if not panel_id or not pipe_type:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            length = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if length <= 0 or length > 10000:
            await update.message.reply_text("Длина от 0.1 до 10 000 м")
            return
        try:
            p = core_plumbing.get_panel(panel_id)
            object_id = p.get('object_id') if p else None
            rid = core_plumbing.create_route(
                object_id=object_id, panel_id=panel_id,
                pipe_type=pipe_type, length_m=length,
                route_type='shtroba'
            )
        except Exception as e:
            print("plumb route create: " + str(e), flush=True)
            rid = None
        for k in ['plumb_route_panel_id', 'plumb_route_pipe', 'waiting_for']:
            context.user_data[k] = None
        if rid:
            await update.message.reply_text(
                "Трасса создана: " + core_plumbing.get_pipe_label(pipe_type) + " · " + str(length) + " м",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📏 К трассам", callback_data="plumb_routes_" + str(panel_id))],
                    [InlineKeyboardButton("📏 Открыть", callback_data="plumb_route_" + str(rid))],
                ])
            )
        else:
            await update.message.reply_text("Не удалось создать трассу")
        return

    if step == 'work_edit_value':
        work_id = context.user_data.get('work_edit_id')
        field = context.user_data.get('work_edit_field')
        if not work_id or not field:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            num = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if num <= 0 or num > 1000000:
            await update.message.reply_text("Значение от 0.1 до 1 000 000")
            return
        try:
            core_works.update_work(work_id, **{field: num, 'is_manual': 1})
        except Exception as e:
            print("work edit: " + str(e), flush=True)
        for k in ['work_edit_id', 'work_edit_field', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            "Сохранено",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔨 К работе", callback_data="works_" + str(work_id))],
            ])
        )
        return

    if step == 'work_new_qty':
        object_id = context.user_data.get('work_new_object_id')
        wtype = context.user_data.get('work_new_type')
        if not object_id or not wtype:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            qty = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if qty <= 0 or qty > 100000:
            await update.message.reply_text("Количество от 0.1 до 100 000")
            return
        try:
            wid = core_works.create_work(object_id, wtype, qty=qty)
        except Exception as e:
            print("work create: " + str(e), flush=True)
            wid = None
        for k in ['work_new_object_id', 'work_new_type', 'waiting_for']:
            context.user_data[k] = None
        if wid:
            await update.message.reply_text(
                "Работа добавлена",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔨 К работам", callback_data="works_list_" + str(object_id))],
                ])
            )
        else:
            await update.message.reply_text("Не удалось добавить")
        return

    if step == 'plumb_new_name':
        name = (update.message.text or '').strip()
        if not name:
            await update.message.reply_text("Введи название")
            return
        object_id = context.user_data.get('plumb_new_object_id')
        ptype = context.user_data.get('plumb_new_type') or 'collector'
        if not object_id:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        try:
            pid = core_plumbing.create_panel(object_id, name, ptype, mount_type='wall')
        except Exception as e:
            print("plumb create: " + str(e), flush=True)
            pid = None
        for k in ['plumb_new_object_id', 'plumb_new_type', 'waiting_for']:
            context.user_data[k] = None
        if pid:
            await update.message.reply_text(
                "Создано: " + name,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Открыть", callback_data="plumb_" + str(pid))],
                    [InlineKeyboardButton("К сантехнике", callback_data="plumb_list_" + str(object_id))],
                ])
            )
        else:
            await update.message.reply_text("Не удалось создать")
        return

    if step == 'component_price':
        comp_id = context.user_data.get('component_price_id')
        if not comp_id:
            await update.message.reply_text("Потерялись данные")
            context.user_data['waiting_for'] = None
            return
        val = (update.message.text or '').strip().replace(',', '.')
        try:
            price = float(val)
        except ValueError:
            await update.message.reply_text("Нужно число")
            return
        if price < 0 or price > 1000000:
            await update.message.reply_text("Цена от 0 до 1 000 000")
            return
        try:
            from core.db import commit
            commit("UPDATE elec_panel_components SET price_unit = ?, price_source = 'manual', price_updated_at = CURRENT_TIMESTAMP WHERE id = ?", (price, comp_id))
        except Exception as e:
            print("set price: " + str(e), flush=True)
        for k in ['component_price_id', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            "✅ Цена сохранена: " + str(price) + " ₽",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К компоненту", callback_data="panel_comp_item_" + str(comp_id))],
            ])
        )
        return

    if step == 'panel_new_name':
        name = (update.message.text or '').strip()
        if not name:
            await update.message.reply_text("Введи название")
            return
        object_id = context.user_data.get('panel_new_object_id')
        ptype = context.user_data.get('panel_new_type') or 'floor'
        if not object_id:
            await update.message.reply_text("Потерялись данные. Начни заново.")
            context.user_data['waiting_for'] = None
            return
        try:
            pid = core_elec_panels.create_panel(
                object_id=object_id, name=name, panel_type=ptype, mount_type='wall'
            )
        except Exception as e:
            print("panel create: " + str(e), flush=True)
            pid = None
        for k in ['panel_new_object_id', 'panel_new_type', 'waiting_for']:
            context.user_data[k] = None
        if pid:
            await update.message.reply_text(
                "Щит создан: " + name,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(pid))],
                    [InlineKeyboardButton("К щитам", callback_data="panels_list_" + str(object_id))],
                ])
            )
        else:
            await update.message.reply_text("Не удалось создать щит")
        return

    if step == 'group_load_watt':
        await _handle_group_load_input(update, context)
        return

    # --- ЭОМ: ввод мощности группы ---
    if step == 'group_load_watt':
        await _handle_group_load_input(update, context)
        return

    # --- Помещения: ввод названия ---
    if step == 'floor_new_name':
        object_id = context.user_data.get('floor_obj_id')
        name = (update.message.text or '').strip()
        if object_id and name:
            try:
                # Автосоздание Дом-корня
                root_id = core_floors.ensure_default_house(object_id)
                f_type = context.user_data.get("floor_new_type") or "floor"
                f_parent = context.user_data.get("floor_new_parent")
                if f_parent is None:
                    f_parent = root_id
                floor_id = core_floors.create_floor(object_id, floor_number=1, floor_name=name,
                                                     parent_id=f_parent, type=f_type)
                context.user_data['waiting_for'] = None
                context.user_data.pop('floor_new_type', None)
                context.user_data.pop('floor_new_parent', None)
                context.user_data['floor_obj_id'] = None
                # Показать карточку помещения
                await update.message.reply_text(
                    f"✅ Помещение «{name}» создано.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏠 Открыть", callback_data=f"floor_{floor_id}")],
                        [InlineKeyboardButton("⬅️ К помещениям", callback_data=f"obj_floors_{object_id}")],
                    ])
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {e}")
        else:
            await update.message.reply_text("❌ Введи название")
        return

    # --- Переименование комнаты ---
    if step == 'room_rename':
        room_id = context.user_data.get('room_rename_id')
        new_name = (update.message.text or '').strip()
        if room_id and new_name:
            try:
                update_room(room_id, name=new_name)
            except Exception:
                db_commit("UPDATE rooms SET name = ? WHERE id = ?", (new_name, room_id))
            context.user_data['waiting_for'] = None
            context.user_data['room_rename_id'] = None
            await update.message.reply_text(
                f"✅ Имя комнаты изменено на «{new_name}»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        return

    # --- Высота ---
    if step == 'total_walls':
        try:
            n = int((update.message.text or '').strip())
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        if n < 3 or n > 12:
            await update.message.reply_text("❌ От 3 до 12")
            return
        core_spec.set_total_walls(n)
        context.user_data['total_walls_asked'] = False
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            "✅ Стён: " + str(n),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Начать обход", callback_data="wall_round_start_" + str(context.user_data.get('wall_room_id') or 0))],
            ])
        )
        return

    if step == 'room_height_point':
        room_id = context.user_data.get('height_room_id')
        if not room_id:
            await update.message.reply_text("❌ Потерялась комната")
            return
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        h_step = context.user_data.get('height_step') or 1
        if h_step == 1:
            context.user_data['height_bottom'] = val
            context.user_data['height_step'] = 2
            await _show_height_step(update, context, room_id, step=2)
        elif h_step == 2:
            context.user_data['height_middle'] = val
            context.user_data['height_step'] = 3
            await _show_height_step(update, context, room_id, step=3)
        else:
            context.user_data['height_top'] = val
            h_bottom = context.user_data.get('height_bottom')
            h_middle = context.user_data.get('height_middle')
            h_top = val
            h_avg = (h_bottom + h_middle + h_top) / 3
            update_room(room_id, height=h_avg, height_bottom=h_bottom,
                        height_middle=h_middle, height_top=h_top)
            for k in ['waiting_for', 'height_room_id', 'height_step',
                      'height_bottom', 'height_middle', 'height_top']:
                context.user_data[k] = None
            await update.message.reply_text(
                f"✅ *Высота сохранена:*\n"
                f"Центр: {h_bottom} см\nЛевый: {h_middle} см\nПравый: {h_top} см\n"
                f"Среднее: {round(h_avg, 1)} см",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 Начать обход стен", callback_data=f"wall_round_start_{room_id}")],
                    [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
                ])
            )
        return

    if step == 'room_height_same':
        room_id = context.user_data.get('height_room_id')
        text_val = (update.message.text or '').strip().replace(',', '.')
        try:
            val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            return
        update_room(room_id, height=val, height_bottom=val, height_middle=val, height_top=val)
        for k in ['waiting_for', 'height_room_id', 'height_step']:
            context.user_data[k] = None
        await update.message.reply_text(
            f"✅ *Высота: {val} см* (везде одинаковая)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📐 Начать обход", callback_data=f"wall_round_start_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    # --- Обход стен ---
    if step in ('wall_round_length', 'wall_round_angle_val',
                'wall_round_plane_bottom', 'wall_round_plane_middle', 'wall_round_plane_top',
                'wall_niche_width', 'wall_niche_depth', 'wall_niche_height',
                'wall_niche_top_width', 'wall_niche_top_depth',
                'wall_rounded_radius', 'wall_wavy_note', 'wall_hidden_note',
                'wall_round_opening_width', 'wall_round_opening_height'):
        await _handle_wall_round_input(update, context, step)
        return

    # --- Коммуникации ---
    if step in ('comm_offset_x', 'comm_offset_y', 'comm_diameter', 'comm_voltage',
                'comm_size_w', 'comm_size_h', 'comm_size_d',
                'comm_edit_value', 'comm_edit_size_part'):
        await _handle_comm_input(update, context, step)
        return

    # --- Проёмы (отдельные) ---
    if step in ('opening_width', 'opening_height', 'opening_edit_value'):
        await _handle_opening_input(update, context, step)
        return


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

def _build_panel_total_text(panel_id):
    """Текст общей сметы щита: компоненты + монтаж."""
    from core.elec_panels import get_panel, calc_panel_cost, get_groups_by_panel
    from core import elec_routes as er

    p = get_panel(panel_id)
    if not p:
        return "Щит не найден"

    # Компоненты
    panels_cost = calc_panel_cost(panel_id)

    # Монтаж
    montage_cost = 0.0
    montage_m = 0.0
    try:
        montage = er.calc_montage_cost_by_panel(panel_id)
        montage_cost = montage['total']
        montage_m = montage['total_m']
    except Exception as e:
        print("montage cost: " + str(e), flush=True)

    total = panels_cost + montage_cost

    lines = [
        "💰 Общая смета щита «" + str(p.get('name') or '?') + "»",
        "",
        "── ЩИТ ──",
        "Компоненты щита: " + str(panels_cost) + " ₽",
        "",
        "── ЭЛЕКТРОМОНТАЖ ──",
        "Метраж: " + str(montage_m) + " м",
        "Кабель + расходники: " + str(montage_cost) + " ₽",
        "",
        "───────────────────────",
        "💰 ВСЕГО: " + str(round(total, 2)) + " ₽",
    ]
    return chr(10).join(lines)





# === Elec (вынесено в rooms_elec.py) ===
from .rooms_elec import *
from .rooms_elec import _show_route_card

# === Reports (вынесено в rooms_reports.py) ===
from .rooms_reports import *
from .rooms_reports import _do_report_electric, _do_export_dxf, _do_export_csv, _do_export_json
