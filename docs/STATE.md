# STATE — где мы сейчас

> Дата: 2026-10-19. Сессия: 20 (закрыта). HEAD: fe1ad91.

---

## 0. СЕССИЯ 20 — РЕФАКТОРИНГ _legacy.py + ФИКС ПАРСЕРА + АУДИТ rooms.py (19.10.2026)

### 0.0 ИТОГ СЕССИИ 20 (13 коммитов)
- `_legacy.py` 487 → 360 (−127).
- `text/parse.py` — новый (135 строк, 10 actions).
- Баг «материалы → еда» — `fe1ad91`.
- Дубль `update_object_status` — `57c34d5`.
- Парсер `add_task` («ноая») — `6bad254`.
- `digest.py` МСК — `13061d6`.
- Доки (STATE/WORKPLAN/ROADMAP) — `36dfa57`.

### 0.0.1 АУДИТ rooms.py (начало плана)
- `rooms.py` — 7638 строк, God Object.
- **Найдены 2 мёртвые функции:** `_after_niches` (1697), `_show_niche_top_width_from_update` (2181). **Удалить в сессии 21.**
- **`handle_measure_input` (5126)** — ЖИВАЯ (вызывается из `_legacy.py:301`).
- **План разбора:** `rooms/walls.py` (~2000), `rooms/comm.py` (~300), `rooms/floors.py` (~300), `rooms/elec.py` (~500), `rooms/openings.py` (~300), `rooms/reports.py` (~300), `rooms/measure.py` (~300).
- **Оценка:** 25–35 часов (10–15 сессий).
- **Старт:** `rooms/walls.py` — сессия 21.



### 0.1 Итоги сессии 20

**8 коммитов, `_legacy.py` 487 → 360 (−127 строк). Создан `text/parse.py` (135 строк, все 10 actions). Баг парсера «материалы → еда» закрыт.**

| # | Действие | Коммит | Результат |
|---|---|---|---|
| 1 | `bo72.db` → `.gitignore` | `82345a8` | БД не в git |
| 2 | Удалён дубль-роутер `_try_objects_cb` | `68fccc6` | −4 строки |
| 3 | Удалён висячий `# УТОЧНЕНИЕ ОБЪЕКТА` | `e7ae107` | −1 строка |
| 4 | `text/parse.py` — 2 actions | `d08ead0` | _legacy 464 |
| 5 | `text/parse.py` — +2 actions | `e2b97bf` | _legacy 430 |
| 6 | `text/parse.py` — +6 actions | `4c2b2ec` | _legacy 375 |
| 7 | Чистка _legacy: 22 мёртвых импорта | `ed41bd0` | _legacy 360 |
| 8 | Фикс бага «материалы → еда» | `fe1ad91` | категория работает |
| 9 | Удалён дубль `update_object_status` | `57c34d5` | −9 строк |
| 10 | Парсер `add_task`: «ноая», «задачу», пробелы | `6bad254` | title чистый |
| 11 | `digest.py`: МСК-часовой пояс (4 места) | `13061d6` | date.today() → MSK |
| 12 | Обновлены STATE / HANDOFF / CODE_MAP | `edb2234`, `0d0c8bd` | — |

### 0.2 TODO на сессию 21

1. **`rooms.py` (7638)** — God Object. Резать постепенно (P2 в WORKPLAN, высокий риск).
2. **`wall_niche_count_`** — callback не доходит (баг Этапа 1.7, последний из 5).
3. **`check_object_vs_comms` — единицы (м vs см)** — ОТЛОЖЕНО. Причина: нет единого стандарта единиц в БД (`length/height/offset_y` — REAL без unit). Требует архитектурного решения (миграция с `unit`, нормализация). Не «баг на 15 минут».
4. **`HANDOFF.md` (Хераборина)** — обновить под X-6.
5. **`modules/parser.py`** — проверить остальные категории (еда, инструмент → «прочее»?).

### 0.3 ГРАБЛИ СЕССИИ 20

