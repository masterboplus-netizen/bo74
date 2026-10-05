# 🏗️ ARCHITECTURE.md — Архитектура Бо

> Версия: 1.0
> Дата: 2026-10-02

---

## 0. ГЛАВНЫЙ ПРИНЦИП

**Ядро независимо от интерфейсов.** Бот, веб, мобильное — все обращаются к ядру через одни и те же функции. Ядро ничего не знает про Telegram.

---

## 1. СЛОИ

ИНТЕРФЕЙСЫ (UI): Telegram, Web, Mobile, Tablet, API
        ↓ (вызовы ядра)
ЯДРО (CORE): spec, geometry, model_3d, sessions, rooms, measures, openings, niches, comms, materials, estimates, economics, tasks, crm, finance, hr
        ↓ (SQL)
БД (SQLite): objects, rooms, measures, sessions, ...
        ↓ (интеграции)
ВНЕШНИЕ СИСТЕМЫ: 1С, МойСклад, Банки, CAD, AI

---

## 2. ЯДРО — МОДУЛИ

### 2.1. Базовые

**db.py** — обёртка над SQLite.
fetchone, fetchall, commit.

**spec.py** — справочник.
Тексты шагов, картинки, типы, валидации.
get_step_spec(), get_image_path().

### 2.2. Геометрия

**geometry.py** — расчёты.
calc_wall_coords() — координаты стен.
check_closure() — замыкание контура.
wall_offset_to_world() — 2D в 3D.

**model_3d.py** — модель комнаты.
get_room_model() — единый объект.
get_room_areas() — площади.

### 2.3. Замеры

**sessions.py** — сессии замеров.
create_session(), get_active_session().

**rooms.py** — комнаты.
**measures.py** — замеры (стены, пол, потолок).
**openings.py** — проёмы.
**niches.py** — ниши.
**comms.py** — коммуникации.

### 2.4. Экономика

**materials.py** — материалы.
**estimates.py** — сметы.
**works.py** — виды работ.
**stages.py** — этапы.
**economics.py** — маржа, P&L, налоги.

### 2.5. Управление

**objects.py** — объекты.
**tasks.py** — задачи.
**crm.py** — CRM.
**finance.py** — финансы.
**hr.py** — HR, KPI.

### 2.6. Служебные

**history.py** — история.
**conflicts.py** — конфликты.
**room_objects.py** — мебель/техника.

### 2.7. Экспорт

export/json_export.py
export/dxf_export.py
export/csv_export.py
export/pdf_export.py
export/ifc_export.py

---

## 3. ИНТЕРФЕЙСЫ

### 3.1. Telegram

interfaces/telegram/rooms.py — UI комнат.
interfaces/telegram/export.py — UI экспорта.
interfaces/telegram/comms.py — UI коммуникаций.
interfaces/telegram/tasks.py — UI задач.

### 3.2. Web

interfaces/web/app.py — Flask/FastAPI.
interfaces/web/templates/ — Jinja2.
interfaces/web/static/ — CSS/JS.

### 3.3. Mobile

interfaces/mobile/ — Flutter.

### 3.4. Tablet

interfaces/tablet/ — Flutter (большая версия).

### 3.5. API

interfaces/api/ — REST API для внешних.


---

## 4. ОБРАБОТЧИКИ (Telegram)

### 4.1. Команды

handlers/commands.py — все команды.
handlers/onboarding.py — роли.
handlers/admin.py — админ.
handlers/digest_cmd.py — дайджесты.

### 4.2. Порядок регистрации (КРИТИЧНО)

1. CommandHandler — команды.
2. MessageHandler(PHOTO) — фото.
3. MessageHandler(TEXT) — текст.
4. CallbackQueryHandler — специфичные.
5. CallbackQueryHandler(handle_rooms_callback) — комнаты.
6. CallbackQueryHandler(handle_callback) — универсальный.

**Правило:** специфичные — раньше универсальных.

---

## 5. ИНТЕГРАЦИИ

### 5.1. Учёт
1С — XML, JSON.
МойСклад — API.

### 5.2. Банки
Сбербанк — API.
Тинькофф — API.

### 5.3. CAD
DXF (AutoCAD).
IFC (Revit).
SKP (SketchUp).

### 5.4. AI
Whisper — голос.
Yandex Vision — OCR.
GPT — помощник.

---

## 6. АНАЛИТИКА

analytics/dashboards.py — дашборды.
analytics/reports.py — отчёты.
analytics/forecasts.py — прогнозы.

---

## 7. ПОТОКИ ДАННЫХ

### 7.1. Замер комнаты

Пользователь → Бот → handle_rooms_callback → _show_wall_* → context.user_data → _save_wall_draft → БД (wall_drafts) → Продолжение или сохранение → БД (room_measures).

### 7.2. Экспорт комнаты

Пользователь → Бот → export.py → core/model_3d.get_room_model → core/export/json_export → файл → Telegram.

### 7.3. Смета

Пользователь → Бот → estimates.py → get_room_areas → work_types × prices → Расчёт → БД (estimates).

### 7.4. Отчёт для заказчика

Заказчик → Веб → reports.py → Сбор данных → Рендер → HTML.

---

## 8. ФАЙЛОВАЯ СТРУКТУРА

