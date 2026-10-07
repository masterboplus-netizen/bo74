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

WALL_NAMES = {1: "напротив", 2: "слева", 3: "у входа", 4: "справа"}
WALL_NAMES_REVERSE = {v: k for k, v in WALL_NAMES.items()}

DEFAULT_FLAGS = {"niche": False, "rounded": False, "wavy": False, "hidden": False}


# ============================================================
# ЕДИНЫЙ STATE СТЕНЫ
# ============================================================

def _get_wall_state(context):
    """Возвращает единый state текущей стены (создаёт, если нет)."""
    if 'wall_state' not in context.user_data or context.user_data['wall_state'] is None:
        context.user_data['wall_state'] = {
            'step_num': 1,
            'step_name': 'flags',
            'flags': dict(DEFAULT_FLAGS),
            'length': None,
            'plane': None,
            'angle_value': None,
            'angle_method': None,
            'niches': [],
            'niche_count': 0,
            'niche_current': 0,
            'niche_temp': {},
            'remaining_steps': None,  # None — маркер «первый заход»
        }
    return context.user_data['wall_state']



def _reset_wall_state(context, keep_step_num=None):
    """Сбрасывает state стены.

    keep_step_num — сохранить этот номер стены. По умолчанию — из старого state.
    """
    step_num = keep_step_num
    if step_num is None:
        old_state = context.user_data.get('wall_state') or {}
        step_num = old_state.get('step_num') or 1
    context.user_data['wall_state'] = {
        'step_num': step_num,
        'step_name': 'flags',
        'flags': dict(DEFAULT_FLAGS),
        'length': None,
        'plane': None,
        'angle_value': None,
        'angle_method': None,
        'niches': [],
        'niche_count': 0,
        'niche_current': 0,
        'niche_temp': {},
        'remaining_steps': None,
    }

def _save_wall_draft(context, room_id):
    """Сохраняет ВЕСЬ state стены в БД (без параметра step_name)."""
    state = _get_wall_state(context)
    try:
        db_commit(
            """INSERT OR REPLACE INTO wall_drafts
            (room_id, step_num, step_name, flags, length, plane,
             angle_value, angle_method, niches, niche_count, niche_current,
             niche_temp, remaining_steps, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (
                room_id,
                state.get('step_num') or 1,
                state.get('step_name') or 'flags',
                json.dumps(state.get('flags') or DEFAULT_FLAGS, ensure_ascii=False),
                state.get('length'),
                state.get('plane'),
                state.get('angle_value'),
                state.get('angle_method'),
                json.dumps(state.get('niches') or [], ensure_ascii=False),
                state.get('niche_count') or 0,
                state.get('niche_current') or 0,
                json.dumps(state.get('niche_temp') or {}, ensure_ascii=False),
                json.dumps(state.get('remaining_steps'), ensure_ascii=False),
            )
        )
    except Exception as e:
        print(f"⚠️ _save_wall_draft: {e}", flush=True)


def _load_wall_draft(context, room_id):
    """Загружает черновик стены из БД. Возвращает step_name или None."""
    try:
        draft = fetchone("SELECT * FROM wall_drafts WHERE room_id = ?", (room_id,))
    except Exception as e:
        print(f"⚠️ _load_wall_draft: {e}", flush=True)
        return None
    if not draft:
        return None
    draft = dict(draft)
    state = _get_wall_state(context)
    state['step_num'] = draft.get('step_num') or 1
    state['step_name'] = draft.get('step_name') or 'flags'
    try:
        flags = json.loads(draft.get('flags') or '{}')
        state['flags'] = flags if flags else dict(DEFAULT_FLAGS)
    except Exception:
        state['flags'] = dict(DEFAULT_FLAGS)
    state['length'] = draft.get('length')
    state['plane'] = draft.get('plane')
    state['angle_value'] = draft.get('angle_value')
    state['angle_method'] = draft.get('angle_method')
    try:
        state['niches'] = json.loads(draft.get('niches') or '[]')
    except Exception:
        state['niches'] = []
    state['niche_count'] = draft.get('niche_count') or 0
    state['niche_current'] = draft.get('niche_current') or 0
    try:
        state['niche_temp'] = json.loads(draft.get('niche_temp') or '{}')
    except Exception:
        state['niche_temp'] = {}
    try:
        rs = json.loads(draft.get('remaining_steps') or 'null')
        # Сохраняем None как маркер «первый заход», [] как «всё обработано»
        state['remaining_steps'] = rs
    except Exception:
        state['remaining_steps'] = None
    return state['step_name']


def _clear_wall_draft(room_id):
    """Удаляет черновик стены."""
    try:
        db_commit("DELETE FROM wall_drafts WHERE room_id = ?", (room_id,))
    except Exception as e:
        print(f"⚠️ _clear_wall_draft: {e}", flush=True)


# ============================================================
# ХЕЛПЕРЫ
# ============================================================

def _current_wall_pos(context):
    """Текущая позиция стены (строка) из state."""
    state = _get_wall_state(context)
    return WALL_NAMES.get(state.get('step_num') or 1, '?')


def _wall_flags_list(context):
    """Возвращает список флагов, которые надо обработать после угла.

    ПРАВИЛО:
    - wavy не добавляем, если плоскость УЖЕ пройдена через 3 точки (plane='wavy').
    - Функция НЕ очищает флаги — этим занимается _after_angle.
    """
    state = _get_wall_state(context)
    flags = state.get('flags') or {}
    steps = []
    if flags.get('niche'):
        steps.append('niche')
    if flags.get('rounded'):
        steps.append('rounded')
    if flags.get('wavy') and state.get('plane') != 'wavy':
        steps.append('wavy')
    if flags.get('hidden'):
        steps.append('hidden')
    return steps


def _image_path(filename):
    """Путь к PNG-схеме."""
    if not filename:
        return None
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "docs", "images", filename)


async def _send_png_or_edit(query, caption, kb, png_filename=None):
    """Отправляет фото или редактирует сообщение.

    Если png есть — удаляет старое сообщение, шлёт фото в тот же чат.
    Если png нет — пытается edit, при неудаче — новое сообщение.
    """
    png = _image_path(png_filename)
    chat_id = query.message.chat_id

    if png and os.path.exists(png):
        # Удаляем старое сообщение (в try — может быть уже удалено)
        try:
            await query.message.delete()
        except Exception:
            pass
        # Отправляем фото — ВСЕГДА в chat_id (не через query.message.chat)
        try:
            with open(png, "rb") as f:
                await query.get_bot().send_photo(
                    chat_id=chat_id,
                    photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            return
        except Exception as e:
            print(f"⚠️ send_photo: {e}", flush=True)
        # Fallback — просто текст, тоже через bot
        try:
            await query.get_bot().send_message(
                chat_id=chat_id, text=caption,
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
            return
        except Exception as e:
            print(f"⚠️ send_message fallback: {e}", flush=True)
        return

    # PNG нет — редактируем существующее сообщение.
    # Если это ФОТО — используем edit_message_caption, если текст — edit_message_text.
    msg = query.message
    is_photo = bool(getattr(msg, "photo", None))
    print(f"🟡 _send_png_or_edit (no png): is_photo={is_photo}, caption={caption[:60]!r}", flush=True)

    try:
        if is_photo:
            await query.edit_message_caption(
                caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        else:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        print(f"🟢 _send_png_or_edit (no png): OK", flush=True)
    except Exception as e:
        err = str(e).lower()
        print(f"⚠️ _send_png_or_edit (no png) edit failed: {e}", flush=True)
        if "message is not modified" in err:
            return
        if "message to edit not found" in err or "not found" in err or "query is too old" in err:
            try:
                await query.get_bot().send_message(
                    chat_id=chat_id, text=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
                print(f"🟢 _send_png_or_edit (no png): fallback OK", flush=True)
            except Exception as e2:
                print(f"⚠️ send_message: {e2}", flush=True)


async def _send_png_or_reply(message, caption, kb=None, png_filename=None):
    """Отправляет фото или текстовое сообщение (для update.message)."""
    png = _image_path(png_filename)
    if png and os.path.exists(png):
        try:
            with open(png, "rb") as f:
                await message.reply_photo(
                    photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            return
        except Exception as e:
            print(f"⚠️ reply_photo: {e}", flush=True)
    await message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


# ============================================================
# КЛАВИАТУРЫ
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
    walls_ok = len(walls) >= 4

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

async def _show_wall_step(query, context, room_id, step, phase='flags', use_photo=False):
    """Экран галочек стены.

    use_photo=True — только при первом входе на стену (отправка фото).
    use_photo=False — при обновлении галочек (просто edit_message_text, БЕЗ мигания).
    """
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = phase
    _save_wall_draft(context, room_id)

    pos = WALL_NAMES.get(step, '?')
    flags = state.get('flags') or DEFAULT_FLAGS

    spec_step = spec.get_wall_step('flags', n=step, pos=pos)
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        image = spec_step.get('image')
    else:
        caption = f"🧱 *Стена {step} — {pos}*\n\n👁 Осмотри стену.\nОтметь особенности:"
        image = f"wall_scheme_s{step}_flags.png"

    f_niche = '✅' if flags.get('niche') else '⬜'
    f_rounded = '✅' if flags.get('rounded') else '⬜'
    f_wavy = '✅' if flags.get('wavy') else '⬜'
    f_hidden = '✅' if flags.get('hidden') else '⬜'

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{f_niche} С нишей", callback_data=f"wall_round_flag_niche_{room_id}")],
        [InlineKeyboardButton(f"{f_rounded} С закруглением", callback_data=f"wall_round_flag_rounded_{room_id}")],
        [InlineKeyboardButton(f"{f_wavy} Разная по высоте", callback_data=f"wall_round_flag_wavy_{room_id}")],
        [InlineKeyboardButton(f"{f_hidden} Скрытые коммуникации", callback_data=f"wall_round_flag_hidden_{room_id}")],
        [InlineKeyboardButton("➡️ Дальше", callback_data=f"wall_round_flags_done_{room_id}")],
        [InlineKeyboardButton("⏭ Пропустить стену", callback_data=f"wall_round_skip_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    # При обновлении галочек — просто редактируем (плавно, без мигания)
    if use_photo:
        await _send_png_or_edit(query, caption, kb, image)
        return

    # use_photo=False — редактируем существующее сообщение.
    # Если это фото — edit_caption; если текст — edit_text.
    # Никогда не пересоздаём, не шлём новое сообщение.
    msg = query.message
    is_photo = bool(getattr(msg, "photo", None))

    try:
        if is_photo:
            await query.edit_message_caption(
                caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        else:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
    except Exception as e:
        err = str(e).lower()
        if "message is not modified" in err:
            return
        print(f"⚠️ _show_wall_step edit: {e}", flush=True)


async def _show_wall_plane(query, context, room_id):
    """Экран плоскости стены (ровная / кривая)."""
    state = _get_wall_state(context)
    state['step_name'] = 'plane'
    _save_wall_draft(context, room_id)

    step = state.get('step_num') or 1
    flags = state.get('flags') or {}

    # Если галочка "Разная по высоте" уже стоит — сразу ввод 3 точек (с фото)
    if flags.get('wavy'):
        state['plane'] = 'wavy'
        state['step_name'] = 'plane_wavy'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        caption = (
            f"🧱 *Стена {step}*\n\n"
            f"📏 *Замер в 3 точках:*\n\n"
            f"Введи НИЗ стены (СМ):"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В комнату", callback_data=f"room_{room_id}")],
        ])
        # Фото для этого шага нет — только текст
        try:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            try:
                await query.get_bot().send_message(
                    chat_id=query.message.chat_id, text=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            except Exception as e:
                print(f"⚠️ plane (wavy) send: {e}", flush=True)
        return

    spec_step = spec.get_wall_step('plane', n=step, pos=WALL_NAMES.get(step, '?'))
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        if spec_step.get('hint'):
            caption += f"\n\n{spec_step['hint']}"
        image = spec_step.get('image')
    else:
        caption = (
            f"🧱 *Стена {step}*\n\n"
            f"📐 *Плоскость стены:*\n\n"
            f"Стена ровная или кривая по высоте?\n\n"
            f"_Если стена «горбатая» — нужно замерить в 3 точках._"
        )
        image = f"wall_scheme_s{step}_plane.png"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_round_plane_straight_{room_id}")],
        [InlineKeyboardButton("📏 Разная (3 точки)", callback_data=f"wall_round_plane_wavy_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_wall_length(query, context, room_id, step):
    """Экран длины стены."""
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = 'length'
    _save_wall_draft(context, room_id)

    context.user_data['waiting_for'] = 'wall_round_length'
    pos = WALL_NAMES.get(step, '?')

    spec_step = spec.get_wall_step('length', n=step, pos=pos)
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        if spec_step.get('hint'):
            caption += f"\n\n{spec_step['hint']}"
        if spec_step.get('prompt'):
            caption += f"\n\n{spec_step['prompt']}"
        image = spec_step.get('image')
    else:
        caption = (
            f"🧱 *Стена {step} — {pos}*\n\n"
            f"📏 *Длина стены* (СМ):\n\n"
            f"⚠️ *ВАЖНО:* дальномер в режиме «от ЗАДНЕЙ СТЕНКИ».\n\n"
            f"Напиши число и отправь."
        )
        image = f"wall_scheme_s{step}_length.png"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_wall_openings(query, context, room_id, step):
    """Экран проёмов стены."""
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = 'openings'
    _save_wall_draft(context, room_id)

    context.user_data['waiting_for'] = None
    pos = WALL_NAMES.get(step, '?')
    length_cm = state.get('length') or 0
    openings = get_openings_by_wall(room_id, pos)

    text = f"🧱 *Стена {step} — {pos}*\n📏 Длина: *{length_cm} см*\n\n"
    if openings:
        text += f"🚪 *Проёмы ({len(openings)}):*\n"
        for o in openings:
            text += f"  • {format_opening(o)}\n"
    else:
        text += "🚪 *Есть ли на этой стене проёмы?*"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪟 Окно", callback_data=f"wall_round_open_win_{room_id}"),
         InlineKeyboardButton("🚪 Дверь", callback_data=f"wall_round_open_door_{room_id}")],
        [InlineKeyboardButton("💨 Вентиляция", callback_data=f"wall_round_open_vent_{room_id}")],
        [InlineKeyboardButton("✅ Готово", callback_data=f"wall_round_openings_done_{room_id}")],
    ])
    await _send_png_or_edit(query, text, kb, None)


async def _show_wall_angle(query, context, room_id, step, use_photo=False):
    """Экран угла между стенами.

    use_photo=True — при первом входе (пересоздать сообщение с фото).
    use_photo=False — при восстановлении/возврате (edit_caption, без пересоздания).
    """
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = 'angle'
    _save_wall_draft(context, room_id)

    context.user_data['waiting_for'] = None
    length_cm = state.get('length') or 0

    spec_step = spec.get_wall_step('angle', n=step, pos=WALL_NAMES.get(step, '?'), length=length_cm)
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        if spec_step.get('hint'):
            caption += f"\n\n{spec_step['hint']}"
        image = spec_step.get('image')
    else:
        caption = (
            f"✅ Длина: *{length_cm} см*\n\n"
            f"📐 *Угол между этой стеной и следующей:*\n\n"
            f"Обычно 90° — прямой угол."
        )
        image = f"wall_scheme_s{step}_angle.png"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 90° (прямой)", callback_data=f"wall_round_angle_90_{room_id}")],
        [InlineKeyboardButton("📏 60-80-100", callback_data=f"wall_round_angle_60_{room_id}")],
        [InlineKeyboardButton("📏 100-100", callback_data=f"wall_round_angle_100_{room_id}")],
        [InlineKeyboardButton("✏️ Угол в °", callback_data=f"wall_round_angle_deg_{room_id}")],
        [InlineKeyboardButton("⬅️ В комнату", callback_data=f"room_{room_id}")],
    ])
    if use_photo:
        await _send_png_or_edit(query, caption, kb, image)
        return

    # use_photo=False — редактируем существующее, при неудаче — пересоздаём.
    msg = query.message
    is_photo = bool(getattr(msg, "photo", None))
    print(f"🟠 _show_wall_angle (use_photo=False): is_photo={is_photo}, step={step}", flush=True)
    try:
        if is_photo:
            await query.edit_message_caption(caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        else:
            await query.edit_message_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        print(f"🟢 _show_wall_angle (use_photo=False): edit OK", flush=True)
    except Exception as e:
        err = str(e).lower()
        print(f"⚠️ _show_wall_angle edit failed: {e}", flush=True)
        if "message is not modified" in err:
            # Ничего не поменялось — но кнопки могут быть привязаны к другому сообщению.
            # Проверим, есть ли reply_markup
            return
        # Все остальные ошибки — пересоздаём сообщение
        chat_id = query.message.chat_id
        # Если есть фото — переслать с фото, иначе текст
        if image and _image_path(image) and os.path.exists(_image_path(image)):
            try:
                with open(_image_path(image), "rb") as f:
                    await query.get_bot().send_photo(
                        chat_id=chat_id, photo=f, caption=caption,
                        parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                    )
                print(f"🟢 _show_wall_angle: fallback send_photo OK", flush=True)
                return
            except Exception as e2:
                print(f"⚠️ _show_wall_angle send_photo fallback: {e2}", flush=True)
        try:
            await query.get_bot().send_message(
                chat_id=chat_id, text=caption,
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
            print(f"🟢 _show_wall_angle: fallback send_message OK", flush=True)
        except Exception as e3:
            print(f"⚠️ _show_wall_angle send_message fallback: {e3}", flush=True)


# ============================================================
# НИШИ — ПОКАЗ ЭКРАНОВ
# ============================================================

async def _show_niche_count(query, context, room_id):
    """Сколько нишей на стене?"""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_count'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = None

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data=f"wall_niche_count_1_{room_id}")],
        [InlineKeyboardButton("2", callback_data=f"wall_niche_count_2_{room_id}")],
        [InlineKeyboardButton("3", callback_data=f"wall_niche_count_3_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    caption = "🕳 *Сколько нишей на этой стене?*"
    print(f"🟠 _show_niche_count вызван, room_id={room_id}", flush=True)

    # Правильный выбор: если текущее сообщение — фото, edit_caption; иначе edit_text
    msg = query.message
    is_photo = bool(getattr(msg, "photo", None))

    try:
        if is_photo:
            await query.edit_message_caption(
                caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        else:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        print(f"🟢 _show_niche_count OK (photo={is_photo})", flush=True)
    except Exception as e:
        err = str(e).lower()
        print(f"⚠️ _show_niche_count edit failed: {e}", flush=True)
        # Удаляем старое и шлём новое
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            await query.get_bot().send_message(
                chat_id=query.message.chat_id, text=caption,
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
            print(f"🟢 _show_niche_count fallback send OK", flush=True)
        except Exception as e2:
            print(f"⚠️ _show_niche_count fallback failed: {e2}", flush=True)


async def _show_niche_width(query, context, room_id):
    """Ширина ниши."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_width'
    _save_wall_draft(context, room_id)

    count = state.get('niche_count') or 1
    current = state.get('niche_current') or 1
    context.user_data['waiting_for'] = 'wall_niche_width'

    spec_step = spec.get_niche_step('width', i=current, count=count)
    if spec_step:
        caption = (
            f"🕳 *Ниша {current} из {count}*\n\n"
            f"{spec_step.get('subtitle', '📏 Ширина ниши (СМ):')}\n\n"
            f"_Например: {spec_step.get('example', '80')}_"
        )
        image = spec_step.get('image')
    else:
        caption = f"🕳 *Ниша {current} из {count}*\n\n📏 *Ширина ниши* (СМ):\n\n_Например: 80_"
        image = "niche_width.png"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_niche_depth(query, context, room_id):
    """Глубина ниши."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_depth'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_niche_depth'

    spec_step = spec.get_niche_step('depth')
    caption = spec_step.get('title', '🕳 *Ниша — ГЛУБИНА* (СМ):')
    hint = spec_step.get('hint')
    if hint:
        caption += f"\n\n{hint}"
    image = spec_step.get('image', 'niche_depth.png')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_niche_height(query, context, room_id):
    """Высота ниши."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_height'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_niche_height'

    spec_step = spec.get_niche_step('height')
    caption = spec_step.get('title', '🕳 *Ниша — ВЫСОТА* (СМ):')
    example = spec_step.get('example')
    if example:
        caption += f"\n\n_Например: {example}_"
    image = spec_step.get('image', 'niche_height.png')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, image)