1. **regex по всему файлу опасен** — съедает границы функций. Для удаления — только `sed -i` по номерам.
2. **sed с `
` в replacement** — не работает для вложенных отступов. Используй `python3` + `splitlines()`.
3. **`OLD_NOT_FOUND`** — всегда `sed -n 'X,Yp' | cat -A` перед патчем (видеть `
`, отступы, пробелы).
4. **Двойной парсинг** (`parse_message` и в `parse.py`, и в `_legacy.py`) — пока есть, но `_legacy.py` уходит в fallback только если `parse.py` вернул `False`. Убрать после того, как все actions уйдут в `parse.py`.

---

## 0. СЕССИЯ 19 — ГИГИЕНА РЕПО + ФИЛЬТР СКАНЕРА (16.10.2026)

### 0.1 Удаление tracked-бэкапов

- 6 файлов через `git rm`: `backups/rooms_pre_1_*` (2), `core/measures.py.crashed_*`,
  `handlers/commands.py.before_fix_*`, `handlers/commands.py.broken_*`,
  `interfaces/telegram/rooms.py.crashed_*`.
- Коммит: `ddc9718`.

### 0.2 .gitignore +6 масок

Добавлено: `*_pre_1_*`, `*.before_*`, `*.broken_*`, `*.crashed_*`, `*.v1`, `backups/`.
Коммит: `b98d02d`.

### 0.3 Удаление .v1 (tracked) + 195 untracked-бэкапов

- `handlers/commands.py.v1` и `modules/parser.py.v1` — были **tracked** (не попали в первый grep).
- Удалено 195 untracked-бэкапов с диска через `find ... -delete`.
- Коммит: `de249e7`.

### 0.4 tools/map_scan.py — фильтр бэкапов

- Строка 28: расширена проверка `if any(s in py.name for s in (".bak", "_pre_1_", ".before_", ".broken_", ".crashed_", ".v1"))`.
- `CODE_MAP_AUTO.md`: 428 → 417 строк, 379 префиксов, 0 дыр.
- Коммит: `341e747`.

### 0.5 ГРАБЛИ СЕССИИ 19

1. **venv/bin/python3 bot.py** — обязательно. Системный `python3` → `ModuleNotFoundError: reportlab`.
2. **`.v1` не был в первом grep** (маска не включала) → сюрприз в `git status` после удаления.
3. **nohup без setsid** — логи бота сыпятся в Shell, приглашение зависает. Решение: `setsid ... < /dev/null &`.

### 0.6 TODO на сессию 20

1. **rooms.py** (7638 строк) — God Object. Резать постепенно.
2. **Домен marketplaces** — расширить (Ozon, WB, Леруа).
3. **`009_contracts.sql.bak`** — восстановить из git history или подтвердить ненужность.
4. **`M bo72.db`** — решить: убрать БД из git / добавить в .gitignore.
5. **Прочие TODO** — см. ROADMAP этапы 2-3.

---

## 0. СЕССИЯ 18 — ЧТО СДЕЛАНО

### 0.1 Fallback вынесен в text/fallback.py

- Строки 595–653 из _legacy.py → text/fallback.py
- Функция: `async def try_handle(update, context, text) -> bool`
- Удалены 2 debug-принта (UNKNOWN)
- Коммит: `9ab3b33`

### 0.2 est_bykind / est_kind_ перенесены в estimates.py

- Блок est_bykind + est_kind_ из _legacy.py → try_handle в callbacks/estimates.py
- Вставлен перед финальным return False (на уровне try_handle, отступ 4)
- **Грабли:** при неверном отступе (8 вместо 4) блок попадает внутрь `if est_cmp_b_` — не срабатывает
- Коммит: `524b5b8`

### 0.3 Создана авто-карта кода

- `tools/map_scan.py` — сканер колбэков и роутеров
- `docs/CODE_MAP_AUTO.md` — авто-карта (428 строк)
- Реестр: 375 callback-префиксов, 8 роутеров, 8 text-доменов
- **Найдено 2 «дыры»:** recognize_receipt (реальный баг), choose_obj_add_task (артефакт f-строки)

