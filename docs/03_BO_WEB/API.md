# API.md — API Бо (REST)

> **Дата:** 2026-10-31
> **Планируется:** Этап 6 (Веб и интеграции).

## 1. АУТЕНТИФИКАЦИЯ
Bearer Token (позже). Пока — только внутренние вызовы.

## 2. ЭНДПОИНТЫ (со статусами)

| Метод | Путь | Статус | Описание |
|---|---|---|---|
| GET | /api/objects | реализовано (Supabase) | Список объектов |
| GET | /api/object/{id} | реализовано (Supabase) | Детали объекта |
| POST | /api/objects | реализовано (Supabase) | Создание объекта |
| PATCH | /api/object/{id} | реализовано (Supabase) | Обновление объекта |
| GET | /api/room/{id}/walls | реализовано (FastAPI) | Стены комнаты |
| GET | /api/room/{id}/report | реализовано (FastAPI) | Отчёт по комнате |
| Остальные | ... | план | ... |

## 3. ВЕБХУКИ (все план)
- POST /webhook/task_created
- POST /webhook/task_done
- POST /webhook/photo_added
- POST /webhook/export_ready

## 4. SDK
Планируется: Python, JavaScript, Мобильный.

## 5. ПРАВИЛА
1. RESTful.
2. JSON.
3. Коды ошибок — 400/401/403/404/500.
4. Rate limiting — 100 req/min.
5. Версионирование — /api/v1/, /api/v2/.

**Конец API.md**