async def _show_niche_plane(query, context, room_id):
    """Ниша ровная или неровная?"""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_plane'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = None

    spec_step = spec.get_niche_step('plane')
    caption = spec_step.get('title', '🕳 *Ниша ровная или неровная по высоте?*')
    hint = spec_step.get('hint')
    if hint:
        caption += f"\n\n{hint}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_niche_plane_rect_{room_id}")],
        [InlineKeyboardButton("📏 Неровная", callback_data=f"wall_niche_plane_irr_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, None)


async def _show_niche_top_width(query, context, room_id):
    """Ширина ниши СВЕРХУ (для неровной)."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_top_width'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_niche_top_width'

    spec_step = spec.get_niche_step('top_width')
    caption = spec_step.get('title', '🕳 *Ширина СВЕРХУ* (СМ):')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, None)


async def _show_niche_top_depth(query, context, room_id):
    """Глубина ниши СВЕРХУ (для неровной)."""
    state = _get_wall_state(context)
    state['step_name'] = 'niche_top_depth'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_niche_top_depth'

    spec_step = spec.get_niche_step('top_depth')
    caption = spec_step.get('title', '🕳 *Глубина сверху* (СМ):')
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_edit(query, caption, kb, None)


# ============================================================
# СОХРАНЕНИЕ СТЕНЫ
# ============================================================


async def _wall_save_and_next(query, context, room_id, step):
    """Сохраняет текущую стену, чистит черновик, идёт к следующей."""
    state = _get_wall_state(context)
    pos = WALL_NAMES.get(step, '?')
    length = state.get('length') or 0
    angle = state.get('angle_value') or 90
    angle_method = state.get('angle_method') or '90'
    flags = state.get('flags') or {}

    note_parts = []
    if flags.get('rounded'): note_parts.append('Закругление')
    if flags.get('wavy'): note_parts.append('Разная по высоте')
    if flags.get('hidden'): note_parts.append('Скрытые коммуникации')
    note = '; '.join(note_parts) if note_parts else None

    try:
        session_id = ensure_session(room_id)
    except Exception:
        session_id = None

    start_x = start_y = end_x = end_y = None
    try:
        walls_existing = get_walls_ordered(room_id)
        walls_for_calc = list(walls_existing) + [{
            'wall_pos': pos, 'length': length, 'angle_value': angle,
        }]
        coords = calc_wall_coords(walls_for_calc)
        if coords:
            last = coords[-1]
            start_x = last.get('start_x'); start_y = last.get('start_y')
            end_x = last.get('end_x'); end_y = last.get('end_y')
    except Exception as e:
        print(f"⚠️ calc_wall_coords: {e}", flush=True)

    kwargs = {
        'label': f'Стена {pos}', 'wall_pos': pos, 'length': length,
        'unit': 'см', 'order_num': step,
        'angle_value': angle, 'angle_method': angle_method,
        'session_id': session_id,
    }
    if flags.get('rounded'): kwargs['has_rounded'] = 1
    if flags.get('wavy'): kwargs['is_wavy'] = 1
    if flags.get('hidden'):
        kwargs['has_hidden'] = 1
        kwargs['hidden_note'] = note
    if note: kwargs['note'] = note
    if start_x is not None:
        kwargs['start_x'] = start_x; kwargs['start_y'] = start_y
        kwargs['end_x'] = end_x; kwargs['end_y'] = end_y

    measure_id = add_measure(room_id, 'wall', **kwargs)

    niches = state.get('niches') or []
    if niches and measure_id:
        for n in niches:
            try:
                add_niche(
                    measure_id=measure_id, room_id=room_id,
                    width_bottom=n.get('width'),
                    width_top=n.get('width_top') or n.get('width'),
                    height=n.get('height'),
                    depth_bottom=n.get('depth'),
                    depth_top=n.get('depth_top') or n.get('depth'),
                    session_id=session_id,
                )
            except Exception as e:
                print(f"⚠️ add_niche: {e}", flush=True)

    _clear_wall_draft(room_id)
    next_step = step + 1 if step < 4 else 1
    _reset_wall_state(context, keep_step_num=next_step)

    summary = f"✅ *Стена {step} ({pos}) сохранена!*\n\n📏 Длина: {length} см\n📐 Угол: {angle}°"
    if niches:
        summary += f"\n🕳 Нишей: {len(niches)}"

    if step >= 4:
        complete_walls_round(room_id)
        await _wall_finish(query, context, room_id, summary)
        return

    state_next = _get_wall_state(context)
    state_next['step_num'] = next_step
    state_next['step_name'] = 'flags'
    _save_wall_draft(context, room_id)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"➡️ Стена {next_step}", callback_data=f"wall_round_start_{room_id}")],
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
    ])
    try:
        await query.edit_message_text(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _wall_finish(query, context, room_id, summary_prefix=''):
    """Финиш обхода стен."""
    areas = calculate_room_areas(room_id)
    text = summary_prefix + "\n\n🎉 *Все 4 стены замерены!*\n\n"
    if areas.get('walls_net') is not None:
        text += f"📊 Площадь стен: {areas['walls_net']} м²\n"
    if areas.get('floor'):
        text += f"📊 Площадь пола: {areas['floor']} м²\n"

    # Замыкание контура
    try:
        walls = get_walls_ordered(room_id)
        closure = check_closure(walls)
        if closure.get('closed'):
            text += "✅ Контур замкнут\n"
        else:
            text += f"⚠️ Контур не замкнут: разрыв {closure.get('gap_cm', 0)} см ({closure.get('gap_percent', 0)}%)\n"
    except Exception:
        pass

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
        [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
    ])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


# ============================================================


# ============================================================
# CALLBACK'И ОБХОДА СТЕН
# ============================================================

async def handle_wall_round_callback(query, context, data):
    """Обработчик всех callback'ов обхода стен.

    Возвращает True, если обработано.
    """
    # --- СТАРТ / ПРОДОЛЖЕНИЕ ---
    if data.startswith("wall_round_start_"):
        room_id = int(data.replace("wall_round_start_", ""))
        await _wall_round_start(query, context, room_id)
        return True

    # --- СБРОС ---
    if data.startswith("wall_round_reset_"):
        room_id = int(data.replace("wall_round_reset_", ""))
        walls = get_measures(room_id, category='wall')
        for w in walls:
            delete_measure(w['id'])
        try:
            db_commit("UPDATE rooms SET walls_started_at = NULL, walls_completed_at = NULL WHERE id = ?", (room_id,))
        except Exception:
            pass
        _clear_wall_draft(room_id)
        _reset_wall_state(context)
        state = _get_wall_state(context)
        state['step_num'] = 1
        state['step_name'] = 'flags'
        await _show_wall_step(query, context, room_id, 1, phase='flags', use_photo=True)
        return True

    # --- ФЛАГИ (галочки) ---
    if data.startswith("wall_round_flag_"):
        parts = data.replace("wall_round_flag_", "").rsplit("_", 1)
        flag = parts[0]
        room_id = int(parts[1])
        state = _get_wall_state(context)
        flags = state.get('flags') or dict(DEFAULT_FLAGS)
        flags[flag] = not flags.get(flag, False)
        state['flags'] = flags
        _save_wall_draft(context, room_id)
        step = state.get('step_num') or 1
        # use_photo=False — обновление галочки, без мигания
        await _show_wall_step(query, context, room_id, step, phase='flags', use_photo=False)
        return True

    # --- ФЛАГИ → ДАЛЬШЕ ---
    if data.startswith("wall_round_flags_done_"):
        room_id = int(data.replace("wall_round_flags_done_", ""))
        state = _get_wall_state(context)
        state['step_name'] = 'plane'
        _save_wall_draft(context, room_id)
        await _show_wall_plane(query, context, room_id)
        return True

    # --- ПРОПУСК СТЕНЫ ---
    if data.startswith("wall_round_skip_"):
        room_id = int(data.replace("wall_round_skip_", ""))
        state = _get_wall_state(context)
        step = state.get('step_num') or 1
        if step >= 4:
            complete_walls_round(room_id)
            _clear_wall_draft(room_id)
            _reset_wall_state(context)
            await _wall_finish(query, context, room_id, "⏭ Стена пропущена")
            return True
        # Сбрасываем state и идём к следующей стене
        _reset_wall_state(context)
        state = _get_wall_state(context)
        state['step_num'] = step + 1
        state['step_name'] = 'flags'
        _save_wall_draft(context, room_id)
        await _show_wall_step(query, context, room_id, step + 1, phase='flags')
        return True

    # --- ПЛОСКОСТЬ ---
    if data.startswith("wall_round_plane_straight_"):
        room_id = int(data.replace("wall_round_plane_straight_", ""))
        context.user_data['wall_room_id'] = room_id
        state = _get_wall_state(context)
        state['plane'] = 'straight'
        state['step_name'] = 'length'
        _save_wall_draft(context, room_id)
        await _show_wall_length(query, context, room_id, state.get('step_num') or 1)
        return True

    if data.startswith("wall_round_plane_wavy_"):
        room_id = int(data.replace("wall_round_plane_wavy_", ""))
        context.user_data['wall_room_id'] = room_id
        state = _get_wall_state(context)
        state['plane'] = 'wavy'
        state['step_name'] = 'plane_wavy'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        step = state.get('step_num') or 1
        caption = (
            f"🧱 *Стена {step}*\n\n"
            f"📏 *Замер в 3 точках:*\n\n"
            f"Введи НИЗ стены (СМ):"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ В комнату", callback_data=f"room_{room_id}")],
        ])
        # Фото для этого шага нет (нужна специальная схема «вид на стену»)
        # Просто текстовое сообщение — БЕЗ вводящего в заблуждение PNG
        try:
            await query.edit_message_text(
                caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            try:
                await query.get_bot().send_message(
                    chat_id=query.message.chat_id, text=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            except Exception as e:
                print(f"⚠️ plane_wavy send: {e}", flush=True)
        return True

    # --- ПРОЁМЫ ПРИ ОБХОДЕ ---
    if data.startswith("wall_round_open_win_"):
        room_id = int(data.replace("wall_round_open_win_", ""))
        return await _wall_round_open_start(query, context, room_id, 'window')

    if data.startswith("wall_round_open_door_"):
        room_id = int(data.replace("wall_round_open_door_", ""))
        return await _wall_round_open_start(query, context, room_id, 'door_interior')

    if data.startswith("wall_round_open_vent_"):
        room_id = int(data.replace("wall_round_open_vent_", ""))
        return await _wall_round_open_start(query, context, room_id, 'vent')

    if data.startswith("wall_round_openings_done_"):
        room_id = int(data.replace("wall_round_openings_done_", ""))
        state = _get_wall_state(context)
        state['step_name'] = 'angle'
        _save_wall_draft(context, room_id)
        # Первый вход на шаг угла — с фото
        await _show_wall_angle(query, context, room_id, state.get('step_num') or 1, use_photo=True)
        return True

    # --- УГОЛ ---
    if data.startswith("wall_round_angle_90_"):
        room_id = int(data.replace("wall_round_angle_90_", ""))
        state = _get_wall_state(context)
        print(f"🔵 wall_round_angle_90_: room_id={room_id}, state['step_num']={state.get('step_num')!r}", flush=True)
        state['angle_value'] = 90
        state['angle_method'] = '90'
        state['step_name'] = 'angle_done'
        _save_wall_draft(context, room_id)
        await _after_angle(query, context, room_id)
        return True

    if data.startswith("wall_round_angle_60_"):
        room_id = int(data.replace("wall_round_angle_60_", ""))
        state = _get_wall_state(context)
        state['angle_method'] = '60'
        state['step_name'] = 'angle'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_angle_val'
        try:
            await query.edit_message_text(
                "📏 *Диагональ (60-80-100)*\n_Идеал: 100 см_\n\nВведи в СМ:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("wall_round_angle_100_"):
        room_id = int(data.replace("wall_round_angle_100_", ""))
        state = _get_wall_state(context)
        state['angle_method'] = '100'
        state['step_name'] = 'angle'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_angle_val'
        try:
            await query.edit_message_text(
                "📏 *Диагональ (100-100)*\n_Идеал: 141 см_\n\nВведи в СМ:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("wall_round_angle_deg_"):
        room_id = int(data.replace("wall_round_angle_deg_", ""))
        state = _get_wall_state(context)
        state['angle_method'] = 'deg'
        state['step_name'] = 'angle'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_angle_val'
        try:
            await query.edit_message_text(
                "📐 *Угол в градусах*\n\nВведи (например 93):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    # --- НИШИ ---
    if data.startswith("wall_niche_count_"):
        parts = data.replace("wall_niche_count_", "").rsplit("_", 1)
        count = int(parts[0])
        room_id = int(parts[1])
        state = _get_wall_state(context)
        state['niche_count'] = count
        state['niche_current'] = 1
        state['niches'] = []
        state['niche_temp'] = {}
        _save_wall_draft(context, room_id)
        await _show_niche_width(query, context, room_id)
        return True

    if data.startswith("wall_niche_plane_rect_"):
        room_id = int(data.replace("wall_niche_plane_rect_", ""))
        state = _get_wall_state(context)
        temp = state.get('niche_temp') or {}
        temp['width_top'] = temp.get('width')
        temp['depth_top'] = temp.get('depth')
        niches = state.get('niches') or []
        niches.append(temp)
        state['niches'] = niches
        state['niche_temp'] = {}
        _save_wall_draft(context, room_id)

        total = state.get('niche_count') or 1
        current = state.get('niche_current') or 1
        if current < total:
            state['niche_current'] = current + 1
            _save_wall_draft(context, room_id)
            await _show_niche_width(query, context, room_id)
            return True
        # Все ниши обработаны — идём к следующему шагу в очереди
        print(f"🔷 wall_niche_plane_rect: все ниши собраны ({len(niches)}), → _after_angle", flush=True)
        await _after_angle(query, context, room_id)
        return True

    if data.startswith("wall_niche_plane_irr_"):
        room_id = int(data.replace("wall_niche_plane_irr_", ""))
        await _show_niche_top_width(query, context, room_id)
        return True

    return False


# ============================================================
# СТАРТ ОБХОДА С ВОССТАНОВЛЕНИЕМ
# ============================================================

async def _wall_round_start(query, context, room_id):
    """Главный вход в обход стен. Восстанавливает прогресс из БД."""
    progress = get_walls_progress(room_id)
    if progress['walls_count'] >= 4:
        await query.edit_message_text(
            "✅ Все 4 стены уже замерены.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Заново", callback_data=f"wall_round_reset_{room_id}")],
                [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
                [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
            ])
        )
        return

    start_walls_round(room_id)
    next_step = progress['current_step']

    # Пытаемся восстановить черновик
    step_name = _load_wall_draft(context, room_id)
    print(f"🔍 _wall_round_start: room_id={room_id}, next_step={next_step}, step_name={step_name!r}", flush=True)

    state = _get_wall_state(context)
    # Если черновика нет — начинаем с начала
    if step_name is None:
        state['step_num'] = next_step
        state['step_name'] = 'flags'
        _save_wall_draft(context, room_id)
        # Первый вход — фото
        await _show_wall_step(query, context, room_id, next_step, phase='flags', use_photo=True)
        return

    # Восстанавливаем step_num из черновика
    step_num = state.get('step_num') or next_step
    context.user_data['wall_room_id'] = room_id

    # === ОБРАБОТКА ВСЕХ step_name ===
    if step_name == 'flags':
        # Восстановление — показываем фото как при первом входе
        await _show_wall_step(query, context, room_id, step_num, phase='flags', use_photo=True)
        return

    if step_name == 'plane':
        await _show_wall_plane(query, context, room_id)
        return

    if step_name == 'plane_wavy':
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            f"🧱 *Стена {step_num}*\n\n"
            f"📏 *Продолжаем замер в 3 точках:*\n\n"
            f"Введи НИЗ стены (СМ):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if step_name == 'length':
        await _show_wall_length(query, context, room_id, step_num)
        return

    if step_name == 'openings':
        await _show_wall_openings(query, context, room_id, step_num)
        return

    if step_name == 'angle':
        # Восстановление — edit_caption (без пересоздания)
        await _show_wall_angle(query, context, room_id, step_num, use_photo=False)
        return

    if step_name == 'angle_done':
        await _after_angle(query, context, room_id)
        return

    # === ВОТ ОН, ТОТ САМЫЙ БАГ — niche_width !!! ===
    if step_name == 'niche_width':
        await _show_niche_width(query, context, room_id)
        return

    if step_name == 'niche_depth':
        await _show_niche_depth(query, context, room_id)
        return

    if step_name == 'niche_height':
        await _show_niche_height(query, context, room_id)
        return

    if step_name == 'niche_plane':
        await _show_niche_plane(query, context, room_id)
        return

    if step_name == 'niche_top_width':
        await _show_niche_top_width(query, context, room_id)
        return

    if step_name == 'niche_top_depth':
        await _show_niche_top_depth(query, context, room_id)
        return

    if step_name == 'niche_count':
        await _show_niche_count(query, context, room_id)
        return

    # Fallback — галочки (первый раз заходим)
    state['step_num'] = step_num
    state['step_name'] = 'flags'
    _save_wall_draft(context, room_id)
    await _show_wall_step(query, context, room_id, step_num, phase='flags', use_photo=True)


# ============================================================
# ХЕЛПЕРЫ ОБХОДА
# ============================================================

async def _after_angle(query, context, room_id):
    """После угла — обрабатываем remaining_steps (ниши/rounded/wavy/hidden).

    ЧИСТАЯ ЛОГИКА:
    - remaining_steps is None  → первый заход. Читаем флаги, чистим их, ставим очередь.
    - remaining_steps == []    → все обработано, сохраняем стену.
    - remaining_steps == [...] → берём [0], идём по очереди.
    """
    state = _get_wall_state(context)
    remaining = state.get('remaining_steps')

    # --- ФАЗА 1: первый заход после угла ---
    if remaining is None:
        flags_queue = _wall_flags_list(context)
        # ВАЖНО: чистим флаги — иначе они снова попадут в очередь
        state['flags'] = dict(DEFAULT_FLAGS)
        state['remaining_steps'] = flags_queue
        _save_wall_draft(context, room_id)
        remaining = flags_queue
        print(f"🔷 _after_angle: первый заход, очередь={remaining}", flush=True)

    # --- ФАЗА 2: очередь пуста → сохраняем стену ---
    if not remaining:
        step_num = state.get('step_num') or 1
        print(f"🔷 _after_angle: очередь пуста. state['step_num']={state.get('step_num')!r}, ИТОГ step_num={step_num} → _wall_save_and_next", flush=True)
        await _wall_save_and_next(query, context, room_id, step_num)
        return

    # --- ФАЗА 3: берём первый элемент очереди ---
    first = remaining[0]
    state['remaining_steps'] = remaining[1:]
    _save_wall_draft(context, room_id)
    print(f"🔷 _after_angle: берём {first!r}, осталось {state['remaining_steps']}", flush=True)

    if first == 'niche':
        await _show_niche_count(query, context, room_id)
        return

    if first == 'rounded':
        state['step_name'] = 'rounded'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_rounded_radius'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "🔄 *Закругление*\n\n📏 Радиус (СМ):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if first == 'wavy':
        # wavy — если УЖЕ прошли через 3 точки — пропускаем, идём дальше
        if state.get('plane') == 'wavy':
            state['remaining_steps'] = remaining[1:] if len(remaining) > 1 else []
            _save_wall_draft(context, room_id)
            await _after_angle(query, context, room_id)
            return
        # Иначе — первый раз, показываем 3 точки
        state['plane'] = 'wavy'
        state['step_name'] = 'plane_wavy'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "📐 *Разная по высоте*\n\n📏 Введи НИЗ стены (СМ):",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if first == 'hidden':
        state['step_name'] = 'hidden'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_hidden_note'
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(
            "🔧 *Скрытые коммуникации*\n\nОпиши что и где:",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Неизвестный шаг — сохраняем
    step_num = state.get('step_num') or 1
    await _wall_save_and_next(query, context, room_id, step_num)


async def _after_niches(query, context, room_id):
    """После нишей — обрабатываем следующий remaining_step или сохраняем."""
    # Просто делегируем в _after_angle, но remaining_steps уже обрезан
    await _after_angle(query, context, room_id)


async def _wall_round_open_start(query, context, room_id, opening_type):
    """Старт добавления проёма при обходе."""
    state = _get_wall_state(context)
    step = state.get('step_num') or 1
    pos = WALL_NAMES.get(step, 'напротив')
    context.user_data['wall_round_opening_type'] = opening_type
    context.user_data['wall_round_opening_wall'] = pos

    if opening_type == 'vent':
        # Вентиляция — сразу высота от пола
        context.user_data['waiting_for'] = 'wall_round_opening_height'
        try:
            await query.edit_message_text(
                "💨 *Вентиляция*\n\n📏 Высота от пола (СМ):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"wall_round_openings_done_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    # Окно/Дверь — сначала ширина
    context.user_data['waiting_for'] = 'wall_round_opening_width'
    label = '🪟 Окно' if opening_type == 'window' else '🚪 Дверь'
    try:
        await query.edit_message_text(
            f"{label}\n\n📏 Ширина (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"wall_round_openings_done_{room_id}")],
            ])
        )
    except Exception:
        pass
    return True


async def _handle_wall_round_input(update, context, step):
    """Ввод при обходе стен."""
    room_id = context.user_data.get('wall_room_id')
    if not room_id:
        # Страховка: восстановить из wall_drafts
        try:
            draft = fetchone("SELECT room_id FROM wall_drafts ORDER BY updated_at DESC LIMIT 1")
            if draft:
                room_id = draft["room_id"]
                context.user_data["wall_room_id"] = room_id
                print(f"⚠️ wall_room_id восстановлен: {room_id}", flush=True)
        except Exception as e:
            print(f"⚠️ restore wall_room_id: {e}", flush=True)
    if not room_id:
        await update.message.reply_text("❌ Потерялась комната. Начни замер заново.")
        context.user_data["waiting_for"] = None
        return
    state = _get_wall_state(context)
    text_val = (update.message.text or '').strip().replace(',', '.')

    if step == 'wall_round_length':
        try:
            length_cm = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число")
            return
        if length_cm <= 0 or length_cm > 5000:
            await update.message.reply_text("❌ Длина от 1 до 5000 см")
            return
        state['length'] = length_cm
        state['step_name'] = 'openings'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = None
        await _show_wall_openings_from_update(update, context, room_id)
        return

    if step == 'wall_round_plane_bottom':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        state['plane_bottom'] = val
        context.user_data['waiting_for'] = 'wall_round_plane_middle'
        step_num = state.get('step_num') or 1
        pos = WALL_NAMES.get(step_num, '?')
        caption = (
            f"🧱 *Стена {step_num} — {pos}*\n\n"
            f"📏 *Замер в 3 точках*\n"
            f"✅ Точка 1 (низ): *{val} см*\n\n"
            f"📍 *Точка 2 — СЕРЕДИНА стены*\n"
            f"Приложи дальномер на середине стены по высоте.\n\n"
            f"Введи результат в СМ:"
        )
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'wall_round_plane_middle':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        state['plane_middle'] = val
        context.user_data['waiting_for'] = 'wall_round_plane_top'
        step_num = state.get('step_num') or 1
        pos = WALL_NAMES.get(step_num, '?')
        bottom = state.get('plane_bottom') or 0
        caption = (
            f"🧱 *Стена {step_num} — {pos}*\n\n"
            f"📏 *Замер в 3 точках*\n"
            f"✅ Точка 1 (низ): *{bottom} см*\n"
            f"✅ Точка 2 (середина): *{val} см*\n\n"
            f"📍 *Точка 3 — ВЕРХ стены*\n"
            f"Приложи дальномер вверху стены (под потолком).\n\n"
            f"Введи результат в СМ:"
        )
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'wall_round_plane_top':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        state['plane_top'] = val
        state['plane'] = 'wavy'
        state['step_name'] = 'length'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_length'
        step_num = state.get('step_num') or 1
        pos = WALL_NAMES.get(step_num, '?')
        bottom = state.get('plane_bottom') or 0
        middle = state.get('plane_middle') or 0
        # Отклонение — насколько «кривая» стена
        avg = (bottom + middle + val) / 3
        deviation = max(bottom, middle, val) - min(bottom, middle, val)
        caption = (
            f"✅ *Замер стены завершён!*\n\n"
            f"🧱 *Стена {step_num} — {pos}*\n"
            f"• Низ: *{bottom} см*\n"
            f"• Середина: *{middle} см*\n"
            f"• Верх: *{val} см*\n\n"
            f"📊 Отклонение: *{round(deviation, 1)} см*\n"
            f"📏 Средняя высота: *{round(avg, 1)} см*\n\n"
            f"Дальше — *длина стены*."
        )
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
        # Непрерывный переход: сразу показываем экран длины
        await _show_wall_length_from_update(update, context, room_id, step_num)
        return

    if step == 'wall_round_angle_val':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        method = state.get('angle_method') or '60'
        if method == '60':
            c = (60*60 + 80*80 - val*val) / (2*60*80)
            c = max(-1, min(1, c))
            angle_deg = round(math.degrees(math.acos(c)), 1)
        elif method == '100':
            c = (100*100 + 100*100 - val*val) / (2*100*100)
            c = max(-1, min(1, c))
            angle_deg = round(math.degrees(math.acos(c)), 1)
        else:
            angle_deg = val
        state['angle_value'] = angle_deg
        state['step_name'] = 'angle_done'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = None
        await _after_angle_from_update(update, context, room_id)
        return

    if step == 'wall_niche_width':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['width'] = round(val, 2)
        state['niche_temp'] = temp
        state['step_name'] = 'niche_depth'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_niche_depth'
        await _show_niche_depth_from_update(update, context, room_id)
        return

    if step == 'wall_niche_depth':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['depth'] = round(val, 2)
        state['niche_temp'] = temp
        state['step_name'] = 'niche_height'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_niche_height'
        await _show_niche_height_from_update(update, context, room_id)
        return

    if step == 'wall_niche_height':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['height'] = round(val, 2)
        state['niche_temp'] = temp
        state['step_name'] = 'niche_plane'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = None
        await _show_niche_plane_from_update(update, context, room_id)
        return

    if step == 'wall_niche_top_width':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['width_top'] = round(val, 2)
        state['niche_temp'] = temp
        state['step_name'] = 'niche_top_depth'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_niche_top_depth'
        await _show_niche_top_depth_from_update(update, context, room_id)
        return

    if step == 'wall_niche_top_depth':
        try: val = float(text_val)
        except ValueError:
            await update.message.reply_text("❌ Нужно число"); return
        temp = state.get('niche_temp') or {}
        temp['depth_top'] = round(val, 2)
        niches = state.get('niches') or []
        niches.append(temp)
        state['niches'] = niches
        state['niche_temp'] = {}
        total = state.get('niche_count') or 1
        current = state.get('niche_current') or 1
        if current < total:
            state['niche_current'] = current + 1
            state['step_name'] = 'niche_width'
            _save_wall_draft(context, room_id)
            context.user_data['waiting_for'] = 'wall_niche_width'
            await update.message.reply_text(
                f"✅ Ниша {current}\n\n🕳 *Ниша {current+1}* — Ширина (СМ):",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        state['step_name'] = 'angle_done'
        _save_wall_draft(context, room_id)
        await _after_angle_from_update(update, context, room_id)
        return

    if step in ('wall_rounded_radius', 'wall_wavy_note', 'wall_hidden_note'):
        state['flags'] = state.get('flags') or dict(DEFAULT_FLAGS)
        if step == 'wall_rounded_radius':
            state['flags']['rounded'] = True
        elif step == 'wall_wavy_note':
            state['flags']['wavy'] = True
        else:
            state['flags']['hidden'] = True
        state['step_name'] = 'angle_done'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = None
        await _after_angle_from_update(update, context, room_id)
        return

    if step in ('wall_round_opening_width', 'wall_round_opening_height'):
        await _handle_wall_round_opening_input(update, context, step)
        return

    context.user_data['waiting_for'] = None
    await update.message.reply_text("⚠️ Неизвестный шаг.")


async def _after_angle_from_update(update, context, room_id):
    """После угла (через update) — остаток шагов или сохранение.

    ЧИСТАЯ ЛОГИКА: см. _after_angle.
    """
    state = _get_wall_state(context)
    remaining = state.get('remaining_steps')

    # --- ФАЗА 1: первый заход ---
    if remaining is None:
        flags_queue = _wall_flags_list(context)
        state['flags'] = dict(DEFAULT_FLAGS)
        state['remaining_steps'] = flags_queue
        _save_wall_draft(context, room_id)
        remaining = flags_queue
        print(f"🔷 _after_angle_from_update: первый заход, очередь={remaining}", flush=True)

    # --- ФАЗА 2: пусто → сохраняем ---
    if not remaining:
        print(f"🔷 _after_angle_from_update: очередь пуста → сохранение", flush=True)
        await _wall_save_and_next_from_update(update, context, room_id, state.get('step_num') or 1)
        return

    # --- ФАЗА 3: берём [0] ---
    first = remaining[0]
    state['remaining_steps'] = remaining[1:]
    _save_wall_draft(context, room_id)
    print(f"🔷 _after_angle_from_update: берём {first!r}, осталось {state['remaining_steps']}", flush=True)

    if first == 'niche':
        state['step_name'] = 'niche_count'
        _save_wall_draft(context, room_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data=f"wall_niche_count_1_{room_id}")],
            [InlineKeyboardButton("2", callback_data=f"wall_niche_count_2_{room_id}")],
            [InlineKeyboardButton("3", callback_data=f"wall_niche_count_3_{room_id}")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
        ])
        await update.message.reply_text("🕳 *Сколько нишей на этой стене?*", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return
    if first == 'rounded':
        state['step_name'] = 'rounded'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_rounded_radius'
        await update.message.reply_text("🔄 *Закругление*\n\n📏 Радиус (СМ):", parse_mode=ParseMode.MARKDOWN)
        return
    if first == 'wavy':
        # Уже прошли через 3 точки — пропускаем
        if state.get('plane') == 'wavy':
            state['remaining_steps'] = remaining[1:] if len(remaining) > 1 else []
            _save_wall_draft(context, room_id)
            await _after_angle_from_update(update, context, room_id)
            return
        context.user_data['wall_room_id'] = room_id
        state['plane'] = 'wavy'
        state['step_name'] = 'plane_wavy'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_round_plane_bottom'
        await update.message.reply_text("📐 *Разная по высоте*\n\n📏 Введи НИЗ стены (СМ):", parse_mode=ParseMode.MARKDOWN)
        return
    if first == 'hidden':
        state['step_name'] = 'hidden'
        _save_wall_draft(context, room_id)
        context.user_data['waiting_for'] = 'wall_hidden_note'
        await update.message.reply_text("🔧 *Скрытые коммуникации*\n\nОпиши что и где:", parse_mode=ParseMode.MARKDOWN)
        return
    await _wall_save_and_next_from_update(update, context, room_id, state.get('step_num') or 1)


async def _wall_save_and_next_from_update(update, context, room_id, step):
    """Сохранение стены (версия для update.message)."""
    state = _get_wall_state(context)
    pos = WALL_NAMES.get(step, '?')
    length = state.get('length') or 0
    angle = state.get('angle_value') or 90
    angle_method = state.get('angle_method') or '90'
    flags = state.get('flags') or {}

    note_parts = []
    if flags.get('rounded'): note_parts.append('Закругление')
    if flags.get('wavy'): note_parts.append('Разная по высоте')
    if flags.get('hidden'): note_parts.append('Скрытые коммуникации')
    note = '; '.join(note_parts) if note_parts else None

    try: session_id = ensure_session(room_id)
    except Exception: session_id = None

    kwargs = {
        'label': f'Стена {pos}', 'wall_pos': pos, 'length': length,
        'unit': 'см', 'order_num': step,
        'angle_value': angle, 'angle_method': angle_method,
        'session_id': session_id,
    }
    if flags.get('rounded'): kwargs['has_rounded'] = 1
    if flags.get('wavy'): kwargs['is_wavy'] = 1
    if flags.get('hidden'):
        kwargs['has_hidden'] = 1
        kwargs['hidden_note'] = note
    if note: kwargs['note'] = note

    measure_id = add_measure(room_id, 'wall', **kwargs)

    niches = state.get('niches') or []
    if niches and measure_id:
        for n in niches:
            try:
                add_niche(
                    measure_id=measure_id, room_id=room_id,
                    width_bottom=n.get('width'),
                    width_top=n.get('width_top') or n.get('width'),
                    height=n.get('height'),
                    depth_bottom=n.get('depth'),
                    depth_top=n.get('depth_top') or n.get('depth'),
                    session_id=session_id,
                )
            except Exception as e:
                print(f"⚠️ add_niche: {e}", flush=True)

    _clear_wall_draft(room_id)
    next_step = step + 1 if step < 4 else 1
    _reset_wall_state(context, keep_step_num=next_step)

    summary = f"✅ *Стена {step} ({pos}) сохранена!*\n\n📏 Длина: {length} см\n📐 Угол: {angle}°"
    if niches: summary += f"\n🕳 Нишей: {len(niches)}"

    if step >= 4:
        complete_walls_round(room_id)
        areas = calculate_room_areas(room_id)
        text = summary + "\n\n🎉 *Все 4 стены замерены!*\n\n"
        if areas.get('walls_net') is not None:
            text += f"📊 Площадь стен: {areas['walls_net']} м²\n"
        if areas.get('floor'):
            text += f"📊 Площадь пола: {areas['floor']} м²\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
            [InlineKeyboardButton("📦 К комнате", callback_data=f"room_{room_id}")],
        ])
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return

    next_step = step + 1
    state_next = _get_wall_state(context)
    state_next['step_num'] = next_step
    state_next['step_name'] = 'flags'
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"➡️ Стена {next_step}", callback_data=f"wall_round_start_{room_id}")],
        [InlineKeyboardButton("📐 К размерам", callback_data=f"room_measures_{room_id}")],
    ])
    await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_wall_openings_from_update(update, context, room_id):
    """Экран проёмов через update.message."""
    state = _get_wall_state(context)
    step = state.get('step_num') or 1
    pos = WALL_NAMES.get(step, '?')
    length_cm = state.get('length') or 0
    openings = get_openings_by_wall(room_id, pos)
    text = f"🧱 *Стена {step} — {pos}*\n📏 Длина: *{length_cm} см*\n\n"
    if openings:
        text += f"🚪 *Проёмы ({len(openings)}):*\n"
        for o in openings:
            text += f"  • {format_opening(o)}\n"
    else:
        text += "🚪 *Есть ли на этой стене проёмы?*"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪟 Окно", callback_data=f"wall_round_open_win_{room_id}"),
         InlineKeyboardButton("🚪 Дверь", callback_data=f"wall_round_open_door_{room_id}")],
        [InlineKeyboardButton("💨 Вентиляция", callback_data=f"wall_round_open_vent_{room_id}")],
        [InlineKeyboardButton("✅ Готово", callback_data=f"wall_round_openings_done_{room_id}")],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_niche_depth_from_update(update, context, room_id):
    spec_step = spec.get_niche_step('depth')
    caption = spec_step.get('title', '🕳 *Ниша — ГЛУБИНА* (СМ):')
    if spec_step.get('hint'):
        caption += f"\n\n{spec_step['hint']}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_reply(update.message, caption, kb, spec_step.get('image', 'niche_depth.png'))


async def _show_niche_height_from_update(update, context, room_id):
    spec_step = spec.get_niche_step('height')
    caption = spec_step.get('title', '🕳 *Ниша — ВЫСОТА* (СМ):')
    if spec_step.get('example'):
        caption += f"\n\n_Например: {spec_step['example']}_"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await _send_png_or_reply(update.message, caption, kb, spec_step.get('image', 'niche_height.png'))


async def _show_niche_plane_from_update(update, context, room_id):
    spec_step = spec.get_niche_step('plane')
    caption = spec_step.get('title', '🕳 *Ниша ровная или неровная по высоте?*')
    if spec_step.get('hint'):
        caption += f"\n\n{spec_step['hint']}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ровная", callback_data=f"wall_niche_plane_rect_{room_id}")],
        [InlineKeyboardButton("📏 Неровная", callback_data=f"wall_niche_plane_irr_{room_id}")],
        [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_{room_id}")],
    ])
    await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_niche_top_width_from_update(update, context, room_id):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await update.message.reply_text("🕳 *Ширина СВЕРХУ* (СМ):", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_niche_top_depth_from_update(update, context, room_id):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад в комнату", callback_data=f"room_{room_id}")],
    ])
    await update.message.reply_text("🕳 *Глубина сверху* (СМ):", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def _show_wall_length_from_update(update, context, room_id, step):
    """Экран длины стены через update.message (после 3 точек)."""
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = 'length'
    _save_wall_draft(context, room_id)
    context.user_data['waiting_for'] = 'wall_round_length'

    pos = WALL_NAMES.get(step, '?')
    spec_step = spec.get_wall_step('length', n=step, pos=pos)
    if spec_step:
        caption = f"{spec_step.get('title', '')}\n\n{spec_step.get('subtitle', '')}"
        if spec_step.get('hint'):
            caption += f"\n\n{spec_step['hint']}"
        if spec_step.get('prompt'):
            caption += f"\n\n{spec_step['prompt']}"
        image = spec_step.get('image')
    else:
        caption = (
            f"🧱 *Стена {step} — {pos}*\n\n"
            f"📏 *Длина стены* (СМ):\n\n"
            f"⚠️ *ВАЖНО:* дальномер в режиме «от ЗАДНЕЙ СТЕНКИ».\n\n"
            f"Напиши число и отправь."
        )
        image = f"wall_scheme_s{step}_length.png"

    await _send_png_or_reply(update.message, caption, None, image)


async def _handle_wall_round_opening_input(update, context, step):
    """Ввод размеров проёма при обходе."""
    room_id = context.user_data.get('wall_room_id')
    otype = context.user_data.get('wall_round_opening_type') or 'window'
    wall_pos = context.user_data.get('wall_round_opening_wall') or 'напротив'
    text_val = (update.message.text or '').strip().replace(',', '.')
    try: val = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Нужно число")
        return

    if step == 'wall_round_opening_width':
        context.user_data['wall_round_opening_width'] = val
        context.user_data['waiting_for'] = 'wall_round_opening_height'
        await update.message.reply_text("📏 *Высота проёма* (СМ):", parse_mode=ParseMode.MARKDOWN)
        return

    if step == 'wall_round_opening_height':
        if otype == 'vent':
            final_width, final_height, final_sill = 100, 100, val
        else:
            final_width = context.user_data.get('wall_round_opening_width') or 0
            final_height, final_sill = val, None
        try: session_id = ensure_session(room_id)
        except Exception: session_id = None
        add_opening(
            room_id=room_id, opening_type=otype, wall_pos=wall_pos,
            width=final_width, height=final_height, sill_height=final_sill,
            session_id=session_id,
            created_by=update.effective_user.id if update.effective_user else None,
        )
        for k in ['wall_round_opening_type', 'wall_round_opening_width',
                  'wall_round_opening_height', 'wall_round_opening_wall']:
            context.user_data[k] = None
        state = _get_wall_state(context)
        step_num = state.get('step_num') or 1
        openings = get_openings_by_wall(room_id, wall_pos)
        length_cm = state.get('length') or 0
        text = f"✅ *Проём добавлен!*\n\n🧱 Стена {step_num}\n📏 Длина: {length_cm} см\n\n🚪 *Проёмы ({len(openings)}):*\n"
        for o in openings:
            text += f"  • {format_opening(o)}\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🪟 Окно", callback_data=f"wall_round_open_win_{room_id}"),
             InlineKeyboardButton("🚪 Дверь", callback_data=f"wall_round_open_door_{room_id}")],
            [InlineKeyboardButton("💨 Вентиляция", callback_data=f"wall_round_open_vent_{room_id}")],
            [InlineKeyboardButton("✅ Готово", callback_data=f"wall_round_openings_done_{room_id}")],
        ])
        context.user_data['waiting_for'] = None
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return


# ============================================================
# КОММУНИКАЦИИ — CALLBACK'И
# ============================================================

async def handle_comm_callback(query, context, data):
    """Обработчик callback'ов коммуникаций. Возвращает True если обработано."""
    if data.startswith("room_comms_"):
        room_id = int(data.replace("room_comms_", ""))
        await _show_comms_list(query, context, room_id)
        return True

    if data.startswith("comm_add_"):
        room_id = int(data.replace("comm_add_", ""))
        buttons = []
        for code, label, _ in COMM_TYPES:
            buttons.append([InlineKeyboardButton(label, callback_data=f"comm_type_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")])
        try:
            await query.edit_message_text(
                "🔧 *Новая коммуникация*\n\nВыбери тип:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_type_"):
        parts = data.replace("comm_type_", "").split("_", 1)
        room_id = int(parts[0])
        ctype = parts[1] if len(parts) > 1 else ''
        context.user_data['comm_room_id'] = room_id
        context.user_data['comm_type'] = ctype
        label = get_comm_type_label(ctype)
        buttons = [
            [InlineKeyboardButton("1. Напротив", callback_data=f"comm_wall_{room_id}_напротив")],
            [InlineKeyboardButton("2. Слева", callback_data=f"comm_wall_{room_id}_слева")],
            [InlineKeyboardButton("3. У входа", callback_data=f"comm_wall_{room_id}_у входа")],
            [InlineKeyboardButton("4. Справа", callback_data=f"comm_wall_{room_id}_справа")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
        ]
        try:
            await query.edit_message_text(
                f"🔧 *{label}*\n\nНа какой стене?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_wall_"):
        parts = data.replace("comm_wall_", "").split("_", 1)
        room_id = int(parts[0])
        wall = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['comm_wall'] = wall
        context.user_data['waiting_for'] = 'comm_offset_x'
        try:
            await query.edit_message_text(
                "📐 *Расстояние от угла* (СМ):\n\n_Например: 50_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_comms_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_show_"):
        comm_id = int(data.replace("comm_show_", ""))
        await _show_comm_card(query, context, comm_id)
        return True

    if data.startswith("comm_del_"):
        comm_id = int(data.replace("comm_del_", ""))
        c = get_comm(comm_id)
        room_id = c['room_id'] if c else None
        delete_comm(comm_id)
        if room_id:
            try:
                await query.edit_message_text(
                    "✅ Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К коммуникациям", callback_data=f"room_comms_{room_id}")],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("comm_edit_"):
        parts = data.replace("comm_edit_", "").split("_")
        comm_id = int(parts[0])
        field = "_".join(parts[1:])
        context.user_data['comm_edit_id'] = comm_id
        context.user_data['comm_edit_field'] = field
        context.user_data['waiting_for'] = 'comm_edit_value'
        prompts = {
            'offset_x': '📐 *Новое расстояние от угла* (СМ):',
            'offset_y': '📏 *Новая высота от пола* (СМ):',
            'diameter': '⭕ *Новый диаметр* (мм):',
            'voltage': '⚡ *Напряжение* (220 или 380):',
        }
        prompt = prompts.get(field, '✏️ Новое значение:')
        try:
            await query.edit_message_text(
                f"{prompt}\n\n_Напиши и отправь._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"comm_show_{comm_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("comm_skip_"):
        # Пропуск шагов — сохраняем как есть
        parts = data.replace("comm_skip_", "").split("_")
        # comm_skip_size_<room> / comm_skip_diam_<room> / comm_skip_depth_<room>
        try:
            room_id = int(parts[-1])
        except ValueError:
            return True
    # === ПРИВЯЗКА К ГРУППЕ ЭОМ ===
    if data.startswith("comm_group_unset_"):
        comm_id = int(data.replace("comm_group_unset_", ""))
        try:
            if core_elec:
                core_elec.unassign_point_from_group(comm_id)
        except Exception as e:
            print(f"⚠️ unassign_point_from_group: {e}", flush=True)
        await _show_comm_card(query, context, comm_id)
        return True

    if data.startswith("comm_group_set_"):
        parts = data.replace("comm_group_set_", "").rsplit("_", 1)
        comm_id = int(parts[0])
        group_id = int(parts[1])
        try:
            if core_elec:
                core_elec.assign_comm_to_group(comm_id, group_id)
        except Exception as e:
            print(f"⚠️ assign_comm_to_group: {e}", flush=True)
        await _show_comm_card(query, context, comm_id)
        return True

    if data.startswith("comm_group_"):
        comm_id = int(data.replace("comm_group_", ""))
        c = get_comm(comm_id)
        if not c:
            try:
                await query.edit_message_text("❌ Коммуникация не найдена")
            except Exception:
                pass
            return True
        _room_obj = get_room(c.get('room_id')) if c.get('room_id') else None
        _floor_id = _room_obj.get('floor_id') if _room_obj else None
        if not _floor_id:
            try:
                await query.edit_message_text(
                    "⚠️ Комната не привязана к помещению.\n\nСначала привяжи комнату к этажу через «🏠 Помещения».",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")],
                    ])
                )
            except Exception:
                pass
            return True
        try:
            groups = core_elec.get_groups_by_floor(_floor_id) if core_elec else []
        except Exception as e:
            print(f"⚠️ get_groups_by_floor: {e}", flush=True)
            groups = []
        if not groups:
            try:
                await query.edit_message_text(
                    "⚠️ На этом этаже пока нет групп ЭОМ.\n\nСоздай группу через «⚡ Группы этажа».",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")],
                    ])
                )
            except Exception:
                pass
            return True
        label = get_comm_type_label(c.get('comm_type'))
        buttons = []
        for g in groups:
            g_name = (g.get('name') or f"#{g['id']}")[:30]
            w = int(g.get('load_watt') or 0)
            buttons.append([InlineKeyboardButton(
                f"⚡ {g_name} · {w}Вт",
                callback_data=f"comm_group_set_{comm_id}_{g['id']}"
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"comm_show_{comm_id}")])
        try:
            await query.edit_message_text(
                f"📋 *Привязка к группе этажа*\n\n🔧 {label}\n🧱 Стена: {c.get('wall') or '?'}\n\nВыбери группу:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

        await _comm_save_from_context(query, context, room_id)
        return True

    return False


async def _show_comms_list(query, context, room_id):
    """Список коммуникаций комнаты."""
    comms = get_comms(room_id)
    room = get_room(room_id)
    room_name = room['name'] if room else '?'
    text = f"🔧 *Коммуникации в «{room_name}»*\n\n"
    if not comms:
        text += "_Пока ничего не добавлено._\n\nДобавь воду, канализацию, электрику, газ, вентиляцию."
    else:
        text += f"Найдено: {len(comms)}\n\n"
        for i, c in enumerate(comms, 1):
            text += f"{i}. {format_comm(c)}\n"
    buttons = []
    for c in comms:
        label = get_comm_type_label(c.get('comm_type'))
        wall = c.get('wall') or '?'
        buttons.append([InlineKeyboardButton(f"{label} ({wall})", callback_data=f"comm_show_{c['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить", callback_data=f"comm_add_{room_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass


async def _show_comm_card(query, context, comm_id):
    """Карточка коммуникации."""
    c = get_comm(comm_id)
    if not c:
        try:
            await query.edit_message_text("❌ Не найдено")
        except Exception:
            pass
        return
    label = get_comm_type_label(c.get('comm_type'))
    text = f"🔧 *Коммуникация #{comm_id}*\n\n{label}\n"
    text += f"🧱 Стена: {c.get('wall') or '?'}\n"
    if c.get('offset_x') is not None:
        text += f"📐 От угла: {c['offset_x']} см\n"
    if c.get('offset_y') is not None:
        text += f"📏 От пола: {c['offset_y']} см\n"
    if c.get('diameter'):
        text += f"⭕ Диаметр: {c['diameter']} мм\n"
    if c.get('voltage'):
        text += f"⚡ Напряжение: {c['voltage']} В\n"
    if c.get('size'):
        text += f"📦 Размер: {c['size']} см\n"
    buttons = [
        [InlineKeyboardButton("✏️ От угла", callback_data=f"comm_edit_{comm_id}_offset_x"),
         InlineKeyboardButton("✏️ От пола", callback_data=f"comm_edit_{comm_id}_offset_y")],
    ]
    ctype = c.get('comm_type')
    if ctype == 'elec_panel':
        buttons.append([InlineKeyboardButton("✏️ Размер щита", callback_data=f"comm_edit_{comm_id}_size")])
    elif ctype in ('water_cold', 'water_hot', 'sewer', 'heating', 'gas', 'drain', 'vent'):
        buttons.append([InlineKeyboardButton("✏️ Диаметр", callback_data=f"comm_edit_{comm_id}_diameter")])
    # === ПРИВЯЗКА К ГРУППЕ ЭОМ ===
    _room_obj = get_room(c.get('room_id')) if c.get('room_id') else None
    _floor_id = _room_obj.get('floor_id') if _room_obj else None
    if _floor_id and ctype in ('elec_socket', 'elec_switch', 'elec_panel', 'elec_cable'):
        _cur_gid = c.get('group_id')
        if _cur_gid:
            try:
                _g = core_elec.get_group(_cur_gid) if core_elec else None
                _g_name = (_g.get('name') if _g else f"#{_cur_gid}")
            except Exception:
                _g_name = f"#{_cur_gid}"
            buttons.append([InlineKeyboardButton(f"📋 Группа: {_g_name[:25]}", callback_data=f"comm_group_{comm_id}")])
            buttons.append([InlineKeyboardButton("❌ Отвязать от группы", callback_data=f"comm_group_unset_{comm_id}")])
        else:
            buttons.append([InlineKeyboardButton("📋 → Привязать к группе", callback_data=f"comm_group_{comm_id}")])
    buttons.append([InlineKeyboardButton("🗑 Удалить", callback_data=f"comm_del_{comm_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К коммуникациям", callback_data=f"room_comms_{c['room_id']}")])
    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass


async def _comm_save_from_context(query, context, room_id):
    """Сохраняет коммуникацию из context.user_data."""
    ctype = context.user_data.get('comm_type')
    wall = context.user_data.get('comm_wall')
    offset_x = context.user_data.get('comm_offset_x')
    offset_y = context.user_data.get('comm_offset_y')
    if not all([room_id, ctype, wall]):
        try:
            await query.edit_message_text("❌ Потерялись данные")
        except Exception:
            pass
        return
    try:
        add_comm(room_id=room_id, comm_type=ctype, wall=wall,
                 offset_x=offset_x, offset_y=offset_y)
    except Exception as e:
        print(f"⚠️ add_comm: {e}", flush=True)
        return
    for k in ['comm_room_id', 'comm_type', 'comm_wall', 'comm_offset_x',
              'comm_offset_y', 'comm_diameter', 'comm_voltage', 'comm_size',
              'comm_size_w', 'comm_size_h', 'comm_size_d', 'waiting_for']:
        context.user_data[k] = None
    label = get_comm_type_label(ctype)
    text = f"✅ *{label}* добавлена!\n\n🧱 {wall}\n"
    if offset_x is not None:
        text += f"📐 От угла: {offset_x} см\n"
    if offset_y is not None:
        text += f"📏 От пола: {offset_y} см\n"
    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"comm_add_{room_id}")],
                [InlineKeyboardButton("✅ К списку", callback_data=f"room_comms_{room_id}")],
            ])
        )
    except Exception:
        pass