### 0.4 Метрики сессии 18

| Файл | Начало 18 | Сейчас |
|---|---|---|
| _legacy.py | 656 | 555 |
| estimates.py | 1252 | 1299 |
| text/fallback.py | — | создан |
| tools/map_scan.py | — | создан |
| docs/CODE_MAP_AUTO.md | — | 428 строк |

Удалено ~20 debug-принтов.

### 0.5 ИТОГИ сессии 18 (10 коммитов)

| # | Задача | Статус | Коммит |
|---|---|---|---|
| 1 | recognize_receipt не подключён | ✅ работает через bot.py | — |
| 2 | Дубли `_try_estimates_cb` (3→1) | ✅ | cfb2af3 |
| 3 | Русификация object_kind/status | ✅ | 12d629b |
| 4 | est_import → marketplaces | ✅ | 90f42e4 |
| 5 | fallback → text/fallback.py | ✅ | 9ab3b33 |
| 6 | est_bykind → estimates.py | ✅ | 524b5b8 |
| 7 | map_scan.py + lint_routers.py | ✅ | b76a99f, 0c20083, 63c2fdb |
| 8 | AI_INSTRUCTIONS.md | ✅ | 1f758eb |

### 0.6 TODO на сессию 19

1. **rooms.py** (7638 строк) — God Object. Резать постепенно.
2. **Сканер (косметика):** не выделять f-строки-артефакты отдельными префиксами.
3. **Домен marketplaces** — расширить (Ozon, WB, Леруа: парсинг цен, автообновление).
4. **`duplicate_if`** в estimates.py — не баг (общий + специфичный префикс).
5. **Прочие TODO** — см. ROADMAP этапы 2-3.

---

## 1. СЕССИЯ 17 — ЧТО СДЕЛАНО

### 1.1 callbacks/ — 8 файлов

- tasks.py (164)
- estimates.py (~700)
- kpi.py (79)
- finance.py (~180)
- objects.py (163)
- reports.py (118)
- misc.py (62)
- personal.py (99)

### 1.2 text/ — новый пакет (7 файлов)

- objects.py (30) — new_object
- tasks.py (100) — setdate_task, rename_task, new_task_text
- finances.py (81) — new_expense_text
- personal.py (48) — personal_expense_text
- crm.py (348) — crm_*, activity_*
- misc.py (154) — room_rename, obj_rename, panel_comp_rating, task_progress, приветствия
- rooms.py (39) — room_name, wall_question

Паттерн: async def try_handle(update, context, text) -> bool

### 1.3 Метрики

| Файл | Начало 17 | Сейчас |
|---|---|---|
| _legacy.py | 1625 | 656 |
| Дельта | — | −60% |

Удалено ~15 debug-принтов.

---

## 2. КОММИТЫ СЕССИИ 17 (15.10.2026)

- e556625 — exp_type_object_ → objects.py
- 5b7a4e3 — new_object → text/objects.py
- 3b1a959 — setdate_task + rename_task → text/tasks.py
- ab48e7c — parse_amount в finances & personal
- abccbc9 — CRM → text/crm.py
- 3418ac9 — misc domain
- 14ad561 — bare returns + dup router fix
- 881e4e6 — rooms domain (HEAD)
- e68db11 — objects (callbacks)
- 7dda2e9 — reports (callbacks)
- b3cc223 — restore menu_reports
- 9a17111 — misc (callbacks)

---

## 3. ЧТО ОСТАЛОСЬ В _legacy.py (~656 строк)

- handle_callback (роутеры) — ~320
- handle_text: parse_message + старая логика — ~115
- Умный fallback — ~60
- Уточнение объекта — ~10
- Служебное

---

## 4. ГРАБЛИ СЕССИИ 17

### 4.1 Локальные импорты внутри функций
При выносе блока — все импорты, что были внутри функций, остаются внутри. Без импорта в шапке — NameError.

**Решение:** AST-проверка после каждого выноса.

