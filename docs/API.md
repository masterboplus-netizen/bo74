# API.md — API Бо

> REST API для внешних систем. Планируется на Этапе 6.

---

## 1. АУТЕНТИФИКАЦИЯ

Bearer Token (позже).
Пока — только внутренние вызовы.

---

## 2. ЭНДПОИНТЫ

### GET /api/summary
Общая сводка.
Возвращает: objects_count, tasks_open, tasks_done, income, expense, balance.

### GET /api/objects
Список объектов.
Возвращает: [{id, name, status, budget, income, expense, tasks_open, tasks_done}]

### GET /api/object/{id}
Детали объекта.
Возвращает: {object, tasks, finance, photos}.

### GET /api/object/{id}/photos
Фото объекта.
Возвращает: [{id, stage, caption, taken_at, task_title, file_id}].

### GET /api/room/{id}
Комната.
Возвращает: {room, measures, openings, niches, comms, areas}.

### GET /api/room/{id}/model
Модель комнаты (JSON).
Возвращает: полную модель для экспорта.

### GET /api/room/{id}/export/{format}
Экспорт комнаты.
Форматы: json, dxf, csv, pdf, ifc.
Возвращает: файл.

### GET /api/tasks
Список задач.
Параметры: object_id, status, assigned_to.
Возвращает: [{id, title, status, deadline, object_name}].

### GET /api/finance
Финансы.
Параметры: object_id, period.
Возвращает: сводку.

### GET /api/kpi
KPI.
Возвращает: по мастерам, по объектам.

---

## 3. ВЕБХУКИ

### POST /webhook/task_created
### POST /webhook/task_done
### POST /webhook/photo_added
### POST /webhook/export_ready

---

## 4. SDK

Планируется:
- Python SDK.
- JavaScript SDK.
- Мобильный SDK.

---

## 5. ПРАВИЛА

1. Все методы — RESTful.
2. Формат ответа — JSON.
3. Ошибки — стандартные коды (400, 401, 403, 404, 500).
4. Rate limiting — 100 запросов/мин.
5. Версионирование — /api/v1/, /api/v2/.

---

*Конец API.md*

---

## 🏛️ АРХИТЕКТУРА ПАКЕТА `rooms/` (сессия 20, 2026-10-19)

**Проблема:** `rooms.py` — 7904 строки, God Object. Нарушает Манифест (Этапы 5–7: API, Web, Mobile).

**Решение:** 4 слоя.

1. **Слой UI-хелперов** — `interfaces/telegram/rooms/_helpers.py`
   - `_safe_edit`, `_send_png_or_edit`, `_send_png_or_reply`, `_image_path`.
2. **Слой каркаса (Telegram)** — `interfaces/telegram/rooms/core.py`
   - `handle_rooms_callback`, `show_rooms_list`, `show_room_card`, `_show_height_step`.
3. **Слой Telegram-доменов** — `interfaces/telegram/rooms/`
   - `walls.py` (обход стен, ниши, углы), `comm.py` (коммуникации), `openings.py` (проёмы), `floors.py` (помещения), `elec.py` (щиты, группы, кабели), `plumbing.py` (сантехника), `works.py` (работы), `reports.py` (отчёты, экспорт).
4. **Слой бизнес-логики (сессия 22+)** — `core/rooms_logic/`
   - Без Telegram-зависимостей. Для Web (FastAPI) и Mobile (Flutter).

**Правило:** сначала хелперы, потом Telegram-домены, потом — бизнес-логику в `core/rooms_logic/`.

---

## 🌐 WEB/MOBILE: СТАРТ (сессия 23)

**Дата:** 2026-10-20, 12:08.

**Что сделано:**
1. **`core/rooms_logic/`** — бизнес-логика (без Telegram):
   - `walls.py` (прогресс, площади).
   - `comm.py` (коммуникации).
   - `openings.py` (проёмы).
   - `elec.py` (группы, щиты).
   - `floors.py` (этажи).
   - `reports.py` (полный отчёт).
2. **`interfaces/api/`** — FastAPI (порт 8080):
   - `main.py` — 3 роута (`/`, `/api/rooms/{id}/walls`, `/api/rooms/{id}/report`).
   - `templates/index.html` — веб-панель.
3. **`.replit`** — добавлен воркфлоу `FastAPI` (порт 8080).

**Что работает:**
- `uvicorn` запущен на 8080, сайт открывается.
- API отдаёт JSON (стены, отчёты).

**Следующие шаги (сессия 24):**
- Расширить API (комнаты, объекты, ЭОМ).
- Сделать полноценный фронтенд (React или Vue).
- Вынести `rooms_elec.py` (P8) — **до** UI.

**Документация:**
- `docs/ARCHITECTURE.md` — обновить (API + core/rooms_logic).
- `docs/API.md` — описать роуты.