# ============================================================
# ПРОЁМЫ (отдельные) — CALLBACK'И
# ============================================================

async def handle_openings_callback(query, context, data):
    """Обработчик callback'ов проёмов."""
    if data.startswith("openings_list_"):
        room_id = int(data.replace("openings_list_", ""))
        openings = get_openings(room_id)
        room = get_room(room_id)
        room_name = room['name'] if room else '?'
        text = f"🚪 *Проёмы в комнате «{room_name}»*\n\n"
        if not openings:
            text += "_Пока проёмов нет._"
        else:
            for i, o in enumerate(openings, 1):
                text += f"{i}. {format_opening(o)}\n"
        buttons = []
        for o in openings:
            label = OPENING_TYPES.get(o.get('opening_type'), '?')
            wall = o.get('wall_pos') or '?'
            buttons.append([InlineKeyboardButton(f"{label} ({wall})", callback_data=f"opening_show_{o['id']}")])
        buttons.append([InlineKeyboardButton("➕ Добавить проём", callback_data=f"opening_add_{room_id}")])
        buttons.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass
        return True

    if data.startswith("opening_add_"):
        room_id = int(data.replace("opening_add_", ""))
        buttons = []
        for code, label in OPENING_TYPES.items():
            buttons.append([InlineKeyboardButton(label, callback_data=f"opening_type_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")])
        try:
            await query.edit_message_text(
                "🚪 *Новый проём*\n\nВыбери тип:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_type_"):
        parts = data.replace("opening_type_", "").split("_", 1)
        room_id = int(parts[0])
        otype = parts[1] if len(parts) > 1 else 'window'
        context.user_data['opening_room_id'] = room_id
        context.user_data['opening_type'] = otype
        label = OPENING_TYPES.get(otype, otype)
        buttons = [
            [InlineKeyboardButton("1. Напротив", callback_data=f"opening_wall_{room_id}_напротив")],
            [InlineKeyboardButton("2. Слева", callback_data=f"opening_wall_{room_id}_слева")],
            [InlineKeyboardButton("3. У входа", callback_data=f"opening_wall_{room_id}_у входа")],
            [InlineKeyboardButton("4. Справа", callback_data=f"opening_wall_{room_id}_справа")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
        ]
        try:
            await query.edit_message_text(
                f"🚪 *{label}*\n\nНа какой стене?",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_wall_"):
        parts = data.replace("opening_wall_", "").split("_", 1)
        room_id = int(parts[0])
        wall_pos = parts[1] if len(parts) > 1 else 'напротив'
        context.user_data['opening_wall_pos'] = wall_pos
        context.user_data['waiting_for'] = 'opening_width'
        try:
            await query.edit_message_text(
                "📏 *Ширина проёма* (СМ):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_show_"):
        opening_id = int(data.replace("opening_show_", ""))
        o = get_opening(opening_id)
        if not o:
            try:
                await query.edit_message_text("❌ Проём не найден")
            except Exception:
                pass
            return True
        otype = o.get('opening_type') or '?'
        label = OPENING_TYPES.get(otype, otype)
        text = f"🚪 *Проём #{opening_id}*\n\n{label}\n"
        text += f"🧱 Стена: {o.get('wall_pos') or '?'}\n"
        if o.get('width'): text += f"📏 Ширина: {o['width']} см\n"
        if o.get('height'): text += f"📏 Высота: {o['height']} см\n"
        if o.get('sill_height'): text += f"📏 Подоконник: {o['sill_height']} см\n"
        buttons = [
            [InlineKeyboardButton("✏️ Ширина", callback_data=f"opening_edit_{opening_id}_width")],
            [InlineKeyboardButton("✏️ Высота", callback_data=f"opening_edit_{opening_id}_height")],
            [InlineKeyboardButton("🗑 Удалить", callback_data=f"opening_del_{opening_id}")],
            [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{o['room_id']}")],
        ]
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            pass
        return True

    if data.startswith("opening_edit_"):
        parts = data.replace("opening_edit_", "").split("_")
        opening_id = int(parts[0])
        field = parts[1] if len(parts) > 1 else 'width'
        context.user_data['opening_edit_id'] = opening_id
        context.user_data['opening_edit_field'] = field
        context.user_data['waiting_for'] = 'opening_edit_value'
        prompts = {'width': 'Ширина', 'height': 'Высота', 'sill': 'Подоконник'}
        try:
            await query.edit_message_text(
                f"✏️ *{prompts.get(field, 'Значение')}* (СМ):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"opening_show_{opening_id}")],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("opening_del_"):
        opening_id = int(data.replace("opening_del_", ""))
        o = get_opening(opening_id)
        room_id = o['room_id'] if o else None
        delete_opening(opening_id)
        if room_id:
            try:
                await query.edit_message_text(
                    "✅ Проём удалён",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К проёмам", callback_data=f"openings_list_{room_id}")],
                    ])
                )
            except Exception:
                pass
        return True

    return False


# ============================================================
# ПЛАН КОМНАТЫ (PNG)
# ============================================================

async def handle_floors_callback(query, context, data):
    """Помещения объекта (этажи / зоны)."""
    print(f"🟠 handle_floors_callback: data={data!r}, core_floors={core_floors is not None}", flush=True)
    if not core_floors:
        try:
            await query.edit_message_text("❌ Модуль помещений не загружен")
        except Exception:
            pass
        return True

    # --- СПИСОК ПОМЕЩЕНИЙ ---
    if data.startswith("obj_floors_"):
        object_id = int(data.replace("obj_floors_", ""))
        await _show_floors_list(query, object_id)
        return True

    # --- СОЗДАТЬ ПОМЕЩЕНИЕ ---
    if data.startswith("obj_floor_add_"):
        object_id = int(data.replace("obj_floor_add_", ""))
        context.user_data['waiting_for'] = 'floor_new_name'
        context.user_data['floor_obj_id'] = object_id
        try:
            await query.edit_message_text(
                "🏠 *Новое помещение*\n\nНапиши название (например «1 этаж», «Цоколь», «Зал»):",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"obj_floors_{object_id}")],
                ])
            )
        except Exception:
            pass
        return True

    # --- КАРТОЧКА ПОМЕЩЕНИЯ ---
    if data.startswith("floor_"):
        parts = data.replace("floor_", "").split("_", 1)
        if parts[0].isdigit():
            floor_id = int(parts[0])
            action = parts[1] if len(parts) > 1 else ''
            if action == 'del':
                await _do_delete_floor(query, floor_id)
            else:
                await _show_floor_card(query, floor_id)
            return True

    # --- КОМНАТЫ ПОМЕЩЕНИЯ (список) ---
    if data.startswith("floor_rooms_"):
        floor_id = int(data.replace("floor_rooms_", ""))
        await _show_floor_rooms_list(query, context, floor_id)
        return True

    # --- ГРУППЫ ЭТАЖА ---
    if data.startswith("floor_groups_"):
        fid = int(data.replace("floor_groups_", ""))
        await _show_floor_groups(query, fid)
        return True

    if data.startswith("floor_group_new_"):
        fid = int(data.replace("floor_group_new_", ""))
        context.user_data['group_floor_id'] = fid
        buttons = []
        for code, label in core_spec.PURPOSE_TYPES.items():
            buttons.append([InlineKeyboardButton(label, callback_data=f"floor_group_purpose_{fid}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"floor_groups_{fid}")])
        try:
            await query.edit_message_text(
                "⚡ *Новая группа этажа*\n\nНазначение:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("floor_group_purpose_"):
        parts = data.replace("floor_group_purpose_", "").rsplit("_", 1)
        fid = int(parts[0])
        purpose = parts[1]
        context.user_data['group_floor_id'] = fid
        context.user_data['group_purpose'] = purpose
        label = core_spec.PURPOSE_TYPES.get(purpose, purpose)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1-фазная", callback_data=f"floor_group_phase_{fid}_1")],
            [InlineKeyboardButton("3-фазная", callback_data=f"floor_group_phase_{fid}_3")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"floor_groups_{fid}")],
        ])
        try:
            await query.edit_message_text(f"⚡ *{label}*\n\nФаза:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        except Exception:
            pass
        return True

    if data.startswith("floor_group_phase_"):
        parts = data.replace("floor_group_phase_", "").rsplit("_", 1)
        fid = int(parts[0])
        phase = int(parts[1])
        context.user_data['group_floor_id'] = fid
        context.user_data['group_phase'] = phase
        context.user_data['waiting_for'] = 'group_load_watt'
        try:
            await query.edit_message_text(
                "⚡ Мощность группы в *Вт*?\n\n_Например: 500_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"floor_groups_{fid}")],
                ])
            )
        except Exception:
            pass
        return True

    return False