### 4.2 Голые return вместо return True
Голый `return` возвращает None. `if await try_handle():` не сработает → fallback вызывается ещё раз → «задвоение».

**Решение:** regex `re.sub(r'^(\s+)return$', r'\1return True', c, flags=re.MULTILINE)`

### 4.3 Дубли роутеров
Если добавить второй вызов try_handle для того же домена — блок сработает дважды.

**Решение:** grep по `_try_..._cb` перед вставкой.

### 4.4 Плавающие номера строк
После каждого выноса номера сдвигаются. Всегда свежий grep/sed перед патчем.

---

## 5. ПРАВИЛА (обновлено)

- Один патч → py_compile → рестарт → тест → коммит.
- Перед патчем — свежий grep + sed.
- Порядок патча: бэкап → create new file → правка _legacy.py → py_compile → AST → test.
- AST-проверка импортов — обязательна.
- Regex return → return True — обязательна.
- После выноса — grep на дубли роутеров.

---

## 6. ПРОЕКТЫ РЯДОМ

### Хераборина (worklog-app/)
- Репо: github.com/masterboplus-netizen/worklog
- Хостинг: https://masterboplus-netizen.github.io/worklog/
- Стек: HTML/CSS/JS + AES-256-GCM + Service Worker (PWA)
- PIN: 201186 (не в git!)
- Данные: worklog.json → encrypt.py → data.encrypted.json

Функции:
- Дашборд: время + сообщения + скрины + метрики
- Дневник: сессии по датам
- Проекты: 11 фаз с прогресс-барами, раскрытие
- Baseline: 336ч с июля
- Gap-правило: 15 минут

## 7. СЛЕДУЮЩИЕ ШАГИ

1. Доделать _legacy.py — fallback, parse_message, уборка (~200 строк).
2. rooms.py (7638 строк) — God Object, большой рефакторинг.
3. modules/ → core/ — 176 импортов через шим.
4. Универсальный приёмник файлов (handle_document).
5. Редизайн Хераборины — графики, аналитика, месяцы.

## 8. ОТКАТ (шпаргалка)

- git checkout path/to/file.py — откат файла.
- cp file.py.bak_NAME file.py — из бэкапа.
- Бэкапы в handlers/commands/_legacy.py.bak_*.

## 9. СТРУКТУРА handlers/commands/

### callbacks/ — 8 файлов
tasks.py, estimates.py, kpi.py, finance.py, objects.py, reports.py, misc.py, personal.py.

### text/ — 7 файлов
objects.py, tasks.py, finances.py, personal.py, crm.py, misc.py, rooms.py.

### _legacy.py — 656 строк (было 1625)

## 10. ПРОВЕРЕННЫЕ ИНСТРУМЕНТЫ

- AST-проверка импортов (после каждого выноса).
- Regex: return → return True (обязательно).
- Grep на дубли роутеров: grep "_try_" _legacy.py.
- Cache-bust для Хераборины: index.html ?v=N.

---

Конец STATE.md (обновлён 2026-10-15, сессия 17)

---

## 🏛️ АРХИТЕКТУРА ПАКЕТА `rooms/` (решение сессии 20)

**Проблема:** `rooms.py` — 7904 строки, God Object. Нарушает Манифест (Этапы 5–7: API, Web, Mobile).

**Решение — 4 слоя:**
1. **`rooms/_helpers.py`** — общие UI-хелперы (`_safe_edit`, `_send_png_or_edit`, `_image_path`).
2. **`rooms/core.py`** — каркас (`handle_rooms_callback`, `show_rooms_list`, `show_room_card`).
3. **`rooms/*.py`** — домены (`walls`, `comm`, `openings`, `floors`, `elec`, `plumbing`, `works`, `reports`).
4. **`core/rooms_logic/`** (сессия 22+) — бизнес-логика без Telegram (для Web, Mobile).

**Правило выноса:** `_helpers` → `core` → `walls` → `comm` → `openings` → `floors` → `elec` → `plumbing` → `works` → `reports` → `core/rooms_logic`.
