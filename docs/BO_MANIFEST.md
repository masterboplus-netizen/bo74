# 📘 BO_MANIFEST.md — Манифест проекта «Бо»

> **Версия:** 8.0
> **Дата:** 2026-10-02
> **Автор:** Andrey (tg_id: 1821030188)
> **Статус:** Активная разработка

---

## 0. КАК ПОЛЬЗОВАТЬСЯ ЭТИМ ДОКУМЕНТОМ

Этот документ — **единая точка входа** в проект «Бо».

**Правило:**
1. В новый чат первым сообщением скидывается **этот документ**.
2. Затем — **актуальные ссылки на код**.
3. Затем — **текущие задачи**.

---

## 1. ФИЛОСОФИЯ ПРОЕКТА

### Что такое «Бо»

**«Бо» — цифровая экосистема для строительной компании**, которая превращает ремонт из «хаоса в голове прораба» в управляемый, контролируемый, прибыльный процесс.

### Главная идея

**«Объять необъятное. Всё автоматизировано. Человек только делает руками.»**

Ремонт — это сотни мелочей. Сейчас всё живёт в голове прораба, в WhatsApp и в блокнотах. Когда прораб уезжает — работа встаёт.

**Бо решает через:**
- Единый цифровой двойник объекта.
- Автоматизацию рутины.
- Максимум контекста.
- Минимум действий от человека.

### Ключевые принципы

1. Бот — дирижёр, а не справочник.
2. Голос — основной ввод.
3. Фото — основной контроль.
4. Много типов замеров.
5. Данные идут в CAD/BIM.
6. Экосистема, а не бот.

### Для кого

Замерщик, программа Бо, дизайнер, инженер, менеджер, сметчик, заказчик, руководитель.

### Чего НЕ делаем

Не заменяем прораба, мастера, дизайнера. Не соревнуемся с 1С — интегрируемся.

---

## 2. ЭКОСИСТЕМА

### 2.1. Интерфейсы

| Интерфейс | Для кого |
|-----------|----------|
| Telegram-бот | Мастера, замерщики |
| Веб-приложение | Дизайнеры, инженеры |
| Мобильное | Прорабы на объекте |
| Планшет | Прораб |
| Клиентский портал | Заказчики |
| Публичный сайт | Клиенты |

### 2.2. Back-office

CRM, ERP, Бухгалтерия, HR, Документооборот, Юр.документы.

### 2.3. Инженерные модули

CAD/BIM, экспорт в DXF/IFC, расчёт освещения, вентиляции, электрики, сантехники, теплотехника.

### 2.4. Экономические модули

Сметы, материалы, маржинальность, кассовый план, налоги, зарплаты, P&L.

### 2.5. Аналитика

Дашборды, отчёты, предиктивная аналитика.

### 2.6. Интеграции

1С, МойСклад, Сбер, Тинькофф, Госуслуги, Google Sheets, CAD, WhatsApp, Email, SMS, Whisper, Yandex Vision, GPT.

### 2.7. Монетизация

Тарифы Лайт / Про / Бизнес / Прайм, подписки, биллинг, партнёрка, API.

### 2.8. Безопасность

RBAC, аудит, бэкапы, шифрование, логирование.

---

## 3. ТИПЫ ОБЪЕКТОВ

| Тип | Описание |
|-----|----------|
| bare_walls | Голые стены |
| ready_repair | Готовый ремонт |
| cosmetic | Косметический |
| frequent_works | Частотные работы |
| designer | Дизайнерский |
| commercial | Коммерческий |

**Следствие для БД:** поле `object_type` в `objects`.

---

## 4. ЭТАПЫ РЕМОНТА

| Этап | Что |
|------|-----|
| demolition | Демонтаж |
| rough | Черновая |
| comms | Коммуникации |
| plaster | Штукатурка |
| screed | Стяжка |
| finish | Чистовая |
| finish_work | Финишная |
| handover | Сдача |

**Следствие для БД:** `work_stages`, `object_stages`.

---

## 5. ВИДЫ РАБОТ

