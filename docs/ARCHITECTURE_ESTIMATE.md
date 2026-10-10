# ARCHITECTURE_ESTIMATE.md — Архитектура сметы Бо

## Принцип: гибрид spec.py + БД

1. core/spec.py — дефолтные цены и нормы (захардкожены).
2. БД-таблицы — overrides (ручные правки, импорт прайсов).
3. Функции get_*_price — сначала БД, потом spec.py.
4. Смета объекта — сумма отделки + ЭОМ + сантехники.

## Слои сметы

### Отделка
- materials (таблица) — нормы + цены
- work_types (таблица) — работы
- spec.MATERIALS_DEFAULT — дефолты
- spec.FINISH_WORK_TYPES — дефолты
- core/materials.py — функции
- core/works.py — функции

### ЭОМ
- component_prices (таблица) — цены
- spec.COMPONENT_PRICES_DEFAULT — дефолты
- spec.CABLE_PRICES_DEFAULT — кабель
- spec.CONSUMABLE_PRICES_DEFAULT — расходники
- spec.WORK_TYPES_DEFAULT — работы
- core/elec_prices.py — функции
- core/elec_routes.py — маршруты
- core/elec_panels.py — щиты

### Сантехника
- plumbing_panels (таблица)
- plumbing_routes (таблица)
- core/plumbing_panels.py — функции

### Смета комнаты
- core/room_estimate.py (новый)
- calc_room_estimate(room_id) — всё вместе

### Смета объекта
- core/object_estimate.py (новый)
- calc_object_estimate(object_id) — сумма по комнатам + работы объекта

## Что уже работает
- Смета ЭОМ (component_prices + elec_routes + spec)
- Смета сантехники (plumbing_panels + spec)
- Работы объекта (object_works)

## Что нужно
1. Миграции 050 (materials), 051 (work_types)
2. spec.MATERIALS_DEFAULT, spec.FINISH_WORK_TYPES
3. core/room_estimate.py
4. core/object_estimate.py
5. UI: кнопка «💰 Смета» в комнате
6. UI: кнопка «💰 Смета объекта»

## Приоритет
Сессия 11: spec.py + миграции
Сессия 12: core/room_estimate.py
Сессия 13: UI сметы комнаты
