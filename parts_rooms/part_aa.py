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

WALL_NAMES = core_spec.WALL_NAMES
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
