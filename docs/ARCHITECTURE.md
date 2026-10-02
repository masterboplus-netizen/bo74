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