async def _show_floors_list(query, object_id):
    """Список помещений объекта."""
    print(f"🟠 _show_floors_list: object_id={object_id}", flush=True)
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else f'Объект {object_id}'

    floors = core_floors.get_floors(object_id)
    text = f"🏠 *Помещения «{obj_name}»*\n\n{core_floors.list_floors_text(object_id)}"

    buttons = []
    for f in floors:
        name = f.get('floor_name') or f"Этаж {f.get('floor_number')}"
        rooms = core_floors.count_rooms(f['id'])
        buttons.append([InlineKeyboardButton(
            f"🏠 {name} ({rooms} комн.)",
            callback_data=f"floor_{f['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить помещение", callback_data=f"obj_floor_add_{object_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К объекту", callback_data=f"obj_{object_id}")])

    try:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        print(f"⚠️ _show_floors_list: {e}", flush=True)


async def _show_floor_groups(query, floor_id):
    """Список групп этажа."""
    if not core_elec:
        try:
            await query.edit_message_text("❌ Модуль ЭОМ не загружен")
        except Exception:
            pass
        return

    f = core_floors.get_floor(floor_id)
    name = f.get('floor_name') or f"Этаж {f.get('floor_number')}" if f else "?"

    groups = core_elec.get_groups_by_floor(floor_id)

    lines = [f"⚡ *Группы этажа* «{name}»\n"]
    if not groups:
        lines.append("_Пока групп нет._\n")
    else:
        total_w = 0
        for g in groups:
            lines.append(core_elec.format_group_with_rooms(g['id']))
            total_w += g.get('load_watt') or 0
        lines.append(f"\n📊 *Групп: {len(groups)} · Σ {int(total_w)} Вт*")

    # Распределение по фазам L1/L2/L3 (для объекта этажа)
    try:
        _floor = core_floors.get_floor(floor_id)
        _obj_id = _floor.get('object_id') if _floor else None
        if _obj_id:
            _phase_text = core_elec.format_phase_distribution(_obj_id)
            if _phase_text:
                lines.append("")
                lines.append(_phase_text)
    except Exception as e:
        print(f"⚠️ floor phase distribution: {e}", flush=True)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🍳 Из шаблона (кухня)", callback_data=f"floor_kitchen_{floor_id}")],
        [InlineKeyboardButton("➕ Создать группу", callback_data=f"floor_group_new_{floor_id}")],
        [InlineKeyboardButton("⬅️ К помещению", callback_data=f"floor_{floor_id}")],
    ])
    try:
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception as e:
        print(f"⚠️ _show_floor_groups: {e}", flush=True)


