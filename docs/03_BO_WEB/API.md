# API.md — API Бо (REST)

> **Дата:** 2026-10-29
> **Планируется:** Этап 6 (Веб и интеграции).

## 1. АУТЕНТИФИКАЦИЯ
Bearer Token (позже). Пока — только внутренние вызовы.

## 2. ЭНДПОИНТЫ (со статусами)

| Метод | Путь | Статус | Описание |
|---|---|---|---|
| GET | /api/summary | 🔴 план | Сводка (objects_count, tasks_open, income, expense, balance) |
| GET | /api/objects | 🟢 реализовано | Список объектов (из bo72.db) |
| GET | /api/object/{id} | 🔴 план | Детали объекта (object, tasks, finance, photos) |
| GET | /api/object/{id}/photos | 🔴 план | Фото объекта |
| GET | /api/room/{id} | 🔴 план | Комната (measures, openings, niches, comms, areas) |
| GET | /api/room/{id}/walls | 🟢 реализовано | Данные о стенах комнаты |
| GET | /api/room/{id}/report | 🟢 реализовано | Полный отчет по комнате |
| GET | /api/room/{id}/model | 🔴 план | Модель комнаты (JSON) |
| GET | /api/room/{id}/export/{format} | 🔴 план | Экспорт (json, dxf, csv, pdf, ifc) |
| GET | /api/tasks | 🔴 план | Список задач |
| GET | /api/finance | 🔴 план | Финансы |
| GET | /api/kpi | 🔴 план | KPI |

## 3. ВЕБХУКИ (все 🔴 план)
- POST /webhook/task_created
- POST /webhook/task_done
- POST /webhook/photo_added
- POST /webhook/export_ready

## 4. SDK
Планируется: Python SDK, JavaScript SDK, Мобильный SDK.

## 5. ПРАВИЛА
1. Все методы — RESTful.
2. Формат ответа — JSON.
3. Ошибки — стандартные коды (400, 401, 403, 404, 500).
4. Rate limiting — 100 запросов/мин.
5. Версионирование — /api/v1/, /api/v2/.

**Конец API.md**
