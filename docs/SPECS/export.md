# SPECS/export.md — Модуль экспорта

> Спецификация модуля `core/export/`

---

## 1. НАЗНАЧЕНИЕ

Превращает данные замеров в файлы для внешних систем: JSON, DXF, IFC, PDF, CSV.

---

## 2. ФОРМАТЫ

### JSON — универсальный
Структура: см. BO_MANIFEST.md раздел 21.

Модуль: `export/json_export.py`
Функция: `export_json(room_id, session_id=None) → dict`

### DXF — для CAD
Слои: WALLS, OPENINGS, NICHES, COMMS, DIMENSIONS, LABELS.

Модуль: `export/dxf_export.py`
Функция: `export_dxf(room_id, session_id=None) → path`
Библиотека: `ezdxf`

### IFC — для BIM
3D-модель с семантикой.

Модуль: `export/ifc_export.py`
Функция: `export_ifc(room_id, session_id=None) → path`
Библиотека: `ifcopenshell` (позже)

### PDF — для печати
Схема + размеры + площадь.

Модуль: `export/pdf_export.py`
Функция: `export_pdf(room_id, session_id=None) → path`
Библиотека: `reportlab`

### CSV — для Excel
Таблица размеров.

Модуль: `export/csv_export.py`
Функция: `export_csv(room_id, session_id=None) → path`

---

## 3. ИСТОЧНИК ДАННЫХ

Все экспорты берут данные из `core/model_3d.get_room_model(room_id, session_id)`.

Это единый объект со всеми данными:
- geometry (координаты)
- walls (стены)
- openings (проёмы)
- niches (ниши)
- communications (коммуникации)
- areas (площади)
- session (сессия)

---

## 4. UI ЭКСПОРТА

Кнопка «📤 Экспорт» в карточке комнаты.

Меню:
- [📄 JSON]
- [📐 DXF] (для CAD)
- [🏗️ IFC] (для BIM, позже)
- [🖨️ PDF] (для печати)
- [📊 CSV] (для Excel)
- [⬅️ Отмена]

После выбора — файл отправляется в чат.

---

## 5. ИСТОРИЯ ЭКСПОРТОВ

Таблица `room_exports`:
- id, room_id, format, file_path, file_size, created_at, created_by

При экспорте — записываем.

---

## 6. ПРАВИЛА

1. Все экспорты — из единого `get_room_model`.
2. СМ → ММ при экспорте.
3. Файлы — во временную папку, потом в чат.
4. История экспортов — в БД.
5. Никаких блокирующих операций (async).

---

*Конец SPECS/export.md*
