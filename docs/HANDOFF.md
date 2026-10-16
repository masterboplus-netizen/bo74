# HANDOFF — как войти в проект «Бо 8.1»

> Для нового чата с AI. Прочитай ПЕРВЫМ.
>
> **⚠️ СНАЧАЛА ПРОЧТИ:** `docs/AI_INSTRUCTIONS.md`
> Там — правила, Хераборина (учёт времени), грабли, инструменты.
> Без него ты будешь задавать Andrey тупые вопросы и он взбесится.
> Дата: 2026-10-16. Сессия: 19 (закрыта).

---

## 1. ЧТО ЭТО

«Бо 8.1» — цифровая экосистема для строительной компании. Telegram-бот + SQLite + Python 3.13.
Стек: python-telegram-bot[job-queue], APScheduler, reportlab, openpyxl, rapidfuzz.
Запуск: `venv/bin/python3 bot.py` (системный python3 → ModuleNotFoundError: reportlab).
Andrey — автор, работает с мобилы через Replit Shell + VPN, скрин = 40 строк.
AI — ведёт патчи, следит за архитектурой, разбивает God Objects.

---

## 1.1. КАРТА КОДА (ЧИТАТЬ ПЕРЕД ЗАДАЧЕЙ)

**Файл:** `docs/CODE_MAP_AUTO.md` — авто-карта, **не редактировать руками**.

**Обновление:** `python3 tools/map_scan.py > docs/CODE_MAP_AUTO.md`

**Что внутри:**
- Роутеры `callbacks/*` (у каждого 1 `try_handle`).
- Text-домены `text/*`.
- **⚠️ Кнопки без обработчика** — потенциальные баги.
- **Реестр callback_data** (~375 префиксов): где формируется кнопка, где обрабатывается.

**Правило:** перед любой задачей — обновить карту, найти нужный префикс, понять куда идти.

---

## 2. ПРАВИЛА (ЖЁСТКО)

- Один патч → один py_compile → один скрин → один тест → один коммит.
- НЕ давать 2+ команд в одном сообщении, если могут упасть.
- Номера строк УСТАРЕВАЮТ после каждого патча. Перед патчем — ВСЕГДА свежий grep -n.
- Перед рискованным патчем — cp file file.bak_ИМЯ_$(date).
- Если OLD_NOT_FOUND — не гадать, прислать sed -n + cat -A.
- 30 минут без движения → СТОП, откат, читаем STATE.md.
- git checkout — наш бэкап.
- Максимум 3 вопроса за раз.
- Перед патчем с отступами — python3 tools/show_structure.py <file> <from> <to>.
- **После выноса — AST-проверка импортов.**
- **После выноса — regex `return` → `return True`.**
- **После выноса — grep на дубли роутеров.**

---

## 3. ГДЕ МЫ (сессия 19, 16.10.2026)

HEAD: 341e747 — fix(map_scan): skip backup artifacts + regenerate map.

### Рефакторинг завершён:

**callbacks/** — 8 файлов (tasks, estimates, kpi, finance, objects, reports, misc, personal).

**text/** — 8 файлов (objects, tasks, finances, personal, crm, misc, rooms, fallback).

**Гигиена репо (сессия 19):**
- Удалено 8 tracked-бэкапов (crashed, broken, before_fix, pre_1, .v1) — коммиты ddc9718, de249e7.
- Удалено 195 untracked-бэкапов с диска.
- .gitignore +6 масок (b98d02d): *_pre_1_*, *.before_*, *.broken_*, *.crashed_*, *.v1, backups/.
- tools/map_scan.py: фильтр бэкапов (341e747).

**Метрики:**
- _legacy.py: 601 → 487.
- text/fallback.py: создан (fallback вынесен).
- estimates.py: 1252 → 1299 (est_bykind/est_kind_ перенесены).
- tools/map_scan.py: обновлён (фильтр бэкапов).
- docs/CODE_MAP_AUTO.md: 417 строк (было 428).
- Найдено 379 callback-префиксов, 0 «дыр».
- callbacks/marketplaces.py: создан (est_import вынесен).

---

## 4. ТЕХДОЛГ

A. _legacy.py — осталось ~200 строк (fallback, parse_message, уборка).
B. rooms.py (7638) — следующий God Object.
C. modules/ → core/ (176 импортов) через шим.
D. Универсальный приёмник файлов (handle_document).

---

## 5. ГЛАВНЫЕ ГРАБЛИ

1. **UnboundLocalError** от локальных from modules.X import Y внутри функций.
2. **Голый `return`** вместо `return True` → задвоение.
3. **Дубли роутеров** — если добавить второй вызов try_handle.
4. **Плавающие номера строк** после каждого выноса.

---

## 6. АРХИТЕКТУРНЫЕ ПРИНЦИПЫ

- Один патч — одно изменение.
- Модуль = домен.
- Реэкспорт через __init__.py.
- Минимум правок в bot.py.
- God Objects резать постепенно.
- _legacy.py — временное.
- Тест вручную после каждого патча.
- Коммит после каждого успешного патча.

---

## 7. СТРУКТУРА handlers/commands/

- _legacy.py (656 строк) — handle_callback + handle_text.
- callbacks/ — 8 файлов (callback-роутеры).
- text/ — 7 файлов (text-роутеры).
- Прочее: start.py, personal.py, receipt.py, photos.py, crm.py, finance.py, objects.py, tasks.py, choose_expense.py, document.py, keyboards.py, add_menu.py, utils.py.

---

## 8. ПРОЕКТЫ РЯДОМ

### Хераборина (worklog-app/) — отдельный репо
- URL: https://masterboplus-netizen.github.io/worklog/
- PIN: 201186 (не в git!)
- Данные: worklog.json → encrypt.py → data.encrypted.json.
- Baseline: 336ч с июля.
- Gap-правило: 15 минут.

---

## 9. ПЕРВЫЙ ПАТЧ НОВОГО AI

1. Прочитай HANDOFF.md, STATE.md, BO_MANIFEST.md.
2. Спроси Andrey: какая задача?
3. Свежий grep -n или show_structure.py.
4. Бэкап.
5. Патч одной командой.
6. py_compile + AST + grep на дубли.
7. Перезапуск.
8. Тест.
9. Коммит.
10. Если сломалось — git checkout.

---

## 10. КОММИТЫ сессии 17

26 коммитов, всё на GitHub. См. docs/STATE.md.

---

## 11. ЧТО ДАЛЬШЕ

1. _legacy.py — fallback, parse_message (~200 строк).
2. rooms.py (7638) — God Object.
3. modules/ → core/.
4. Универсальный приёмник файлов.
5. Редизайн Хераборины (графики, аналитика).

---

Готов. Погнали.