165+ видов. Категории: демонтаж, электрика, сантехника, штукатурка, стяжка, плитка, покраска, обои, полы, потолки, двери, мебель, декор, клининг.


**Следствие для БД:** `work_types`, `object_works`.

---

## 6. ТИПЫ ЗАМЕРОВ

### Главная идея

**Один объект — много версий замеров.**

### Типы сессий

| Код | Название | Когда |
|-----|----------|-------|
| initial | Первичный | До работ |
| after_rough | После черновой | После стяжки |
| furniture | Под мебель | Перед мебелью |
| tiling | Под плитку | Перед плиткой |
| mirror | Под зеркала | Перед зеркалами |
| electric | Под электрику | Перед электрикой |
| plumbing | Под сантехнику | Перед сантехникой |
| final | Финальный | Перед сдачей |
| custom | Свой | По необходимости |

**Все замеры привязаны к `session_id`.**

---

## 7. ОБХОД СТЕН

### ШАГ 1. Высота

- Одинаковая → 1 замер в центре.
- Разная → 3 замера: центр, левый, правый.

**Картинки:** `height_scheme_step1/2/3.png`.

### ШАГ 2. Обход стен

Стены нумеруются против часовой от двери:

| № | Позиция |
|---|---------|
| 1 | напротив |
| 2 | слева |
| 3 | у входа |
| 4 | справа |

Для каждой — **6 подшагов**:

1. Галочки (ниша / закругление / wavy / hidden).
2. Плоскость (ровная / разная).
3. Длина в СМ.
4. Проёмы (окно / дверь / вентиляция).
5. Угол (90° / 60-80-100 / 100-100 / градусы).
6. Доп. шаги (ниши, закругления, wavy, hidden).

**Картинки:** `wall_scheme_s{N}_{phase}.png`.

### ШАГ 3. Финал

Считаем площади, рисуем контур, проверяем замыкание (< 5%).

**Картинка:** `room_{id}_final.png`.

### ШАГ 4. Коммуникации

Отдельный экран: 19 типов.

### Восстановление

Состояние в `wall_drafts`. Шаги: `flags → plane → length → openings → angle → niche_width → niche_depth → niche_height → niche_plane → done`.

---

## 8. КАРТИНКИ

docs/images/
├── height_scheme_step1.png
├── height_scheme_step2.png
├── height_scheme_step3.png
├── wall_scheme_s1_flags.png
├── wall_scheme_s1_plane.png
├── wall_scheme_s1_length.png
├── wall_scheme_s1_angle.png
├── ... (4 стены × 4 фазы = 16 PNG)
├── niche_width.png
├── niche_depth.png
├── niche_height.png
├── opening_window.png
├── opening_door.png
├── opening_vent.png
└── room_{id}_final.png

---

## 9. МАТЕРИАЛЫ СТЕН

brick (кирпич), concrete (бетон), aerated (газобетон), drywall (гипсокартон), wood (дерево), plaster (штукатурка), other (прочее).

**Следствие для БД:** поле `material` в `room_measures`.

---

## 10. ЕДИНАЯ СИСТЕМА КООРДИНАТ

- Начало — левый нижний угол у двери (0,0,0).
- X — вдоль стены «напротив», вправо.
- Y — вдоль стены «слева», вверх.
- Z — высота.

Замыкание: если расхождение ≤ 5% — замкнуто.

Единицы: храним в СМ, при экспорте в ММ.

**Следствие для БД:** координаты в `room_measures`, `openings`, `wall_niches`, `room_comms`.


---

## 11. ЭКСПОРТ

| Формат | Для кого |
|--------|----------|
| JSON | Любые системы |
| DXF | AutoCAD, SketchUp |
| IFC | Revit, BIM |
| PDF | Печать, клиенты |
| CSV | Excel, сметы |

Библиотеки: `ezdxf`, `reportlab`, `ifcopenshell`.

UI: кнопка «📤 Экспорт» в карточке комнаты.

---

## 12. ЭКОНОМИКА