async def _show_floor_card(query, floor_id):
    """Карточка помещения."""
    f = core_floors.get_floor(floor_id)
    if not f:
        try:
            await query.edit_message_text("❌ Помещение не найдено")
        except Exception:
            pass
        return

    object_id = f.get('object_id')
    name = f.get('floor_name') or f"Этаж {f.get('floor_number')}"
    rooms = core_floors.get_rooms_of_floor(floor_id)

    lines = [f"🏠 *{name}*"]
    if f.get('area_sqm'):
        lines.append(f"📐 Площадь: {f['area_sqm']} м²")
    if f.get('height_avg'):
        lines.append(f"📏 Высота: {f['height_avg']} см")
    lines.append("")
    lines.append(f"📦 *Комнаты ({len(rooms)}):*")
    if not rooms:
        lines.append("_Пока нет комнат_")
    else:
        for r in rooms:
            lines.append(f"  • {r['name']}")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Комнаты", callback_data=f"floor_rooms_{floor_id}")],
        [InlineKeyboardButton("⚡ Группы этажа", callback_data=f"floor_groups_{floor_id}")],
        [InlineKeyboardButton("⚡ ЭОМ объекта", callback_data=f"obj_elec_{object_id}")],
        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"floor_rename_{floor_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"floor_{floor_id}_del")],
        [InlineKeyboardButton("⬅️ К помещениям", callback_data=f"obj_floors_{object_id}")],
    ])
    try:
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception as e:
        print(f"⚠️ _show_floor_card: {e}", flush=True)


async def _show_floor_rooms_list(query, context, floor_id):
    """Список комнат помещения (кликабельный)."""
    f = core_floors.get_floor(floor_id)
    if not f:
        try:
            await query.edit_message_text("❌ Помещение не найдено")
        except Exception:
            pass
        return
    floor_name = f.get('floor_name') or f"Этаж {f.get('floor_number')}"
    object_id = f.get('object_id')
    rooms = core_floors.get_rooms_of_floor(floor_id)

    text = f"📦 *Комнаты «{floor_name}»*\n\n"
    if not rooms:
        text += "_Пока комнат нет._"
    else:
        text += f"Всего: {len(rooms)}\n"

    buttons = []
    for r in rooms:
        buttons.append([InlineKeyboardButton(
            f"📦 {r['name']}",
            callback_data=f"room_{r['id']}"
        )])
    buttons.append([InlineKeyboardButton("➕ Добавить комнату", callback_data=f"room_add_{object_id}")])
    buttons.append([InlineKeyboardButton("⬅️ К помещению", callback_data=f"floor_{floor_id}")])

    try:
        await query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        print(f"⚠️ _show_floor_rooms_list: {e}", flush=True)

async def _do_delete_floor(query, floor_id):
    f = core_floors.get_floor(floor_id)
    if not f:
        return
    object_id = f.get('object_id')
    core_floors.delete_floor(floor_id)
    await _show_floors_list(query, object_id)


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

    if data.startswith("obj_elec_") and not data.startswith(("obj_elec_cost_", "obj_elec_pdf_")):
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


