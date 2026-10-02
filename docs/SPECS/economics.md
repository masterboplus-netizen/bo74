# SPECS/economics.md — Модуль экономики

> Спецификация модулей `core/materials.py`, `core/estimates.py`, `core/economics.py`

---

## 1. НАЗНАЧЕНИЕ

Считает сметы, материалы, маржу, P&L, налоги. Автоматически — по замерам.

---

## 2. МАТЕРИАЛЫ (core/materials.py)

### calc_material(material_id, area_sqm, loss_percent=10)
Считает количество:
qty = area_sqm × norm_per_sqm × (1 + loss_percent/100)

### calc_all_materials(work_type_id, area_sqm)
Все материалы для вида работ.

### get_materials_for_room(room_id)
Материалы по всем видам работ комнаты.

---

## 3. СМЕТЫ (core/estimates.py)

### create_estimate(object_id, session_id=None, name=None)
Создаёт смету.

### add_estimate_item(estimate_id, work_type_id, qty, unit, price)
Добавляет позицию.

### calc_estimate(estimate_id)
Считает итог: sum(qty × price).

### get_estimate(estimate_id)
Возвращает смету с позициями.

### format_estimate(estimate_id)
Текст для UI.

---

## 4. ЭКОНОМИКА (core/economics.py)

### calc_margin(object_id)
Маржа:
- income (доход)
- expense (расход)
- profit = income − expense
- margin_percent = profit / income × 100%

### calc_margin_by_work(object_id)
Маржа по видам работ.

### calc_margin_by_master(object_id)
Маржа по мастерам.

### calc_pnl(period='month')
P&L за период:
- Выручка
- Расходы (материалы + работы + прочее)
- Прибыль
- Налоги
- Чистая прибыль

### calc_taxes(period='month')
Налоги: НДС (20%), УСН (6% или 15%), взносы, НДФЛ.

### calc_cashflow(months=3)
Кассовый план на N месяцев.

---

## 5. СПРАВОЧНИКИ

### work_types
Виды работ с нормой времени, ценой, инструментами, материалами.

### materials
Материалы с нормой расхода, ценой.

### suppliers
Поставщики.

---

## 6. ПРИМЕР РАСЧЁТА

Дано:
- Комната: 30.4 м² стен, 7.6 м² пола.
- Проёмы: 1.6 м².

Расчёт:
1. Стены — штукатурка: (30.4−1.6) × 800 = 23 040 ₽.
2. Стены — покраска: 28.8 × 250 = 7 200 ₽.
3. Пол — стяжка: 7.6 × 1200 = 9 120 ₽.
4. Потолок: 7.6 × 900 = 6 840 ₽.

Материалы:
1. Штукатурка: 28.8 × 15 × 1.1 = 475 кг → 16 мешков × 450 = 7 200 ₽.
2. Краска: 28.8 × 0.3 × 2 = 17.3 л → 5 банок × 1500 = 7 500 ₽.

Итого: 66 800 ₽.

Маржа (если заказчик платит 100 000):
Прибыль: 33 200 ₽. Маржа: 33.2%.

---

## 7. ПРАВИЛА

1. Все расчёты — на основе замеров.
2. Нормы — из справочников.
3. Потери — 10% по умолчанию.
4. Цены — из system_settings или отдельной таблицы.
5. Итоги — всегда с округлением вверх.

---

*Конец SPECS/economics.md*
