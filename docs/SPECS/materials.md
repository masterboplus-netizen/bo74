# SPECS/materials.md — Модуль материалов

> Спецификация модуля `core/materials.py`

---

## 1. НАЗНАЧЕНИЕ

Справочник материалов + расчёт по нормам.

---

## 2. СТРУКТУРА МАТЕРИАЛА

- id
- name (название)
- category (категория)
- unit (кг, л, м², м.п., шт)
- norm_per_sqm (норма расхода на м²)
- price (цена за единицу)
- supplier_id (поставщик)
- loss_percent (потери на обрезку)

---

## 3. КАТЕГОРИИ

- Штукатурка
- Шпаклёвка
- Грунтовка
- Краска
- Клей
- Затирка
- Стяжка
- Плитка
- Ламинат
- Обои
- Кабель
- Трубы
- Фитинги
- Крепёж
- Прочее

---

## 4. ФУНКЦИИ

### add_material(name, category, unit, norm_per_sqm, price, supplier_id=None, loss_percent=10)
### get_material(material_id)
### get_materials(category=None)
### update_material(material_id, **kwargs)
### delete_material(material_id)

### calc_qty(material_id, area_sqm)
qty = area_sqm × norm_per_sqm × (1 + loss_percent/100)

### calc_cost(material_id, area_sqm)
cost = calc_qty(...) × price

### calc_room_materials(room_id, work_types)
Все материалы для комнаты.

---

## 5. ИМПОРТ ИЗ JSON

data/materials.json:
[
  {"name": "Штукатурка гипсовая", "category": "Штукатурка", "unit": "кг", "norm_per_sqm": 15, "price": 30},
  ...
]

Импорт: `import_materials_from_json(path)`

---

## 6. ПРАВИЛА

1. Норма — на 1 м².
2. Потери — 10% по умолчанию, настраивается.
3. Цена — актуальная на дату.
4. Категория — обязательна.
5. Единица — из фиксированного списка.

---

*Конец SPECS/materials.md*
