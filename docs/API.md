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
