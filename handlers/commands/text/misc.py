"""Text-хендлеры misc-домена (сессия 17).

Вынесено из handlers/commands/_legacy.py (handle_text).
Блоки: room_rename, obj_rename, panel_comp_rating, task_progress_*.

Роутер try_handle(update, context, text) -> bool.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import get_connection


async def try_handle(update, context, text: str) -> bool:
    """Обрабатывает misc text-команды. True = обработано."""

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
            return True

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
            return True

    if context.user_data.get("waiting_for") == "panel_comp_rating":
        from core import elec_panels as core_elec_panels
        panel_id = context.user_data.get("panel_comp_panel_id")
        ctype = context.user_data.get("panel_comp_type")
        text_in = text.strip()
        if not panel_id or not ctype:
            await update.message.reply_text("Потерялись данные. Начни заново.")
            context.user_data["waiting_for"] = None
            return True
        try:
                import re as _re
                _m = _re.search(r"[0-9]+", text_in)
                if _m is None:
                    await update.message.reply_text("Не нашёл число. Введи номинал, например 16:")
                    return True
                rating = int(_m.group())
        except ValueError:
            await update.message.reply_text("Нужно число, например 16. Попробуй ещё раз.")
            return True
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
        return True

    # Дневник работ — шаг 1: часы
    if context.user_data.get("waiting_for") == "task_progress_hours":
        try:
            _h = float((text or "").strip().replace(",", "."))
        except ValueError:
            await update.message.reply_text("⚠️ Нужно число. Сколько часов? Например: 8")
            return True
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
        return True

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
        return True

    return False