- Сметы — автоматические.
- Материалы — по нормам × потери.
- Маржинальность — по объекту, мастеру, виду работ.
- Кассовый план — прогноз.
- Налоги — НДС, УСН, взносы.
- Зарплаты — сделка / оклад / KPI.
- P&L, баланс, движение денег.

---

## 13. АНАЛИТИКА

- Дашборды: объекты, задачи, деньги, мастера, риски.
- Отчёты: заказчику, руководству, налоговой.
- Предиктивная: прогноз сроков, бюджета, рисков.

---

## 14. ИНТЕГРАЦИИ

- 1С, МойСклад — учёт.
- Сбер, Тинькофф — выписки.
- Google Sheets — для привыкших.
- CAD — DXF, IFC, SKP.
- Whisper, Yandex Vision — голос и OCR.
- GPT, Yandex GPT — AI-помощник.

---

## 15. МОДУЛЬ-СПРАВОЧНИК core/spec.py

Единый источник: тексты шагов, картинки, типы, валидации.

В `rooms.py` — никаких магических строк.

---

## 16. СХЕМА БД

Ключевые таблицы:
- users, objects, rooms
- measurement_sessions (новое!)
- room_measures, openings, wall_niches, room_comms
- wall_drafts
- work_stages, work_types, object_stages, object_works
- estimates, estimate_items, materials, suppliers, purchases
- tasks, task_history, photos
- clients, crm_deals, crm_activities
- finance, receipt_items
- room_exports (новое!)
- digest_log, action_log, system_settings

---

## 17. АРХИТЕКТУРА ЯДРА

core/
├── db.py, spec.py
├── geometry.py, model_3d.py
├── sessions.py, rooms.py, measures.py
├── openings.py, niches.py, comms.py
├── materials.py, estimates.py
├── works.py, stages.py, objects.py
├── tasks.py, crm.py, finance.py
├── economics.py, hr.py
├── history.py, conflicts.py, room_objects.py
├── export/
└── api/

interfaces/
├── telegram/, web/, mobile/, tablet/

---

## 18. МОНЕТИЗАЦИЯ

| Тариф | Для кого |
|-------|----------|
| Лайт | Частный мастер |
| Про | Бригада |
| Бизнес | Компания |
| Прайм | Крупная |

---

## 19. БЕЗОПАСНОСТЬ

- RBAC — роли.
- Аудит — в action_log.
- Бэкапы — в GitHub.
- Шифрование.
- Логирование.


---

## 20. ПЛАН РАБОТ

### ЭТАП 1. Ядро (сейчас)
- core/spec.py
- Переписать interfaces/telegram/rooms.py
- core/geometry.py
- core/model_3d.py
- Миграции БД
- core/sessions.py

### ЭТАП 2. Экспорт
- core/export/json_export.py
- core/export/dxf_export.py
- UI экспорта

### ЭТАП 3. Экономика
- core/materials.py
- core/estimates.py
- core/economics.py

### ЭТАП 4. Аналитика
- analytics/dashboards.py
- analytics/reports.py

### ЭТАП 5. Интеграции
- integrations/gsheets.py
- integrations/sberbank.py

### ЭТАП 6. Веб
- interfaces/web/

### ЭТАП 7. Мобильное
- interfaces/mobile/

### ЭТАП 8. Монетизация
- billing/

### ТЕКУЩИЕ БАГИ
- wall_niche_count_ — callback не доходит.
- Парсер add_task.
- Дубликат update_object.
- check_object_vs_comms — единицы.
- log_digest_sent — часовой пояс.

---

## ПРИЛОЖЕНИЕ A. ПРАВИЛА РАБОТЫ

1. Не проси скрины — работай через sed, grep.
2. Правки через python3 heredoc.
3. Бэкап перед правкой.
4. Проверка синтаксиса.
5. Перезапуск: pkill -9 -f "bot.py"; sleep 2; ./start_all.sh.
6. Коммит: git add -A && git commit -m "..." && git push.

---

## ПРИЛОЖЕНИЕ B. ССЫЛКИ

Репозиторий: https://github.com/masterboplus-netizen/bo74