async def handle_groups_callback(query, context, data):
    """Управление группами ЭОМ."""
    if not core_elec:
        try:
            await query.edit_message_text("❌ Модуль ЭОМ не загружен")
        except Exception:
            pass
        return True

    # --- ТРАССЫ ГРУППЫ ---
    if data.startswith("group_routes_auto_"):
        group_id = int(data.replace("group_routes_auto_", ""))
        try:
            res = core_elec_routes.auto_routes_for_group(group_id, route_type="shtroba") if core_elec_routes else None
        except Exception as e:
            print("auto routes: " + str(e), flush=True)
            res = None
        if not res:
            try:
                await query.edit_message_text("Ошибка автотрассировки")
            except Exception:
                pass
            return True
        text = (
            "🪄 Авто-трассировка выполнена" + chr(10) + chr(10) +
            "Создано трасс: " + str(res.get('created', 0)) + chr(10) +
            "Пропущено: " + str(res.get('skipped', 0)) + chr(10) +
            "Суммарно: " + str(res.get('total_m', 0)) + " м"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📏 Трассы", callback_data="group_routes_" + str(group_id))],
                    [InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("group_routes_clear_"):
        group_id = int(data.replace("group_routes_clear_", ""))
        try:
            if core_elec_routes:
                core_elec_routes.delete_routes_by_group(group_id, only_auto=True)
        except Exception as e:
            print("clear routes: " + str(e), flush=True)
        try:
            await query.edit_message_text(
                "🗑 Авто-трассы удалены",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("group_routes_"):
        group_id = int(data.replace("group_routes_", ""))
        print("group_routes_ handler: group_id=" + str(group_id), flush=True)
        try:
            text = core_elec_routes.format_routes_summary(group_id=group_id) if core_elec_routes else "Модуль не загружен"
            routes = core_elec_routes.get_routes_by_group(group_id) if core_elec_routes else []
        except Exception as e:
            print("routes show: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
            routes = []
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        kb_rows = []
        for idx, r in enumerate(routes, start=1):
            label = core_elec_routes.format_route(r)[:45] if core_elec_routes else "?"
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + label,
                callback_data="route_" + str(r['id'])
            )])
        kb_rows.append([InlineKeyboardButton("🪄 Авто-трассировка", callback_data="group_routes_auto_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("🗑 Очистить", callback_data="group_routes_clear_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К группе", callback_data="group_" + str(group_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    # --- КАРТОЧКА ТРАССЫ ---
    if data.startswith("route_edit_len_"):
        route_id = int(data.replace("route_edit_len_", ""))
        context.user_data['route_edit_id'] = route_id
        context.user_data['waiting_for'] = 'route_length'
        try:
            await query.edit_message_text(
                "📏 Новая длина (метры):" + chr(10) + chr(10) + "_Например: 12.5_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="route_" + str(route_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("route_edit_type_"):
        route_id = int(data.replace("route_edit_type_", ""))
        context.user_data['route_edit_id'] = route_id
        try:
            await query.edit_message_text(
                "🛠 Выбери тип прокладки:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Штроба", callback_data="route_set_type_" + str(route_id) + "_shtroba")],
                    [InlineKeyboardButton("Потолок", callback_data="route_set_type_" + str(route_id) + "_potolok")],
                    [InlineKeyboardButton("Стяжка", callback_data="route_set_type_" + str(route_id) + "_styazhka")],
                    [InlineKeyboardButton("Лоток", callback_data="route_set_type_" + str(route_id) + "_lotok")],
                    [InlineKeyboardButton("Открыто", callback_data="route_set_type_" + str(route_id) + "_otkryto")],
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="route_" + str(route_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("route_set_type_"):
        parts = data.replace("route_set_type_", "").rsplit("_", 1)
        route_id = int(parts[0])
        rtype = parts[1]
        try:
            core_elec_routes.update_route(route_id, route_type=rtype, is_manual=1)
        except Exception as e:
            print("route set type: " + str(e), flush=True)
        await _show_route_card(query, route_id)
        return True

    if data.startswith("route_del_"):
        route_id = int(data.replace("route_del_", ""))
        try:
            r = core_elec_routes.get_route(route_id)
            group_id = r.get('group_id') if r else None
            panel_id = r.get('panel_id') if r else None
            core_elec_routes.delete_route(route_id)
        except Exception as e:
            print("route del: " + str(e), flush=True)
            group_id = None
            panel_id = None
        kb = []
        if group_id:
            kb.append([InlineKeyboardButton("⬅️ К трассам группы", callback_data="group_routes_" + str(group_id))])
        elif panel_id:
            kb.append([InlineKeyboardButton("⬅️ К трассам щита", callback_data="panel_routes_" + str(panel_id))])
        try:
            await query.edit_message_text("✅ Трасса удалена", reply_markup=InlineKeyboardMarkup(kb) if kb else None)
        except Exception:
            pass
        return True

    if data.startswith("route_") and not data.startswith(("route_edit_", "route_set_", "route_del_")):
        try:
            route_id = int(data.replace("route_", ""))
        except ValueError:
            return False
        await _show_route_card(query, route_id)
        return True

    # --- КАРТОЧКА ГРУППЫ ---
    if data.startswith("group_panel_pick_"):
        group_id = int(data.replace("group_panel_pick_", ""))
        g = core_elec.get_group(group_id) if core_elec else None
        if not g:
            try:
                await query.edit_message_text("Группа не найдена")
            except Exception:
                pass
            return True
        object_id = g.get('object_id')
        panels = core_elec_panels.get_panels(object_id) if core_elec_panels else []
        if not panels:
            try:
                await query.edit_message_text(
                    "У объекта нет щитов. Создай щит сначала.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("K группе", callback_data="group_" + str(group_id))],
                    ])
                )
            except Exception:
                pass
            return True
        cur_panel_id = g.get('panel_id')
        lines = ["Привязать группу к щиту:", ""]
        kb_rows = []
        for idx, p2 in enumerate(panels, start=1):
            ptype = core_elec_panels.get_panel_type_label(p2.get('panel_type'))
            mark = " - текущий" if p2['id'] == cur_panel_id else ""
            pname = (p2.get('name') or '?')[:30]
            lines.append(str(idx) + ". " + pname + " (" + str(ptype) + ")" + mark)
            label = str(idx) + ". " + pname + mark
            kb_rows.append([InlineKeyboardButton(
                label[:60],
                callback_data="group_panel_set_" + str(group_id) + "_" + str(p2['id'])
            )])
        kb_rows.append([InlineKeyboardButton("K группе", callback_data="group_" + str(group_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("group_panel_set_"):
        parts = data.replace("group_panel_set_", "").rsplit("_", 1)
        group_id = int(parts[0])
        panel_id = int(parts[1])
        try:
            if core_elec_panels:
                core_elec_panels.assign_group_to_panel(group_id, panel_id)
                core_elec_panels.recalc_panel_safe(panel_id)
        except Exception as e:
            print("group_panel_set: " + str(e), flush=True)
        await handle_panels_callback(query, context, "panel_" + str(panel_id))
        return True

    if data.startswith("group_panel_unset_"):
        group_id = int(data.replace("group_panel_unset_", ""))
        _old_panel_id = None
        try:
            _g_before = core_elec.get_group(group_id) if core_elec else None
            _old_panel_id = _g_before.get("panel_id") if _g_before else None
        except Exception:
            _old_panel_id = None
        try:
            if core_elec_panels:
                core_elec_panels.unassign_group_from_panel(group_id)
                if _old_panel_id:
                    core_elec_panels.recalc_panel_safe(_old_panel_id)
        except Exception as e:
            print("group_panel_unset: " + str(e), flush=True)
        _g = core_elec.get_group(group_id) if core_elec else None
        _obj_id = _g.get("object_id") if _g else 0
        await handle_panels_callback(query, context, "panels_list_" + str(_obj_id))
        return True

    if data.startswith("group_") and not data.startswith(("group_new_", "group_purpose_", "group_phase_", "group_routes_")):
        try:
            group_id = int(data.replace("group_", ""))
        except ValueError:
            return False
        try:
            g = core_elec.get_group(group_id) if core_elec else None
        except Exception:
            g = None
        if not g:
            try:
                await query.edit_message_text("Группа не найдена")
            except Exception:
                pass
            return True
        _phase = g.get('phase') or 1
        _load = int(g.get('load_watt') or 0)
        _breaker = g.get('breaker_type') or '—'
        _cable = g.get('cable_type') or '—'
        _purpose = g.get('purpose') or '—'
        _panel_id = g.get('panel_id')
        text = (
            "⚡ *" + str(g.get('name') or '?') + "*" + chr(10) + chr(10) +
            "Назначение: " + str(_purpose) + chr(10) +
            "Фаза: " + str(_phase) + "ф" + chr(10) +
            "Мощность: " + str(_load) + " Вт" + chr(10) +
            "Автомат: " + str(_breaker) + chr(10) +
            "Кабель: " + str(_cable)
        )
        if _panel_id:
            text += chr(10) + "Щит: " + (core_elec_panels.get_panel(_panel_id).get("name") if (core_elec_panels and core_elec_panels.get_panel(_panel_id)) else ("#" + str(_panel_id)))
        kb_rows = [
            [InlineKeyboardButton("📏 Трассы", callback_data="group_routes_" + str(group_id))],
        ]
        if _panel_id:
            kb_rows.append([InlineKeyboardButton("⚡ К щиту", callback_data="panel_" + str(_panel_id))])
            kb_rows.append([InlineKeyboardButton("⚡ Сменить щит", callback_data="group_panel_pick_" + str(group_id))])
            kb_rows.append([InlineKeyboardButton("⚡ Отвязать", callback_data="group_panel_unset_" + str(group_id))])
        else:
            kb_rows.append([InlineKeyboardButton("⚡ Привязать к щиту", callback_data="group_panel_pick_" + str(group_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К группам", callback_data="room_groups_" + str(g.get('room_id') or 0))])
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("group card: " + str(e), flush=True)
        return True

    # --- СПИСОК ГРУПП КОМНАТЫ ---
    if data.startswith("room_groups_"):
        room_id = int(data.replace("room_groups_", ""))
        room = get_room(room_id)
        name = room.get('name', '?') if room else '?'

        # Новая архитектура: группы через точки (room_comms.group_id)
        # Fallback на legacy (room_id) — если точек с группой ещё нет
        groups = core_elec.get_groups_by_room(room_id)
        if not groups:
            groups = core_elec.get_groups(room_id)
        lines = ["📋 Группы ЭОМ «" + str(name) + "»", ""]
        if not groups:
            lines.append("_Пока групп нет._\n")
        else:
            total_w = 0
            for g in groups:
                lines.append(core_elec.format_group(g))
                total_w += g.get('load_watt') or 0
            lines.append(f"\n📊 *Групп: {len(groups)} · Σ {int(total_w)} Вт*")

        kb_rows = []
        for g in groups:
            gname = (g.get('name') or ('Группа #' + str(g['id'])))[:40]
            kb_rows.append([InlineKeyboardButton(
                "⚡ " + gname,
                callback_data="group_" + str(g['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Создать группу", callback_data=f"group_new_{room_id}")])
        kb_rows.append([InlineKeyboardButton("⬅️ К комнате", callback_data=f"room_{room_id}")])
        kb = InlineKeyboardMarkup(kb_rows)
        try:
            await query.edit_message_text(
                "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except Exception:
            pass
        return True

    # --- СОЗДАНИЕ ГРУППЫ (шаг 1: назначение) ---
    if data.startswith("group_new_"):
        room_id = int(data.replace("group_new_", ""))
        buttons = []
        for code, label in core_spec.PURPOSE_TYPES.items():
            buttons.append([InlineKeyboardButton(label, callback_data=f"group_purpose_{room_id}_{code}")])
        buttons.append([InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_groups_{room_id}")])
        try:
            await query.edit_message_text(
                "⚡ *Новая группа*\n\nВыбери назначение:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    # --- ВЫБОР НАЗНАЧЕНИЯ (шаг 2: фаза) ---
    if data.startswith("group_purpose_"):
        parts = data.replace("group_purpose_", "").rsplit("_", 1)
        room_id = int(parts[0])
        purpose = parts[1]
        context.user_data['group_room_id'] = room_id
        context.user_data['group_purpose'] = purpose
        label = core_spec.PURPOSE_TYPES.get(purpose, purpose)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("1-фазная", callback_data=f"group_phase_{room_id}_1")],
            [InlineKeyboardButton("3-фазная", callback_data=f"group_phase_{room_id}_3")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_groups_{room_id}")],
        ])
        try:
            await query.edit_message_text(
                f"⚡ *{label}*\n\nФаза:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb
            )
        except Exception:
            pass
        return True

    # --- ВЫБОР ФАЗЫ (шаг 3: ввод мощности) ---
    if data.startswith("group_phase_"):
        parts = data.replace("group_phase_", "").rsplit("_", 1)
        room_id = int(parts[0])
        phase = int(parts[1])
        context.user_data['group_phase'] = phase
        context.user_data['waiting_for'] = 'group_load_watt'
        try:
            await query.edit_message_text(
                f"⚡ Мощность группы в *Вт*?\n\n_Например: 2000_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data=f"room_groups_{room_id}")],
                ])
            )
        except Exception:
            pass
        return True

    return False


async def handle_reports_callback(query, context, data):
    """Меню планов и отчётов."""
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

async def handle_rooms_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер всех callback'ов комнат."""
    query = update.callback_query
    print(f"🔴 HANDLE_ROOMS_CALLBACK ВЫЗВАН: {query.data!r}", flush=True)
    await query.answer()
    data = query.data
    print(f"🔍 ROOMS: data={data!r}", flush=True)

    # --- Объекты ---
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
    if data.startswith("obj_elec_") and not data.startswith(("obj_elec_cost_", "obj_elec_pdf_")):
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
        object_id = int(data.replace("room_add_", ""))
        context.user_data['waiting_for'] = 'room_name'
        context.user_data['room_object_id'] = object_id
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
        new_room_id = create_room(object_id, name, room_type=room_type)
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

    if data.startswith(("obj_elec_pdf_", "plumb_pdf_obj_")):
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
    walls_ok = len(walls) >= 4
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
    walls_ok = len(walls) >= 4

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

        if step == "panel_comp_rating":
            panel_id = context.user_data.get("panel_comp_panel_id")
            ctype = context.user_data.get("panel_comp_type")
            text_in = update.message.text.strip()
            try:
                rating = int(text_in)
            except ValueError:
                await update.message.reply_text("Нужно число, например 16. Попробуй ещё раз.")
                return
            try:
                core_elec_panels.add_component(panel_id, component_type=ctype, rating=rating, is_manual=1)
            except Exception as e:
                print("panel comp add: " + str(e), flush=True)
            for k in ["panel_comp_panel_id", "panel_comp_type", "waiting_for"]:
                context.user_data[k] = None
            await update.message.reply_text("✅ Компонент добавлен", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚡ К щиту", callback_data="panel_" + str(panel_id))], [InlineKeyboardButton("📦 К компонентам", callback_data="panel_comp_" + str(panel_id))]]))
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
                floor_id = core_floors.create_floor(object_id, floor_number=1, floor_name=name)
                context.user_data['waiting_for'] = None
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


async def _handle_comm_input(update, context, step):
    """Ввод коммуникаций — заглушка, реализуем отдельно при необходимости."""
    context.user_data['waiting_for'] = None
    await update.message.reply_text("⚠️ Ввод коммуникаций временно отключён — используйте кнопки.")


async def _handle_opening_input(update, context, step):
    """Ввод проёмов (отдельных)."""
    text_val = (update.message.text or '').strip().replace(',', '.')
    try:
        val = float(text_val)
    except ValueError:
        await update.message.reply_text("❌ Введи число")
        return

    if step == 'opening_width':
        room_id = context.user_data.get('opening_room_id')
        context.user_data['opening_width'] = val
        context.user_data['waiting_for'] = 'opening_height'
        await update.message.reply_text(
            "📏 *Высота проёма* (СМ):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Отмена", callback_data=f"openings_list_{room_id}")],
            ])
        )
        return

    if step == 'opening_height':
        room_id = context.user_data.get('opening_room_id')
        otype = context.user_data.get('opening_type')
        wall_pos = context.user_data.get('opening_wall_pos')
        width = context.user_data.get('opening_width')
        try:
            session_id = ensure_session(room_id)
        except Exception:
            session_id = None
        add_opening(room_id=room_id, opening_type=otype, wall_pos=wall_pos,
                    width=width, height=val, session_id=session_id,
                    created_by=update.effective_user.id if update.effective_user else None)
        for k in ['opening_room_id', 'opening_type', 'opening_wall_pos',
                  'opening_width', 'opening_height', 'waiting_for']:
            context.user_data[k] = None
        await update.message.reply_text(
            f"✅ *Проём добавлен!*\n\n{OPENING_TYPES.get(otype, otype)} на стене «{wall_pos}»\n📏 {width} × {val} см",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Ещё", callback_data=f"opening_add_{room_id}")],
                [InlineKeyboardButton("✅ К проёмам", callback_data=f"openings_list_{room_id}")],
            ])
        )
        return

    if step == 'opening_edit_value':
        opening_id = context.user_data.get('opening_edit_id')
        field = context.user_data.get('opening_edit_field')
        if field == 'width':
            update_opening(opening_id, width=val)
        elif field == 'height':
            update_opening(opening_id, height=val)
        elif field == 'sill':
            update_opening(opening_id, sill_height=val)
        context.user_data['waiting_for'] = None
        context.user_data['opening_edit_id'] = None
        context.user_data['opening_edit_field'] = None
        await update.message.reply_text(
            "✅ Обновлено!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К проёму", callback_data=f"opening_show_{opening_id}")],
            ])
        )
        return


# ============================================================
# ОБЪЕКТЫ — РЕДАКТИРОВАНИЕ
# ============================================================

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

async def handle_kitchen_callback(query, context, data):
    """Обработчик кухонных шаблонов. Возвращает True если обработано."""
    if not core_elec:
        return False

    # --- ПОКАЗ СПИСКА ОБОРУДОВАНИЯ ---
    if data.startswith("floor_kitchen_add_"):
        parts = data.replace("floor_kitchen_add_", "").rsplit("_", 1)
        floor_id = int(parts[0])
        equip_idx = int(parts[1])
        items = core_elec.get_kitchen_equipment()
        if equip_idx < 0 or equip_idx >= len(items):
            try:
                await query.edit_message_text("Оборудование не найдено")
            except Exception:
                pass
            return True
        equip_code = items[equip_idx][0]
        try:
            _floor = core_floors.get_floor(floor_id)
            _obj_id = _floor.get('object_id') if _floor else None
        except Exception:
            _obj_id = None
        if not _obj_id:
            try:
                await query.edit_message_text("Помещение не найдено")
            except Exception:
                pass
            return True
        try:
            gid = core_elec.create_kitchen_group(_obj_id, floor_id, equip_code)
        except Exception as e:
            print(f"kitchen create: {e}", flush=True)
            gid = None
        if gid:
            try:
                _g = core_elec.get_group(gid)
                _name = (_g.get('name') if _g else '?')
                _phase = (_g.get('phase') if _g else 0) or 1
                _load = int((_g.get('load_watt') if _g else 0) or 0)
                _breaker = (_g.get('breaker_type') if _g else '-') or '-'
                _cable = (_g.get('cable_type') if _g else '-') or '-'
                _voltage = 380 if _phase == 3 else 220
                try:
                    _current = core_elec.calc_current(_load, _phase, _voltage)
                except Exception:
                    _current = 0
                try:
                    _cable_label = core_spec.get_cable_label(_cable)
                except Exception:
                    _cable_label = _cable
                _text = (
                    "✅ Группа создана!\n\n"
                    "⚡ " + str(_name) + "\n"
                    "Фаза: " + str(_phase) + "ф (" + str(_voltage) + "В)\n"
                    "Мощность: " + str(_load) + " Вт\n"
                    "Ток: " + str(_current) + " А\n"
                    "Автомат: " + str(_breaker) + "\n"
                    "Кабель: " + str(_cable_label)
                )
                await query.edit_message_text(
                    _text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Ещё оборудование", callback_data="floor_kitchen_" + str(floor_id))],
                        [InlineKeyboardButton("⚡ К группам этажа", callback_data="floor_groups_" + str(floor_id))],
                    ])
                )
            except Exception as e:
                print(f"kitchen msg: {e}", flush=True)
                try:
                    await query.edit_message_text(
                        "✅ Группа создана (ID: " + str(gid) + ")",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("<< Назад", callback_data="floor_kitchen_" + str(floor_id))],
                        ])
                    )
                except Exception:
                    pass
        else:
            try:
                await query.edit_message_text(
                    "❌ Не удалось создать группу.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("<< Назад", callback_data="floor_kitchen_" + str(floor_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("floor_kitchen_all_"):
        floor_id = int(data.replace("floor_kitchen_all_", ""))
        try:
            _floor = core_floors.get_floor(floor_id)
            _obj_id = _floor.get('object_id') if _floor else None
        except Exception:
            _obj_id = None
        if not _obj_id:
            return True
        created = 0
        try:
            items = core_elec.get_kitchen_equipment()
            for code, name, watts, phase in items:
                try:
                    gid = core_elec.create_kitchen_group(_obj_id, floor_id, code)
                    if gid:
                        created += 1
                except Exception as e:
                    print(f"kitchen all {code}: {e}", flush=True)
        except Exception as e:
            print(f"kitchen all: {e}", flush=True)
        try:
            await query.edit_message_text(
                "Создано: " + str(created) + " групп.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("<< Назад", callback_data="floor_groups_" + str(floor_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("floor_kitchen_"):
        floor_id = int(data.replace("floor_kitchen_", ""))
        try:
            items = core_elec.get_kitchen_equipment()
        except Exception as e:
            print(f"kitchen list: {e}", flush=True)
            items = []
        if not items:
            try:
                await query.edit_message_text("Оборудование не найдено.")
            except Exception:
                pass
            return True
        buttons = []
        for idx, (code, name, watts, phase) in enumerate(items):
            label = name + " " + str(watts) + "W " + str(phase) + "f"
            buttons.append([InlineKeyboardButton(
                label[:60],
                callback_data="floor_kitchen_add_" + str(floor_id) + "_" + str(idx)
            )])
        buttons.append([InlineKeyboardButton(
            ">> Создать все",
            callback_data="floor_kitchen_all_" + str(floor_id)
        )])
        buttons.append([InlineKeyboardButton("<< Назад", callback_data="floor_groups_" + str(floor_id))])
        try:
            await query.edit_message_text(
                "🍳 Кухня. Выбери оборудование:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    return False

# ============================================================
# КАБЕЛЬНЫЙ ЖУРНАЛ — UI
# ============================================================

async def handle_cables_callback(query, context, data):
    """Обработчик кабельного журнала."""
    if not core_elec:
        return False

    if data.startswith("cables_list_"):
        object_id = int(data.replace("cables_list_", ""))
        try:
            cables = core_elec.get_cables_by_object(object_id)
            summary = core_elec.get_cable_summary(object_id)
        except Exception as e:
            print(f"cables list: {e}", flush=True)
            cables = []
            summary = {}
        lines = ["📋 *Кабельный журнал*"]
        if not cables:
            lines.append("")
            lines.append("_Пока кабелей нет._")
        else:
            lines.append("")
            lines.append("Записей: " + str(summary.get('count', 0)) + " / Всего: " + str(summary.get('total_m', 0)) + " м")
            lines.append("")
            for c in cables[:20]:
                lines.append(core_elec.format_cable(c))
        kb_rows = [
            [InlineKeyboardButton("➕ Добавить кабель", callback_data="cables_add_" + str(object_id))],
            [InlineKeyboardButton("⬅️ Назад", callback_data="obj_elec_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print(f"cables list show: {e}", flush=True)
        return True

    if data.startswith("cables_add_"):
        object_id = int(data.replace("cables_add_", ""))
        try:
            groups = core_elec.get_groups_by_object(object_id)
        except Exception as e:
            print(f"cables add groups: {e}", flush=True)
            groups = []
        if not groups:
            try:
                await query.edit_message_text(
                    "⚠️ Сначала создай хотя бы одну группу ЭОМ.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Назад", callback_data="cables_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
            return True
        buttons = []
        for g in groups[:20]:
            gname = (g.get('name') or ('Группа #' + str(g['id'])))[:35]
            buttons.append([InlineKeyboardButton(
                "⚡ " + gname,
                callback_data="cables_group_" + str(object_id) + "_" + str(g['id'])
            )])
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="cables_list_" + str(object_id))])
        try:
            await query.edit_message_text(
                "📋 *Выбери группу* для кабеля:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            pass
        return True

    if data.startswith("cables_group_"):
        parts = data.replace("cables_group_", "").rsplit("_", 1)
        object_id = int(parts[0])
        group_id = int(parts[1])
        context.user_data['cable_object_id'] = object_id
        context.user_data['cable_group_id'] = group_id
        context.user_data['waiting_for'] = 'cable_from_point'
        try:
            await query.edit_message_text(
                "📋 *Кабель*\n\nОткуда (от щита)?\n\n_Например: Щит этажа_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="cables_list_" + str(object_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("cables_del_"):
        cable_id = int(data.replace("cables_del_", ""))
        try:
            c = core_elec.get_cable(cable_id)
            object_id = c.get('object_id') if c else None
            core_elec.delete_cable(cable_id)
        except Exception as e:
            print(f"cables del: {e}", flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "✅ Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К журналу", callback_data="cables_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    return False

# ============================================================
# ЩИТЫ ЭОМ — UI
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




async def _show_route_card(query, route_id):
    """Карточка трассы."""
    try:
        r = core_elec_routes.get_route(route_id) if core_elec_routes else None
    except Exception as e:
        print("route card: " + str(e), flush=True)
        r = None
    if not r:
        try:
            await query.edit_message_text("Трасса не найдена")
        except Exception:
            pass
        return
    # Инфо
    lines = ["📏 Трасса #" + str(route_id), ""]
    lines.append("Длина: " + str(r.get('length_m') or 0) + " м")
    lines.append("Кабель: " + str(r.get('cable_type') or '—'))
    lines.append("Прокладка: " + str(r.get('route_type') or '—'))
    if r.get('is_manual'):
        lines.append("Тип: [ручная]")
    if r.get('to_point_id'):
        lines.append("Точка: #" + str(r['to_point_id']))
    # Цена
    try:
        cost = core_elec_routes.calc_route_cost(route_id) if core_elec_routes else None
        if cost:
            lines.append("")
            lines.append("💵 Кабель: " + str(cost.get('cable_cost', 0)) + " ₽")
            lines.append("🔧 Расходники: " + str(cost.get('consumable_cost', 0)) + " ₽")
            lines.append("💰 Итого: " + str(cost.get('total', 0)) + " ₽")
    except Exception:
        pass
    # Кнопки
    kb = []
    kb.append([InlineKeyboardButton("✏️ Длина", callback_data="route_edit_len_" + str(route_id))])
    kb.append([InlineKeyboardButton("✏️ Тип прокладки", callback_data="route_edit_type_" + str(route_id))])
    kb.append([InlineKeyboardButton("🗑 Удалить", callback_data="route_del_" + str(route_id))])
    gid = r.get('group_id')
    pid = r.get('panel_id')
    if gid:
        kb.append([InlineKeyboardButton("⬅️ К трассам группы", callback_data="group_routes_" + str(gid))])
    elif pid:
        kb.append([InlineKeyboardButton("⬅️ К трассам щита", callback_data="panel_routes_" + str(pid))])
    await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb))


async def handle_panels_callback(query, context, data):
    """Обработчик щитов ЭОМ. Возвращает True если обработано."""
    if not core_elec_panels:
        try:
            await query.edit_message_text("Модуль щитов не загружен")
        except Exception:
            pass
        return True

    # --- СПИСОК ЩИТОВ ОБЪЕКТА ---
    if data.startswith("panels_list_"):
        object_id = int(data.replace("panels_list_", ""))
        try:
            panels = core_elec_panels.get_panels(object_id)
        except Exception as e:
            print("panels list: " + str(e), flush=True)
            panels = []
        from modules.objects import get_object as _get_obj
        _obj = _get_obj(object_id)
        _obj_name = _obj['name'] if _obj else ('Объект ' + str(object_id))
        lines = ["⚡ *Щиты объекта «" + str(_obj_name) + "»*", ""]
        if not panels:
            lines.append("_Пока щитов нет._")
        else:
            total = 0
            for p in panels:
                try:
                    load = core_elec_panels.calc_panel_load(p['id'])
                except Exception:
                    load = 0
                total += load
            lines.append("Щитов: " + str(len(panels)) + " / Общая нагрузка: " + str(total) + " Вт")
            lines.append("")
            for p in panels:
                ptype = core_elec_panels.get_panel_type_label(p.get('panel_type'))
                lines.append("⚡ *" + str(p.get('name') or '?') + "*")
                lines.append("   " + str(ptype))
        kb_rows = []
        for p in panels:
            pname = (p.get('name') or '?')[:35]
            kb_rows.append([InlineKeyboardButton(
                "⚡ " + pname,
                callback_data="panel_" + str(p['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить щит", callback_data="panel_add_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("panels list show: " + str(e), flush=True)
        return True

    # --- КАРТОЧКА ЩИТА ---
    if data.startswith("panel_groups_"):
        panel_id = int(data.replace("panel_groups_", ""))
        try:
            groups = core_elec_panels.get_groups_by_panel(panel_id)
            p = core_elec_panels.get_panel(panel_id)
        except Exception as e:
            print("panel groups: " + str(e), flush=True)
            groups = []
            p = None
        pname = (p.get('name') if p else '?')
        lines = ["📋 Группы щита «" + str(pname) + "»", ""]
        if not groups:
            lines.append("Пока групп нет.")
        else:
            total = 0
            for idx, g in enumerate(groups, start=1):
                total += int(g.get('load_watt') or 0)
                lines.append(str(idx) + ". " + core_elec.format_group(g))
            lines.append("")
            lines.append("📊 Групп: " + str(len(groups)) + " · Σ " + str(total) + " Вт")
        kb_rows = []
        for idx, g in enumerate(groups, start=1):
            gname = (g.get('name') or ('Группа #' + str(g['id'])))[:35]
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + gname,
                callback_data="group_" + str(g['id'])
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_input_type_"):
        parts = data.replace("panel_input_type_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        btype = parts[1]
        kb_rows = []
        for r in [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100]:
            kb_rows.append([InlineKeyboardButton(
                str(r) + "А",
                callback_data="panel_input_set_" + str(panel_id) + "_" + btype + "_" + str(r)
            )])
        kb_rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="panel_input_" + str(panel_id))])
        try:
            await query.edit_message_text(
                "Номинал (" + btype + "):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_input_set_"):
        parts = data.replace("panel_input_set_", "").split("_")
        panel_id = int(parts[0])
        btype = parts[1]
        rating = int(parts[2])
        poles = 3 if btype == 'auto3' else 1
        try:
            core_elec_panels.set_input_breaker(panel_id, breaker_type=btype.replace('auto3', 'auto'),
                                                rating=rating, curve='C', poles=poles)
        except Exception as e:
            print("panel input set: " + str(e), flush=True)
        try:
            s = core_elec_panels.format_selectivity(panel_id)
        except Exception:
            s = ""
        try:
            await query.edit_message_text(
                "Вводной установлен: " + btype + " " + str(rating) + "А" + chr(10) + chr(10) + s,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_input_"):
        panel_id = int(data.replace("panel_input_", ""))
        cur = core_elec_panels.get_input_breaker(panel_id) or {}
        cur_type = cur.get('type') or 'не задан'
        cur_rating = cur.get('rating') or '-'
        cur_fmt = core_elec_panels.format_input_breaker(panel_id)
        s = core_elec_panels.format_selectivity(panel_id)
        text = (
            "🔌 Вводной автомат" + chr(10) + chr(10) +
            "Сейчас: " + cur_fmt + chr(10) + chr(10) +
            s + chr(10) + chr(10) +
            "Выбери тип:"
        )
        kb_rows = [
            [InlineKeyboardButton("Автомат 1ф", callback_data="panel_input_type_" + str(panel_id) + "_auto")],
            [InlineKeyboardButton("Автомат 3ф", callback_data="panel_input_type_" + str(panel_id) + "_auto3")],
            [InlineKeyboardButton("УЗО", callback_data="panel_input_type_" + str(panel_id) + "_uzo")],
            [InlineKeyboardButton("Дифавтомат", callback_data="panel_input_type_" + str(panel_id) + "_dif")],
            [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_children_"):
        panel_id = int(data.replace("panel_children_", ""))
        try:
            children = core_elec_panels.get_child_panels(panel_id)
        except Exception as e:
            print("panel children: " + str(e), flush=True)
            children = []
        lines = ["⬇️ Дочерние щиты:", ""]
        if not children:
            lines.append("_Пока нет._")
        else:
            for c in children:
                ctype = core_elec_panels.get_panel_type_label(c.get('panel_type'))
                lines.append("└ " + str(c.get('name')) + " (" + str(ctype) + ")")
        kb_rows = []
        for c in children:
            kb_rows.append([InlineKeyboardButton(
                "⚡ " + str(c.get('name'))[:35],
                callback_data="panel_" + str(c['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить дочерний", callback_data="panel_child_add_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("panel children show: " + str(e), flush=True)
        return True

    if data.startswith("panel_child_type_"):
        parts = data.replace("panel_child_type_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        ptype = parts[1]
        context.user_data['child_parent_id'] = panel_id
        context.user_data['child_panel_type'] = ptype
        context.user_data['waiting_for'] = 'child_panel_name'
        type_labels = {
            'floor': 'Щит этажа', 'apartment': 'Щит квартиры',
            'outdoor': 'Уличный щит', 'subpanel': 'Подщиток',
        }
        tlabel = type_labels.get(ptype, ptype)
        try:
            await query.edit_message_text(
                "⬇️ Новый дочерний: " + tlabel + chr(10) + chr(10) + "Напиши название:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_child_add_"):
        panel_id = int(data.replace("panel_child_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("⚡ Щит этажа", callback_data="panel_child_type_" + str(panel_id) + "_floor")],
            [InlineKeyboardButton("🏢 Щит квартиры", callback_data="panel_child_type_" + str(panel_id) + "_apartment")],
            [InlineKeyboardButton("📦 Подщиток", callback_data="panel_child_type_" + str(panel_id) + "_subpanel")],
            [InlineKeyboardButton("🌳 Уличный щит", callback_data="panel_child_type_" + str(panel_id) + "_outdoor")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_children_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                "⬇️ Новый дочерний щит" + chr(10) + chr(10) + "Выбери тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_routes_auto_"):
        panel_id = int(data.replace("panel_routes_auto_", ""))
        print("panel_routes_auto handler: panel_id=" + str(panel_id), flush=True)
        try:
            res = core_elec_routes.auto_routes_for_panel(panel_id, route_type="shtroba") if core_elec_routes else None
        except Exception as e:
            print("panel auto routes: " + str(e), flush=True)
            res = None
        if not res:
            try:
                await query.edit_message_text("Ошибка автотрассировки")
            except Exception:
                pass
            return True
        text = (
            "🪄 Авто-трассировка щита" + chr(10) + chr(10) +
            "Групп обработано: " + str(res.get('groups', 0)) + chr(10) +
            "Создано трасс: " + str(res.get('created', 0)) + chr(10) +
            "Суммарно: " + str(res.get('total_m', 0)) + " м"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📏 Трассы щита", callback_data="panel_routes_" + str(panel_id))],
                    [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception as e:
            print("panel auto routes show: " + str(e), flush=True)
        return True

    if data.startswith("panel_routes_"):
        panel_id = int(data.replace("panel_routes_", ""))
        print("panel_routes handler: panel_id=" + str(panel_id), flush=True)
        try:
            text = core_elec_routes.format_routes_summary(panel_id=panel_id) if core_elec_routes else "Модуль не загружен"
        except Exception as e:
            print("panel routes show: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        try:
            routes = core_elec_routes.get_routes_by_panel(panel_id) if core_elec_routes else []
        except Exception:
            routes = []
        kb_rows = []
        for idx, r in enumerate(routes, start=1):
            label = core_elec_routes.format_route(r)[:45] if core_elec_routes else "?"
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + label,
                callback_data="route_" + str(r['id'])
            )])
        kb_rows.append([InlineKeyboardButton("🪄 Трассировать все", callback_data="panel_routes_auto_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_montage_"):
        panel_id = int(data.replace("panel_montage_", ""))
        try:
            if core_elec_routes:
                text = core_elec_routes.format_montage_cost_summary(panel_id=panel_id)
            else:
                text = "Модуль маршрутов не загружен"
        except Exception as e:
            print("panel montage: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_total_"):
        panel_id = int(data.replace("panel_total_", ""))
        print("panel_total handler: panel_id=" + str(panel_id), flush=True)
        try:
            text = _build_panel_total_text(panel_id)
        except Exception as e:
            print("panel total: " + str(e), flush=True)
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
        context.user_data['waiting_for'] = 'work_new_qty'
        try:
            await query.edit_message_text(
                "🔨 " + core_spec.get_work_label(wtype) + chr(10) + chr(10) +
                "Количество (" + core_spec.get_work_unit(wtype) + "):" + chr(10) + chr(10) +
                "_Например: 15_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="works_list_" + str(object_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("works_add_"):
        object_id = int(data.replace("works_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("Штробление (электро)", callback_data="works_add_type_" + str(object_id) + "_elec_shtroba")],
            [InlineKeyboardButton("Прокладка кабеля", callback_data="works_add_type_" + str(object_id) + "_elec_cable")],
            [InlineKeyboardButton("Установка розетки", callback_data="works_add_type_" + str(object_id) + "_elec_socket")],
            [InlineKeyboardButton("Установка светильника", callback_data="works_add_type_" + str(object_id) + "_elec_light")],
            [InlineKeyboardButton("Монтаж щита", callback_data="works_add_type_" + str(object_id) + "_elec_panel_mount")],
            [InlineKeyboardButton("Прокладка трубы", callback_data="works_add_type_" + str(object_id) + "_plumb_pipe")],
            [InlineKeyboardButton("Установка смесителя", callback_data="works_add_type_" + str(object_id) + "_plumb_socket")],
            [InlineKeyboardButton("Установка унитаза", callback_data="works_add_type_" + str(object_id) + "_plumb_toilet")],
            [InlineKeyboardButton("Установка раковины", callback_data="works_add_type_" + str(object_id) + "_plumb_sink")],
            [InlineKeyboardButton("Установка ванны", callback_data="works_add_type_" + str(object_id) + "_plumb_bath")],
            [InlineKeyboardButton("Установка душа", callback_data="works_add_type_" + str(object_id) + "_plumb_shower")],
            [InlineKeyboardButton("Установка радиатора", callback_data="works_add_type_" + str(object_id) + "_plumb_radiator")],
            [InlineKeyboardButton("Монтаж бойлера", callback_data="works_add_type_" + str(object_id) + "_plumb_boiler")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="works_list_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "🔨 Новая работа" + chr(10) + chr(10) + "Тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("works_del_"):
        work_id = int(data.replace("works_del_", ""))
        try:
            w = core_works.get_work(work_id)
            object_id = w.get('object_id') if w else None
            core_works.delete_work(work_id)
        except Exception as e:
            print("works del: " + str(e), flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К работам", callback_data="works_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("works_edit_qty_"):
        work_id = int(data.replace("works_edit_qty_", ""))
        context.user_data['work_edit_id'] = work_id
        context.user_data['work_edit_field'] = 'qty'
        context.user_data['waiting_for'] = 'work_edit_value'
        w = core_works.get_work(work_id) if core_works else None
        unit = w.get('unit') if w else ''
        try:
            await query.edit_message_text(
                "Новое количество (" + str(unit) + "):" + chr(10) + chr(10) + "_Например: 15_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="works_" + str(work_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("works_edit_price_"):
        work_id = int(data.replace("works_edit_price_", ""))
        context.user_data['work_edit_id'] = work_id
        context.user_data['work_edit_field'] = 'price_unit'
        context.user_data['waiting_for'] = 'work_edit_value'
        try:
            await query.edit_message_text(
                "Новая цена за единицу (₽):" + chr(10) + chr(10) + "_Например: 350_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="works_" + str(work_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("works_") and not data.startswith(("works_list_", "works_add_", "works_del_", "works_edit_")):
        try:
            work_id = int(data.replace("works_", ""))
        except ValueError:
            return False
        w = core_works.get_work(work_id) if core_works else None
        if not w:
            try:
                await query.edit_message_text("Работа не найдена")
            except Exception:
                pass
            return True
        lines = ["🔨 " + str(w.get('work_label') or '?'), ""]
        lines.append("Количество: " + str(w.get('qty') or 0) + " " + str(w.get('unit') or ''))
        lines.append("Цена за ед.: " + str(w.get('price_unit') or 0) + " ₽")
        lines.append("Итого: " + str(w.get('total') or 0) + " ₽")
        mark = " [ручная]" if w.get('is_manual') else ""
        if mark:
            lines.append("Тип: [ручная]")
        kb_rows = [
            [InlineKeyboardButton("✏️ Кол-во", callback_data="works_edit_qty_" + str(work_id)),
             InlineKeyboardButton("✏️ Цена", callback_data="works_edit_price_" + str(work_id))],
            [InlineKeyboardButton("🗑 Удалить", callback_data="works_del_" + str(work_id))],
            [InlineKeyboardButton("⬅️ К работам", callback_data="works_list_" + str(w.get('object_id')))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    # ============ САНТЕХНИКА ============
    if data.startswith("plumb_list_"):
        object_id = int(data.replace("plumb_list_", ""))
        if not core_plumbing:
            try:
                await query.edit_message_text("Модуль сантехники не загружен")
            except Exception:
                pass
            return True
        panels = core_plumbing.get_panels(object_id)
        lines = ["🔧 Сантехника объекта", ""]
        if not panels:
            lines.append("Пока коллекторов нет.")
        else:
            for idx, p in enumerate(panels, start=1):
                ptype = core_plumbing.get_panel_type_label(p.get('panel_type'))
                lines.append(str(idx) + ". " + str(p.get('name')) + " (" + str(ptype) + ")")
        kb_rows = []
        for idx, p in enumerate(panels, start=1):
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + str(p.get('name'))[:35],
                callback_data="plumb_" + str(p['id'])
            )])
        kb_rows.append([InlineKeyboardButton("🚰 Вода", callback_data="plumb_water_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("💰 Смета сантехники", callback_data="plumb_cost_obj_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("📊 Смета (CSV)", callback_data="plumb_csv_obj_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("➕ Добавить коллектор", callback_data="plumb_add_" + str(object_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К объекту", callback_data="obj_" + str(object_id))])
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_add_type_"):
        parts = data.replace("plumb_add_type_", "").rsplit("_", 1)
        object_id = int(parts[0])
        ptype = parts[1]
        context.user_data['plumb_new_object_id'] = object_id
        context.user_data['plumb_new_type'] = ptype
        context.user_data['waiting_for'] = 'plumb_new_name'
        type_labels = {
            'collector': 'Коллектор', 'riser': 'Стояк',
            'boiler': 'Котёл', 'pump': 'Насосная группа', 'filter': 'Фильтр',
        }
        try:
            await query.edit_message_text(
                "🔧 Новый элемент: " + type_labels.get(ptype, ptype) + chr(10) + chr(10) +
                "Напиши название (например «Коллектор ХВС»):",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_list_" + str(object_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_add_"):
        object_id = int(data.replace("plumb_add_", ""))
        kb_rows = [
            [InlineKeyboardButton("Коллектор", callback_data="plumb_add_type_" + str(object_id) + "_collector")],
            [InlineKeyboardButton("Стояк", callback_data="plumb_add_type_" + str(object_id) + "_riser")],
            [InlineKeyboardButton("Котёл", callback_data="plumb_add_type_" + str(object_id) + "_boiler")],
            [InlineKeyboardButton("Насосная группа", callback_data="plumb_add_type_" + str(object_id) + "_pump")],
            [InlineKeyboardButton("Фильтр", callback_data="plumb_add_type_" + str(object_id) + "_filter")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_list_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "🔧 Новый элемент сантехники" + chr(10) + chr(10) + "Тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_del_"):
        panel_id = int(data.replace("plumb_del_", ""))
        try:
            p = core_plumbing.get_panel(panel_id)
            object_id = p.get('object_id') if p else None
            core_plumbing.delete_panel(panel_id)
        except Exception as e:
            print("plumb del: " + str(e), flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_") and not data.startswith(("plumb_list_", "plumb_add_", "plumb_del_", "plumb_spec_", "plumb_csv_obj_", "plumb_cost_", "plumb_cost_obj_", "plumb_routes_", "plumb_route_", "plumb_points_", "plumb_point_add_", "plumb_point_set_", "plumb_point_unset_", "plumb_pdf_obj_")):
        try:
            panel_id = int(data.replace("plumb_", ""))
        except ValueError:
            return False
        try:
            p = core_plumbing.get_panel(panel_id)
        except Exception:
            p = None
        if not p:
            try:
                await query.edit_message_text("Не найдено")
            except Exception:
                pass
            return True
        ptype = core_plumbing.get_panel_type_label(p.get('panel_type'))
        mount = core_plumbing.get_mount_type_label(p.get('mount_type'))
        lines = ["🔧 " + str(p.get('name')) + " (" + str(ptype) + ")", ""]
        lines.append("Монтаж: " + str(mount))
        if p.get('note'):
            lines.append("Заметка: " + str(p['note']))
        # Трассы
        try:
            routes = core_plumbing.get_routes_by_panel(panel_id)
            lines.append("")
            lines.append("Трассы: " + str(len(routes)))
            for idx, r in enumerate(routes, start=1):
                lines.append("  " + str(idx) + ". " + core_plumbing.format_route(r))
        except Exception:
            pass
        kb_rows = [
            [InlineKeyboardButton("📏 Трассы", callback_data="plumb_routes_" + str(panel_id))],
            [InlineKeyboardButton("➕ Добавить трассу", callback_data="plumb_route_new_" + str(panel_id))],
            [InlineKeyboardButton("💰 Смета коллектора", callback_data="plumb_cost_" + str(panel_id))],
            [InlineKeyboardButton("📍 Точки коллектора", callback_data="plumb_points_" + str(panel_id))],
            [InlineKeyboardButton("📄 Спецификация (TXT)", callback_data="plumb_spec_" + str(panel_id))],
            [InlineKeyboardButton("🔨 Работы сантехники", callback_data="works_list_" + str(p.get('object_id')))],
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(p.get('object_id')))],
            [InlineKeyboardButton("🗑 Удалить", callback_data="plumb_del_" + str(panel_id))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    # --- ТРАССЫ САНТЕХНИКИ ---
    if data.startswith("plumb_routes_"):
        panel_id = int(data.replace("plumb_routes_", ""))
        try:
            routes = core_plumbing.get_routes_by_panel(panel_id)
            p = core_plumbing.get_panel(panel_id)
            pname = p.get('name') if p else '?'
        except Exception as e:
            print("plumb routes: " + str(e), flush=True)
            routes = []
            pname = '?'
        lines = ["📏 Трассы коллектора «" + str(pname) + "»", ""]
        if not routes:
            lines.append("Трасс пока нет.")
        else:
            for idx, r in enumerate(routes, start=1):
                lines.append(str(idx) + ". " + core_plumbing.format_route(r))
        kb_rows = []
        for idx, r in enumerate(routes, start=1):
            label = core_plumbing.format_route(r)[:40]
            kb_rows.append([InlineKeyboardButton(
                str(idx) + ". " + label,
                callback_data="plumb_route_" + str(r['id'])
            )])
        kb_rows.append([InlineKeyboardButton("➕ Добавить", callback_data="plumb_route_new_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))])
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_route_new_"):
        panel_id = int(data.replace("plumb_route_new_", ""))
        context.user_data['plumb_route_panel_id'] = panel_id
        # Шаг 1 — тип трубы
        kb_rows = [
            [InlineKeyboardButton("PPR 20 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr20")],
            [InlineKeyboardButton("PPR 25 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr25")],
            [InlineKeyboardButton("PPR 32 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_ppr32")],
            [InlineKeyboardButton("PEX 16 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_pex16")],
            [InlineKeyboardButton("Медь 15 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_copper15")],
            [InlineKeyboardButton("Канализация 50 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_sewer50")],
            [InlineKeyboardButton("Канализация 110 мм", callback_data="plumb_route_pipe_" + str(panel_id) + "_sewer110")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_routes_" + str(panel_id))],
        ]
        try:
            await query.edit_message_text(
                "📏 Новая трасса" + chr(10) + chr(10) + "Тип трубы:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_route_pipe_"):
        parts = data.replace("plumb_route_pipe_", "").rsplit("_", 1)
        panel_id = int(parts[0])
        pipe_type = parts[1]
        context.user_data['plumb_route_pipe'] = pipe_type
        context.user_data['waiting_for'] = 'plumb_route_length'
        try:
            await query.edit_message_text(
                "📏 Длина трассы (метры):" + chr(10) + chr(10) + "_Например: 8.5_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="plumb_routes_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("plumb_route_del_"):
        route_id = int(data.replace("plumb_route_del_", ""))
        try:
            import sqlite3
            from core.db import fetchone
            row = fetchone("SELECT panel_id FROM plumbing_routes WHERE id = ?", (route_id,))
            panel_id = row['panel_id'] if row else None
            core_plumbing.delete_route(route_id)
        except Exception as e:
            print("plumb route del: " + str(e), flush=True)
            panel_id = None
        if panel_id:
            try:
                await query.edit_message_text(
                    "Удалено",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К трассам", callback_data="plumb_routes_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_route_") and not data.startswith(("plumb_route_new_", "plumb_route_pipe_", "plumb_route_del_")):
        try:
            route_id = int(data.replace("plumb_route_", ""))
        except ValueError:
            return False
        try:
            from core.db import fetchone
            row = fetchone("SELECT * FROM plumbing_routes WHERE id = ?", (route_id,))
            r = dict(row) if row else None
        except Exception:
            r = None
        if not r:
            try:
                await query.edit_message_text("Трасса не найдена")
            except Exception:
                pass
            return True
        lines = ["📏 Трасса #" + str(route_id), ""]
        lines.append("Труба: " + core_plumbing.get_pipe_label(r.get('pipe_type')))
        lines.append("Длина: " + str(r.get('length_m') or 0) + " м")
        lines.append("Прокладка: " + str(r.get('route_type') or '—'))
        try:
            cost = core_plumbing.calc_route_cost(route_id)
            if cost:
                lines.append("")
                lines.append("Труба: " + str(cost.get('pipe_cost', 0)) + " ₽")
                lines.append("Расходники: " + str(cost.get('consumable_cost', 0)) + " ₽")
                lines.append("💰 Итого: " + str(cost.get('total', 0)) + " ₽")
        except Exception:
            pass
        kb_rows = [
            [InlineKeyboardButton("🗑 Удалить", callback_data="plumb_route_del_" + str(route_id))],
            [InlineKeyboardButton("⬅️ К трассам", callback_data="plumb_routes_" + str(r.get('panel_id')))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_points_"):
        panel_id = int(data.replace("plumb_points_", ""))
        try:
            text = core_plumbing.format_points_of_panel(panel_id)
        except Exception as e:
            print("plumb points: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Привязать точку", callback_data="plumb_point_add_" + str(panel_id))],
            [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
        ]))
        return True

    if data.startswith("plumb_point_add_"):
        panel_id = int(data.replace("plumb_point_add_", ""))
        p = core_plumbing.get_panel(panel_id)
        object_id = p.get("object_id") if p else None
        all_points = core_plumbing.get_available_plumb_points(object_id) if object_id else []
        used_ids = {pt["id"] for pt in core_plumbing.get_points_of_panel(panel_id)}
        free = [pt for pt in all_points if pt["id"] not in used_ids]
        if not free:
            text = "Свободных plumb-точек нет. Добавь точки в комнатах."
        else:
            text = "Выбери точку для привязки к коллектору:"
        kb_rows = []
        for pt in free[:15]:
            label = str(pt.get("room_name") or "?") + " · " + str(pt.get("comm_type") or "?")
            kb_rows.append([InlineKeyboardButton(label[:60], callback_data="plumb_point_set_" + str(panel_id) + "_" + str(pt["id"]))])
        kb_rows.append([InlineKeyboardButton("⬅️ К точкам", callback_data="plumb_points_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("plumb_point_set_"):
        rest = data.replace("plumb_point_set_", "")
        parts = rest.split("_", 1)
        panel_id = int(parts[0])
        point_id = int(parts[1])
        try:
            core_plumbing.assign_point_to_panel(point_id, panel_id)
        except Exception as e:
            print("plumb_point_set: " + str(e), flush=True)
        await handle_panels_callback(query, context, "plumb_points_" + str(panel_id))
        return True

    if data.startswith("plumb_point_unset_"):
        rest = data.replace("plumb_point_unset_", "")
        parts = rest.split("_", 1)
        panel_id = int(parts[0])
        point_id = int(parts[1])
        try:
            core_plumbing.unassign_point_from_panel(point_id, panel_id)
        except Exception as e:
            print("plumb_point_unset: " + str(e), flush=True)
        await handle_panels_callback(query, context, "plumb_points_" + str(panel_id))
        return True

    if data.startswith("plumb_water_"):
        object_id = int(data.replace("plumb_water_", ""))
        try:
            text = core_plumbing.format_water_summary(object_id)
        except Exception as e:
            print("plumb water: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Стояк", callback_data="plumb_add_type_" + str(object_id) + "_riser")],
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
        ]))
        return True

    if data.startswith("plumb_spec_"):
        panel_id = int(data.replace("plumb_spec_", ""))
        if export_plumbing_panel_spec is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_plumbing_panel_spec(panel_id)
            if not content:
                raise Exception("Пустая спецификация")
            target = os.path.join(tempfile.gettempdir(), "plumb_spec_" + str(panel_id) + ".txt")
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            p = core_plumbing.get_panel(panel_id)
            name = (p.get('name') if p else 'panel') or 'panel'
            with open(target, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=name + "_spec.txt",
                    caption="📄 Спецификация сантехники «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
                    ])
                )
        except Exception as e:
            print("plumb spec: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_csv_obj_"):
        object_id = int(data.replace("plumb_csv_obj_", ""))
        if export_plumbing_object_csv is None or save_estimate_csv is None:
            try:
                await query.edit_message_text("Модуль экспорта не загружен")
            except Exception:
                pass
            return True
        try:
            import tempfile, os
            content = export_plumbing_object_csv(object_id)
            if not content:
                raise Exception("Пустая смета")
            target = os.path.join(tempfile.gettempdir(), "plumb_obj_" + str(object_id) + ".csv")
            path = save_estimate_csv(content, path=target, prefix="plumb_obj")
            from modules.objects import get_object
            o = get_object(object_id)
            name = o['name'] if o else ('obj_' + str(object_id))
            with open(path, "rb") as f:
                await query.message.chat.send_document(
                    document=f,
                    filename=str(name) + "_plumb.csv",
                    caption="📊 Смета сантехники «" + str(name) + "»",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
        except Exception as e:
            print("plumb csv obj: " + str(e), flush=True)
            try:
                await query.edit_message_text(
                    "Ошибка: " + str(e),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("plumb_cost_obj_"):
        object_id = int(data.replace("plumb_cost_obj_", ""))
        try:
            text = core_plumbing.format_object_cost(object_id)
        except Exception as e:
            print("plumb cost obj: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К сантехнике", callback_data="plumb_list_" + str(object_id))],
        ]))
        return True

    if data.startswith("plumb_cost_"):
        panel_id = int(data.replace("plumb_cost_", ""))
        try:
            text = core_plumbing.format_panel_cost(panel_id)
        except Exception as e:
            print("plumb cost: " + str(e), flush=True)
            text = "Ошибка: " + str(e)
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "..."
        await _safe_edit(query, text, InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ К коллектору", callback_data="plumb_" + str(panel_id))],
        ]))
        return True

    if data.startswith("panel_auto_"):
        panel_id = int(data.replace("panel_auto_", ""))
        try:
            result = core_elec_panels.autocomplete_panel(panel_id)
        except Exception as e:
            print("panel auto: " + str(e), flush=True)
            result = None
        if not result:
            try:
                await query.edit_message_text(
                    "Не удалось автокомплектовать",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
            return True
        text = (
            "Автокомплектация выполнена" + chr(10) + chr(10) +
            "Создано компонентов: " + str(result.get('created', 0)) + chr(10) +
            "Ручных (сохранено): " + str(result.get('manual', 0)) + chr(10) +
            "Групп: " + str(result.get('groups', 0)) + chr(10) +
            "Нагрузка: " + str(result.get('total_watt', 0)) + " Вт" + chr(10) +
            "С K_одновр: " + str(result.get('calc_watt', 0)) + " Вт"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Комплектация", callback_data="panel_comp_" + str(panel_id))],
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_comp_price_"):
        comp_id = int(data.replace("panel_comp_price_", ""))
        context.user_data['component_price_id'] = comp_id
        context.user_data['waiting_for'] = 'component_price'
        try:
            await query.edit_message_text(
                "💰 Введи новую цену (₽):" + chr(10) + chr(10) + "_Например: 350_",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Отмена", callback_data="panel_comp_item_" + str(comp_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_comp_del_"):
        comp_id = int(data.replace("panel_comp_del_", ""))
        try:
            c = core_elec_panels.get_component(comp_id)
            panel_id = c.get('panel_id') if c else None
            if c:
                core_elec_panels.delete_component(comp_id)
        except Exception as e:
            print("panel comp del: " + str(e), flush=True)
            panel_id = None
        if panel_id:
            try:
                await query.edit_message_text(
                    "✅ Компонент удалён",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К комплектации", callback_data="panel_comp_" + str(panel_id))],
                    ])
                )
            except Exception:
                pass
        return True

    if data.startswith("panel_comp_item_"):
        comp_id = int(data.replace("panel_comp_item_", ""))
        try:
            c = core_elec_panels.get_component(comp_id)
        except Exception as e:
            print("panel comp item: " + str(e), flush=True)
            c = None
        if not c:
            try:
                await query.edit_message_text("Компонент не найден")
            except Exception:
                pass
            return True
        panel_id = c.get('panel_id')
        # Найти порядковый номер компонента среди всех компонентов щита
        try:
            all_comps = core_elec_panels.get_components(panel_id)
            idx = next((i for i, x in enumerate(all_comps, start=1) if x['id'] == comp_id), 0)
            total = len(all_comps)
        except Exception:
            idx = 0
            total = 0
        lines = ["🔧 Компонент " + str(idx) + " из " + str(total), ""]
        lines.append("Тип: " + str(c.get('component_type') or '?'))
        if c.get('component_model'):
            lines.append("Модель: " + str(c['component_model']))
        if c.get('rating'):
            lines.append("Номинал: " + str(c['rating']) + "А")
        if c.get('poles'):
            lines.append("Полюса: " + str(c['poles']) + "P")
        if c.get('curve'):
            lines.append("Кривая: " + str(c['curve']))
        if c.get('rcd_ma'):
            lines.append("УЗО: " + str(c['rcd_ma']) + "мА")
        if c.get('quantity'):
            lines.append("Количество: " + str(c['quantity']))
        if c.get('is_manual'):
            lines.append("Тип: [ручной]")
        lines.append("")
        try:
            price = core_elec_panels.calc_component_price(c)
        except Exception:
            price = 0
        unit_price = c.get('price_unit')
        if unit_price:
            lines.append("💰 Цена за шт: " + str(unit_price) + " ₽ [ручная]")
        lines.append("💰 Итого: " + str(price) + " ₽")
        kb_rows = [
            [InlineKeyboardButton("💰 Изменить цену", callback_data="panel_comp_price_" + str(comp_id))],
            [InlineKeyboardButton("🗑 Удалить", callback_data="panel_comp_del_" + str(comp_id))],
            [InlineKeyboardButton("⬅️ К комплектации", callback_data="panel_comp_" + str(panel_id))],
        ]
        await _safe_edit(query, chr(10).join(lines), InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_comp_"):
        panel_id = int(data.replace("panel_comp_", ""))
        try:
            comps = core_elec_panels.get_components(panel_id)
            text = core_elec_panels.format_panel_components(panel_id)
        except Exception as e:
            print("panel comp: " + str(e), flush=True)
            comps = []
            text = "Ошибка"
        if len(text) > 4000:
            text = text[:3900] + chr(10) + "... (обрезано)"
        kb_rows = []
        for idx, c in enumerate(comps, start=1):
            label = core_elec_panels.format_component(c)[:40]
            mark = " [ручной]" if c.get('is_manual') else ""
            num = str(idx) + ". "
            kb_rows.append([InlineKeyboardButton(
                num + label + mark,
                callback_data="panel_comp_item_" + str(c['id'])
            )])
            kb_rows.append([InlineKeyboardButton("➕ Добавить вручную", callback_data="panel_comp_add_" + str(panel_id))])
        kb_rows.append([InlineKeyboardButton("⬅️ К щиту", callback_data="panel_" + str(panel_id))])
        await _safe_edit(query, text, InlineKeyboardMarkup(kb_rows))
        return True

    if data.startswith("panel_stats_"):
        panel_id = int(data.replace("panel_stats_", ""))
        try:
            stats = core_elec_panels.get_panel_stats(panel_id)
        except Exception as e:
            print("panel stats: " + str(e), flush=True)
            stats = None
        if not stats:
            try:
                await query.edit_message_text("Ошибка статистики")
            except Exception:
                pass
            return True
        text = (
            "Статистика щита" + chr(10) + chr(10) +
            "Компонентов: " + str(stats.get('components_total', 0)) + chr(10) +
            "Модулей занято: " + str(stats.get('modules_used', 0)) + chr(10) +
            "Групп: " + str(stats.get('groups_count', 0)) + chr(10) +
            "Нагрузка: " + str(stats.get('total_load_watt', 0)) + " Вт"
        )
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("К щиту", callback_data="panel_" + str(panel_id))],
                ])
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_del_"):
        panel_id = int(data.replace("panel_del_", ""))
        try:
            p = core_elec_panels.get_panel(panel_id)
            object_id = p.get('object_id') if p else None
            core_elec_panels.delete_panel(panel_id)
        except Exception as e:
            print("panel del: " + str(e), flush=True)
            object_id = None
        if object_id:
            try:
                await query.edit_message_text(
                    "✅ Щит удалён",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ К щитам", callback_data="panels_list_" + str(object_id))],
                    ])
                )
            except Exception:
                pass
        return True

    # --- СОЗДАНИЕ ЩИТА: ШАГ 1 (тип) ---
    if data.startswith("panel_add_type_"):
        parts = data.replace("panel_add_type_", "").rsplit("_", 1)
        object_id = int(parts[0])
        ptype = parts[1]
        context.user_data['panel_new_object_id'] = object_id
        context.user_data['panel_new_type'] = ptype
        context.user_data['waiting_for'] = 'panel_new_name'
        type_labels = {
            'vru': 'ВРУ (вводно-распределительное)',
            'floor': 'Щит этажа',
            'apartment': 'Щит квартиры',
            'outdoor': 'Уличный щит',
        }
        tlabel = type_labels.get(ptype, ptype)
        kb_rows = [
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panels_list_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "⚡ Новый щит: " + tlabel + chr(10) + chr(10) +
                "Напиши название (например «Щит 1 этажа», «ВРУ на столбе»):",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_add_"):
        object_id = int(data.replace("panel_add_", ""))
        context.user_data['panel_new_object_id'] = object_id
        kb_rows = [
            [InlineKeyboardButton("🔌 ВРУ (ввод)", callback_data="panel_add_type_" + str(object_id) + "_vru")],
            [InlineKeyboardButton("⚡ Щит этажа", callback_data="panel_add_type_" + str(object_id) + "_floor")],
            [InlineKeyboardButton("🏢 Щит квартиры", callback_data="panel_add_type_" + str(object_id) + "_apartment")],
            [InlineKeyboardButton("🌳 Уличный щит", callback_data="panel_add_type_" + str(object_id) + "_outdoor")],
            [InlineKeyboardButton("⬅️ Отмена", callback_data="panels_list_" + str(object_id))],
        ]
        try:
            await query.edit_message_text(
                "⚡ Новый щит" + chr(10) + chr(10) + "Выбери тип:",
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception:
            pass
        return True

    if data.startswith("panel_"):
        panel_id = int(data.replace("panel_", ""))
        try:
            summary = core_elec_panels.get_panel_summary(panel_id)
        except Exception as e:
            print("panel card: " + str(e), flush=True)
            summary = None
        if not summary:
            try:
                await query.edit_message_text("Щит не найден")
            except Exception:
                pass
            return True
        p = summary['panel']
        ptype = core_elec_panels.get_panel_type_label(p.get('panel_type'))
        mount = core_elec_panels.get_mount_type_label(p.get('mount_type'))
        lines = ["⚡ *" + str(p.get('name') or '?') + "*", ""]
        lines.append("Тип: " + str(ptype))
        lines.append("Монтаж: " + str(mount))
        if p.get('input_breaker'):
            lines.append("Вводной: " + str(p['input_breaker']))
        if p.get('meter_type'):
            lines.append("Счётчик: " + str(p['meter_type']))
        lines.append("")
        lines.append("📋 Групп: " + str(summary['groups_count']))
        lines.append("📊 Нагрузка: " + str(summary['total_load_watt']) + " Вт")
        parent = summary.get('parent')
        if parent:
            lines.append("⬆️ Питается от: " + str(parent.get('name')))
        children = summary.get('children') or []
        if children:
            lines.append("⬇️ Питает: " + ", ".join(c.get('name') or '?' for c in children))
        kb_rows = []
        try:
            _children_count = len(core_elec_panels.get_child_panels(panel_id))
        except Exception:
            _children_count = 0
        if _children_count > 0:
            kb_rows.append([InlineKeyboardButton("⬇️ Дочерние щиты (" + str(_children_count) + ")", callback_data="panel_children_" + str(panel_id))])
        kb_rows.extend([
            [InlineKeyboardButton("🔌 Вводной автомат", callback_data="panel_input_" + str(panel_id))],
            [InlineKeyboardButton("🪄 Автокомплектация", callback_data="panel_auto_" + str(panel_id))],
            [InlineKeyboardButton("📏 Трассы щита", callback_data="panel_routes_" + str(panel_id))],
            [InlineKeyboardButton("🪄 Трассировать все группы", callback_data="panel_routes_auto_" + str(panel_id))],
            [InlineKeyboardButton("🔧 Смета монтажа", callback_data="panel_montage_" + str(panel_id))],
            [InlineKeyboardButton("💰 Общая смета щита", callback_data="panel_total_" + str(panel_id))],
            [InlineKeyboardButton("📄 Спецификация (TXT)", callback_data="panel_spec_" + str(panel_id))],
            [InlineKeyboardButton("📄 PDF-спецификация", callback_data="panel_pdf_" + str(panel_id))],
            [InlineKeyboardButton("📊 Смета (CSV)", callback_data="panel_est_csv_" + str(panel_id))],
            [InlineKeyboardButton("📋 Комплектация", callback_data="panel_comp_" + str(panel_id))],
            [InlineKeyboardButton("📊 Статистика", callback_data="panel_stats_" + str(panel_id))],
            [InlineKeyboardButton("📋 Группы щита", callback_data="panel_groups_" + str(panel_id))],
            [InlineKeyboardButton("🗑 Удалить щит", callback_data="panel_del_" + str(panel_id))],
            [InlineKeyboardButton("⬅️ К щитам", callback_data="panels_list_" + str(p.get('object_id')))],
        ])
        try:
            await query.edit_message_text(
                chr(10).join(lines),
                reply_markup=InlineKeyboardMarkup(kb_rows)
            )
        except Exception as e:
            print("panel card show: " + str(e), flush=True)
        return True

    return False
