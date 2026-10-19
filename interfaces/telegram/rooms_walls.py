"""interfaces/telegram/rooms_walls.py — обход стен, ниши, углы, проёмы."""
import os
import json
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Импорты core / modules
from core.rooms import get_rooms, get_room, create_room, delete_room, update_room
from core.rooms_ui import format_room_card, format_rooms_list
from core.measures import (
    get_measures, calculate_room_areas, format_measure, get_walls_ordered,
    add_measure, delete_measure,
    start_walls_round, complete_walls_round, get_walls_progress,
)
from core.openings import (
    add_opening, get_opening, get_openings, get_openings_by_wall,
    update_opening, delete_opening, format_opening, OPENING_TYPES,
)
from core.niches import (
    add_niche, get_niches, get_niches_by_room,
    update_niche, delete_niche, format_niche,
)
from core.sessions import ensure_session
from core.geometry import calc_wall_coords, check_closure
from core.db import fetchone, fetchall, commit as db_commit
from core import spec

DEFAULT_FLAGS = {"niche": False, "rounded": False, "wavy": False, "hidden": False}
try:
    from core import spec as core_spec
except Exception:
    core_spec = spec

# Локальный импорт rooms (чтобы не было цикла при загрузке)
def _get_rooms_helpers():
    from . import rooms as _r
    return _r



# ============================================================
# WALLS FUNCTIONS (вынесено из rooms.py)
# ============================================================

# Локальные хелперы из rooms.py (для избежания цикла)
def _get_rooms_helpers():
    from . import rooms as _r
    return _r

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




def _image_path(filename):
    """Путь к PNG-схеме."""
    if not filename:
        return None
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "docs", "images", filename)

async def _send_png_or_edit(query, caption, kb, png_filename=None):
    """Отправляет фото или редактирует сообщение."""
    png = _image_path(png_filename)
    chat_id = query.message.chat_id
    if png and os.path.exists(png):
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            with open(png, "rb") as f:
                await query.get_bot().send_photo(
                    chat_id=chat_id, photo=f, caption=caption,
                    parse_mode=ParseMode.MARKDOWN, reply_markup=kb
                )
            return
        except Exception as e:
            print(f"⚠️ send_photo: {e}", flush=True)
        try:
            await query.get_bot().send_message(
                chat_id=chat_id, text=caption,
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
            return
        except Exception as e:
            print(f"⚠️ send_message fallback: {e}", flush=True)
        return
    msg = query.message
    is_photo = bool(getattr(msg, "photo", None))
    try:
        if is_photo:
            await query.edit_message_caption(caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        else:
            await query.edit_message_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    except Exception as e:
        err = str(e).lower()
        if "message is not modified" in err:
            return
        print(f"⚠️ _send_png_or_edit edit failed: {e}", flush=True)

async def _send_png_or_reply(message, caption, kb=None, png_filename=None):
    """Отправляет фото или текст (для update.message)."""
    png = _image_path(png_filename)
    if png and os.path.exists(png):
        try:
            with open(png, "rb") as f:
                await message.reply_photo(photo=f, caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            return
        except Exception as e:
            print(f"⚠️ reply_photo: {e}", flush=True)
    await message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

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
    return core_spec.get_wall_name(state.get('step_num') or 1, core_spec.get_total_walls())



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



async def _show_wall_step(query, context, room_id, step, phase='flags', use_photo=False):
    """Экран галочек стены.

    use_photo=True — только при первом входе на стену (отправка фото).
    use_photo=False — при обновлении галочек (просто edit_message_text, БЕЗ мигания).
    """
    state = _get_wall_state(context)
    state['step_num'] = step
    state['step_name'] = phase
    _save_wall_draft(context, room_id)

    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
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

    spec_step = spec.get_wall_step('plane', n=step, pos=core_spec.get_wall_name(step, core_spec.get_total_walls()))
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
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())

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
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
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

    spec_step = spec.get_wall_step('angle', n=step, pos=core_spec.get_wall_name(step, core_spec.get_total_walls()), length=length_cm)
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
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
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
    next_step = step + 1 if step < core_spec.get_total_walls() else 1
    _reset_wall_state(context, keep_step_num=next_step)

    summary = f"✅ *Стена {step} ({pos}) сохранена!*\n\n📏 Длина: {length} см\n📐 Угол: {angle}°"
    if niches:
        summary += f"\n🕳 Нишей: {len(niches)}"

    if step >= core_spec.get_total_walls():
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
        if step >= core_spec.get_total_walls():
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
    if progress['walls_count'] >= core_spec.get_total_walls():
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



async def _wall_round_open_start(query, context, room_id, opening_type):
    """Старт добавления проёма при обходе."""
    state = _get_wall_state(context)
    step = state.get('step_num') or 1
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
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
        pos = core_spec.get_wall_name(step_num, core_spec.get_total_walls())
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
        pos = core_spec.get_wall_name(step_num, core_spec.get_total_walls())
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
        pos = core_spec.get_wall_name(step_num, core_spec.get_total_walls())
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
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
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
    next_step = step + 1 if step < core_spec.get_total_walls() else 1
    _reset_wall_state(context, keep_step_num=next_step)

    summary = f"✅ *Стена {step} ({pos}) сохранена!*\n\n📏 Длина: {length} см\n📐 Угол: {angle}°"
    if niches: summary += f"\n🕳 Нишей: {len(niches)}"

    if step >= core_spec.get_total_walls():
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
    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
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

    pos = core_spec.get_wall_name(step, core_spec.get_total_walls())
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