Основные файлы:
- https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/bot.py
- https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/config.py
- https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/db.py
- https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/interfaces/telegram/rooms.py
- https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/handlers/commands.py
- https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/core/measures.py
- https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/core/rooms.py

---

## ПРИЛОЖЕНИЕ C. ЧЕК-ЛИСТ НОВОГО ЧАТА

1. Скинь этот документ (BO_MANIFEST.md).
2. Скинь актуальные ссылки на код.
3. Скинь список текущих задач.
4. Скажи «Погнали».

Всё. Никаких объяснений заново.

---

**Конец BO_MANIFEST.md**
*Версия 8.0. Финальная архитектура.*


---

## 21. СТРУКТУРА JSON (ПОЛНЫЙ ПРИМЕР)

Это то, что уходит во внешние системы. Пример комнаты «Зал»:

{
  "room": {
    "id": 48,
    "name": "Зал",
    "type": "living",
    "height_avg": 305,
    "height_points": {"center": 305, "left": 304, "right": 306}
  },
  "geometry": {
    "origin": "дверь, левый нижний угол",
    "coordinate_system": "локальная, X вправо, Y вверх, Z высота",
    "units": "см",
    "gap_percent": 0.8,
    "locked_at": "2026-10-02T18:42:00",
    "corners": [
      {"id": 1, "x": 0, "y": 0},
      {"id": 2, "x": 304, "y": 0},
      {"id": 3, "x": 304, "y": 250},
      {"id": 4, "x": 0, "y": 250}
    ]
  },
  "walls": [
    {
      "id": 1, "position": "напротив", "label": "Стена 1",
      "start": {"x": 0, "y": 0}, "end": {"x": 304, "y": 0},
      "length": 304, "height": 305, "angle_to_next": 90,
      "plane": "straight", "material": "brick",
      "features": {"niche": false, "rounded": false, "wavy": false, "hidden": false}
    }
  ],
  "openings": [
    {"id": 1, "type": "window", "wall": 1, "offset_x": 50,
     "width": 140, "height": 150, "sill_height": 80,
     "world_center": {"x": 120, "y": 0, "z": 155}}
  ],
  "niches": [
    {"id": 1, "wall": 1, "offset_x": 80,
     "width_bottom": 60, "width_top": 60,
     "depth_bottom": 40, "depth_top": 40, "height": 200,
     "world_center": {"x": 110, "y": 0, "z": 100}}
  ],
  "communications": [
    {"id": 1, "type": "elec_socket", "wall": 1,
     "offset_x": 200, "height": 30,
     "world": {"x": 200, "y": 0, "z": 30}}
  ],
  "areas": {
    "walls_gross": 30.4, "walls_net": 28.8,
    "floor": 7.6, "ceiling": 7.6
  },
  "session": {
    "type": "initial", "date": "2026-10-02",
    "created_by": 1821030188
  }
}

### Экспорт в DXF — слои

- WALLS — линии стен.
- OPENINGS — проёмы (вырезами).
- NICHES — ниши.
- COMMS — коммуникации.
- DIMENSIONS — размеры.
- LABELS — подписи.

### Экспорт в CSV — простой формат

Тип,Стена,Длина,Высота,Примечание
Стена,напротив,304,305,кирпич
Окно,напротив,140,150,подоконник 80

---

## 22. КЛЮЧЕВЫЕ ФУНКЦИИ ЯДРА

### core/geometry.py

def calc_wall_coords(walls_ordered):
    # Возвращает список стен с координатами (start_x, start_y, end_x, end_y).
    # Строит контур по длинам и углам.
    ...

def check_closure(walls):
    # Возвращает (closed: bool, gap_cm: float, gap_percent: float).
    # Проверяет замыкание контура.
    ...

def wall_offset_to_world(wall, offset_x, height):
    # Возвращает (world_x, world_y, world_z).
    # Конвертирует смещение вдоль стены в 3D-координаты.
    ...

### core/model_3d.py

def get_room_model(room_id, session_id=None):
    # Возвращает единый объект со всеми данными комнаты.
    # Для экспорта, для 3D, для смет.
    ...