bo_ecosystem/
├── core/
│   ├── db.py, spec.py, geometry.py, model_3d.py
│   ├── sessions.py, rooms.py, measures.py
│   ├── openings.py, niches.py, comms.py
│   ├── materials.py, estimates.py, works.py, stages.py
│   ├── objects.py, tasks.py, crm.py, finance.py
│   ├── economics.py, hr.py
│   ├── history.py, conflicts.py, room_objects.py
│   ├── export/
│   └── api/
├── interfaces/
│   ├── telegram/, web/, mobile/, tablet/
├── handlers/
│   ├── commands.py, onboarding.py, admin.py, digest_cmd.py
├── modules/
│   ├── objects.py, tasks.py, finance.py, users.py
│   ├── personal.py, parser.py, crm.py, digest.py
│   ├── kpi.py, reports.py, ocr.py, calendar.py
│   └── backup_db.py, dashboard_link.py, phone_utils.py
├── integrations/, analytics/, public/, billing/, security/
├── data/, docs/, migrations/, tests/, scripts/
├── bot.py, web.py, config.py, requirements.txt

---

## 9. ПРАВИЛА АРХИТЕКТУРЫ

1. Ядро независимо — не знает про Telegram.
2. Никаких магических строк — всё из spec.py.
3. Никаких дублей — одна функция, одно место.
4. Один вход — один выход — в handle_measure_input.
5. Специфичные callback раньше универсальных.
6. Черновики в БД — для восстановления.
7. Бэкап перед любой миграцией.
8. Проверка синтаксиса после правки.
9. Коммит с понятным сообщением.
10. Тесты перед push в main.

---

*Конец ARCHITECTURE.md*
## 10. ЯДРО ЭОМ (расширение, сессия 2)

### core/elec.py (базовый)
- Питание объекта (legacy) — set_supply, get_supply
- Группы — create_group, get_groups, get_groups_by_floor, get_groups_by_room
- Привязка точек — assign_comm_to_group, unassign_point_from_group
- Расчёты — calc_current, pick_breaker, pick_cable, auto_fill_group
- Фазы L1/L2/L3 — calc_balance, auto_pick_phase, assign_phases_by_load
- Формат — format_group, format_elec_full, format_phase_distribution
- Кухня — get_kitchen_equipment, create_kitchen_group
- Кабели — add_cable, get_cables_by_object, get_cables_by_group, get_cable_summary

### core/elec_panels.py (новый)
- Щиты — create_panel, get_panel, get_panels, update_panel, delete_panel
- Связи щит-щит — link_panels, get_parent_panel, get_child_panels, get_panel_links
- Дерево щитов — get_panel_tree(object_id)
- Связь группа-щит — assign_group_to_panel, unassign_group_from_panel, get_groups_by_panel
- Нагрузка — calc_panel_load, calc_object_total_load
- Формат — format_panel, format_panel_short, get_panel_summary

### Паттерн callback (bot.py)
^(rooms_list_|room_|wall_|openings_|opening_|comm_|obj_|floor_|group_|cables_|panels_|panel_)

### Миграции
- 034 — базовый ЭОМ (elec_supply, elec_groups, elec_cables)
- 035 — floor_id, phase_l1/l2/l3
- 036 — привязка групп к этажу (legacy)
- 037 — Щиты ЭОМ (elec_panels, elec_panel_links, elec_groups.panel_id)

## 11. ЯДРО ЭОМ: ИЕРАРХИЯ ЩИТОВ (сессия 3)

### core/elec_rules.py (новый)
- DEFAULT_RULES — правила по умолчанию
- get_rules(object_id) — правила с переопределениями
- set_rule(object_id, key, value) — переопределить
- reset_rules(object_id) — сбросить
- list_overrides(object_id) — список изменений
- format_rules(object_id) — текст

### core/elec_panels.py (расширение сессии 3)
- Вводной автомат: set_input_breaker, get_input_breaker, format_input_breaker
- Компоненты: add_component, get_component, get_components, get_components_by_group, delete_component, clear_auto_components, format_component
- Автокомплектация: autocomplete_panel, recalc_panel, format_panel_components, get_panel_stats
- Селективность: check_selectivity, format_selectivity
- Иерархия: add_child_panel, set_panel_link_breaker, get_children_tree, _get_link

### Миграции (дополнение)
- 034 — базовый ЭОМ (elec_supply, elec_groups, elec_cables)
- 035 — floor_id, phase_l1/l2/l3
- 036 — привязка групп к этажу (legacy)
- 037 — Щиты ЭОМ (elec_panels, elec_panel_links, elec_groups.panel_id)
- 038 — elec_panel_components + поля вводного автомата
- 039 — расширение elec_panel_links (номиналы, полюса, кривые)

### Иерархия (правильная)
Объект → Щиты (N) → Группы (M) → Точки (K)
Связь щит-щит: автомат на родителе + вводной на дочернем
Связь щит-группа: elec_groups.panel_id
Связь группа-точка: room_comms.group_id

### UI (rooms.py)
- handle_panels_callback — роутер
- panels_list_{object_id} — список щитов
- panel_{panel_id} — карточка
- panel_input_* — вводной
- panel_auto_{panel_id} — автокомплектация
- panel_comp_{panel_id} — комплектация
- panel_stats_{panel_id} — статистика
- panel_children_* — дочерние
- panel_add_* — создание щита
- panel_child_* — создание дочернего

### Паттерн callback (bot.py)
^(rooms_list_|room_|wall_|openings_|opening_|comm_|obj_|floor_|group_|cables_|panels_|panel_)