def get_room_areas(room_id, session_id=None):
    # Возвращает площади стен, пола, потолка, проёмов.
    ...

### core/export/

def export_json(room_id, session_id=None):
    # Возвращает dict.
    ...

def export_dxf(room_id, session_id=None):
    # Возвращает путь к .dxf файлу.
    ...

def export_csv(room_id, session_id=None):
    # Возвращает путь к .csv файлу.
    ...

### core/sessions.py

def create_session(room_id, session_type, label):
    # Создаёт новую сессию замеров.
    ...

def get_active_session(room_id):
    # Возвращает актуальную сессию или None.
    ...

def list_sessions(room_id):
    # Возвращает все сессии комнаты.
    ...

### core/spec.py

def get_step_spec(step_name):
    # Возвращает текст, картинку, валидацию для шага.
    ...

def get_image_path(step_name, **kwargs):
    # Возвращает путь к картинке для шага.
    ...

---

## 23. ПОЛНЫЕ ОПИСАНИЯ ТАБЛИЦ БД

### users

id, tg_id, name, username, role, phone,
onboarded, created_at

### objects

id, code, name, address, status,
object_type, budget, execution_type, created_by, created_at

### rooms

id, object_id, name, room_type,
height, height_bottom, height_middle, height_top,
measure_method,
geometry_locked_at, geometry_gap_percent, coord_origin_note,
walls_started_at, walls_completed_at, contour_check_passed,
created_at, updated_at

### measurement_sessions

id, room_id, session_type, session_label,
session_date, created_by, notes,
is_active, created_at

### room_measures

id, room_id, session_id, category, label, wall_pos, order_num, material,
length, width, height, depth, angle, unit,
angle_value, angle_method,
start_x, start_y, end_x, end_y,
start_z, end_z,
has_rounded, radius,
has_hidden, hidden_note,
is_wavy, measured_bottom, measured_middle, measured_top,
tenant_id, created_by, created_at

### openings

id, room_id, session_id, opening_type,
wall_pos, offset_x, width, height, depth, sill_height,
from_room_id, to_room_id, to_outside, is_main,
vent_type, door_kind, note,
world_x, world_y, world_z,
tenant_id, created_by, created_at

### wall_niches

id, measure_id, room_id, session_id, name,
offset_x, offset_y,
width_bottom, width_top, depth_bottom, depth_top,
height, niche_type, note,
world_x, world_y, world_z, created_at

### room_comms

id, room_id, session_id, comm_type,
label, wall, offset_x, offset_y,
depth, diameter, voltage, size,
note, photo_id,
world_x, world_y, world_z,
tenant_id, created_by, created_at

### wall_drafts

room_id PRIMARY KEY, step_num, step_name,
flags TEXT (JSON), length, plane, angle_value, angle_method,
niches TEXT (JSON), niche_count, niche_current,
niche_temp TEXT (JSON), remaining_steps TEXT (JSON),
updated_at

### wall_lean

id, measure_id, room_id, lean_angle, lean_direction,
offset_top_x, offset_top_y, twist_angle, note

### wall_corners

id, room_id, corner_number, corner_type, angle_value,
radius, radius_note, deviation_bottom, deviation_top, note

### work_stages

id, code, name, description, order_num, typical_days

### work_types

id, code, name, category, unit,
tools (JSON), materials (JSON),
norm_hours, norm_price

### object_stages

id, object_id, stage_id, status,
started_at, completed_at, note

### object_works

id, object_id, room_id, work_type_id, stage_id,
qty, unit, price, total,
status, assigned_to,
started_at, completed_at, note

### estimates

id, object_id, session_id, name, total,
status, created_at

### estimate_items

id, estimate_id, work_type_id,
name, qty, unit, price, total

### materials

id, name, category, unit,
norm_per_sqm, price, supplier_id

### suppliers

id, name, phone, category, note, created_at

### purchases

id, object_id, material_id, qty, unit_price, total,
status, supplier_id, ordered_at, delivered_at, note

### tasks

id, object_id, room_id, title, description,
status, priority, type, assigned_to,
deadline, deadline_start, deadline_end,
completed_at, created_at

### task_history

id, task_id, old_status, new_status, changed_by, changed_at

### photos

id, object_id, task_id, room_id,
file_id, caption, stage, uploaded_by, taken_at, created_at

### clients

id, name, phone, email, address, source, tg_id, created_at

### crm_deals

id, client_id, object_id, status, budget, created_at

### crm_activities

id, client_id, user_id, type, description,
due_date, status, created_at, completed_at

### finance

id, object_id, task_id, category, amount, type,
date, note, is_personal, reimbursable, created_at

### receipt_items

id, finance_id, object_id, name, qty, unit,
price, total, is_personal, receipt_date, shop, created_at

### room_exports

id, room_id, format, file_path, file_size,
created_at, created_by

### digest_log

id, digest_type, sent_at, UNIQUE(digest_type, sent_at)

### action_log

id, user_id, action, entity, entity_id, details, created_at

### system_settings

key TEXT PRIMARY KEY, value TEXT, updated_at

---

## 24. ССЫЛКИ НА ВСЕ ФАЙЛЫ, МИГРАЦИИ, МОДУЛИ

### Репозиторий

https://github.com/masterboplus-netizen/bo74

### Основные файлы

- bot.py
- config.py
- db.py
- start_all.sh
- web_dashboard.py
- watchdog.py
- keep_alive.py
- requirements.txt

### Ядро (core/)

- core/db.py — обёртка БД
- core/spec.py — справочник (новое)
- core/geometry.py — геометрия (новое)
- core/model_3d.py — 3D-модель (новое)
- core/sessions.py — сессии (новое)
- core/rooms.py — комнаты
- core/measures.py — замеры
- core/openings.py — проёмы (вынести из measures)
- core/niches.py — ниши (вынести)
- core/comms.py — коммуникации
- core/materials.py — материалы (новое)
- core/estimates.py — сметы (новое)
- core/works.py — виды работ (новое)
- core/stages.py — этапы (новое)
- core/objects.py — объекты
- core/tasks.py — задачи
- core/crm.py — CRM
- core/finance.py — финансы
- core/economics.py — экономика (новое)
- core/hr.py — HR, KPI (новое)
- core/history.py — история
- core/conflicts.py — конфликты
- core/room_objects.py — мебель/техника
- core/export/json_export.py
- core/export/dxf_export.py
- core/export/csv_export.py
- core/export/pdf_export.py (позже)
- core/export/ifc_export.py (позже)

### Интерфейсы (interfaces/)

- interfaces/telegram/rooms.py — UI комнат
- interfaces/telegram/export.py — UI экспорта (новое)
- interfaces/web/ — веб-приложение (новое)
- interfaces/mobile/ — мобильное (новое)
- interfaces/tablet/ — планшет (новое)

### Обработчики (handlers/)

- handlers/commands.py — команды
- handlers/onboarding.py — онбординг
- handlers/admin.py — админ
- handlers/digest_cmd.py — дайджесты

### Модули (modules/)

- modules/objects.py, tasks.py, finance.py, users.py, personal.py
- modules/parser.py, crm.py, digest.py, kpi.py, reports.py
- modules/ocr.py, calendar.py, backup_db.py, dashboard_link.py, phone_utils.py

### Интеграции (integrations/) — новое

- integrations/1c.py
- integrations/moysklad.py
- integrations/sberbank.py
- integrations/tinkoff.py
- integrations/gsheets.py
- integrations/yandex_gpt.py
- integrations/whisper.py
- integrations/yandex_vision.py
- integrations/cad/

### Аналитика (analytics/) — новое

- analytics/dashboards.py
- analytics/reports.py
- analytics/forecasts.py
- analytics/kpi.py

### Публичная часть (public/) — новое

- public/website/
- public/client_portal/

### Монетизация (billing/) — новое

- billing/plans.py
- billing/billing.py
- billing/partners.py

### Скрипты (scripts/)

- scripts/draw_room_scheme.py — PNG-схемы
- scripts/backup_db.py — бэкапы

### Миграции (migrations/)

- 019_room_type.sql
- 020_room_height_points.sql
- 021_openings.sql
- 022_measure_method.sql
- 023_wall_niches.sql
- 024_wall_lean.sql
- 025_wall_corners.sql
- 026_room_walls_progress.sql
- 027_openings_extend.sql
- 028_measurement_sessions.sql (новое)
- 029_session_id.sql (новое)
- 030_material.sql (новое)
- 031_coords.sql (новое)
- 032_room_exports.sql (новое)
- 033_work_stages.sql (новое)

### Данные (data/)

- data/stages.json — 165 этапов
- data/works.json — виды работ
- data/materials.json — материалы
- data/templates.json — 8 шаблонов заказов
- data/checklists.json — чек-листы

### Документация (docs/)

- docs/BO_MANIFEST.md — этот файл
- docs/architecture.md
- docs/api.md
- docs/deploy.md
- docs/images/ — картинки

### Нарезка (parts/) — для чтения больших файлов

- parts/rooms_aa … rooms_ag
- parts/commands_aa … commands_ag
- parts/draw_aa, draw_ab
- parts/dashboard_aa, dashboard_ab

---

## 25. ДЕТАЛЬНЫЙ ПЛАН РАБОТ

### ЭТАП 1. Ядро (сейчас)

- [ ] Создать docs/BO_MANIFEST.md — готово
- [ ] Создать core/spec.py — справочник
- [ ] Переписать interfaces/telegram/rooms.py с нуля
- [ ] Создать core/geometry.py
- [ ] Создать core/model_3d.py
- [ ] Создать core/sessions.py
- [ ] Миграции: measurement_sessions, session_id, material, coords, room_exports
- [ ] Обновить bot.py под новый handle_rooms_callback

### ЭТАП 2. Экспорт

- [ ] core/export/json_export.py
- [ ] core/export/dxf_export.py (установить ezdxf)
- [ ] core/export/csv_export.py
- [ ] interfaces/telegram/export.py — кнопка «📤 Экспорт»

### ЭТАП 3. Экономика

- [ ] core/materials.py — расчёт по нормам
- [ ] core/estimates.py — сметы
- [ ] core/works.py — виды работ (импорт data/works.json)
- [ ] core/stages.py — этапы (импорт data/stages.json)
- [ ] core/economics.py — маржа, P&L

### ЭТАП 4. Аналитика

- [ ] analytics/dashboards.py
- [ ] analytics/reports.py
- [ ] analytics/forecasts.py

### ЭТАП 5. Интеграции

- [ ] integrations/gsheets.py
- [ ] integrations/sberbank.py
- [ ] integrations/1c.py

### ЭТАП 6. Веб-приложение

- [ ] interfaces/web/app.py (Flask/FastAPI)
- [ ] interfaces/web/templates/
- [ ] public/client_portal/

### ЭТАП 7. Мобильное приложение

- [ ] interfaces/mobile/ (Flutter)

### ЭТАП 8. Монетизация

- [ ] billing/plans.py
- [ ] billing/billing.py
- [ ] billing/partners.py

### ТЕКУЩИЕ БАГИ (фиксим параллельно)

- [ ] wall_niche_count_ — callback не доходит до handle_rooms_callback
- [ ] Парсер add_task в modules/parser.py — блок не возвращает return
- [ ] Дубликат update_object в modules/objects.py
- [ ] check_object_vs_comms — единицы (м vs см)
- [ ] log_digest_sent — часовой пояс (local vs МСК)

---

## 26. ИСТОРИЯ ВЕРСИЙ

- 7.0–7.1 — старт, объекты, задачи, финансы
- 7.2 — фундамент, 27 таблиц, роли
- 7.3 — рабочий бот на Replit
- 7.4 — фиксы парсера, кнопки Добавить
- 7.5 — онбординг, 4 роли
- 7.6 — фикс UnboundLocalError
- 7.7 — комнаты, обход стен
- 7.7.1–7.7.4 — замеры, ниши, коммуникации
- 8.0 — финальная архитектура, экосистема

---

*Конец Части 5. Манифест полностью завершён.*
