# PROMPTS/export_format.md

> Как добавить новый формат экспорта.

---

## ШАБЛОН

Формат:
[Например, IFC]

Для кого:
[Например, для Revit/BIM инженеров]

Библиотека:
[Например, ifcopenshell]

Структура:
[Что должно быть в файле]

Ссылки:
[Raw-ссылки на core/export/, model_3d.py]

---

## ПРИМЕР

Формат:
IFC.

Для кого:
Инженеры с Revit, BIM-специалисты.

Библиотека:
ifcopenshell.

Структура:
- IfcProject
- IfcSite
- IfcBuilding
- IfcBuildingStorey
- IfcSpace (комната)
- IfcWall (стены)
- IfcOpeningElement (проёмы)
- IfcWindow, IfcDoor

Ссылки:
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/core/model_3d.py
...

---

## ЧТО ДЕЛАЕТ АССИСТЕНТ

1. Устанавливает библиотеку (в requirements.txt).
2. Создаёт core/export/ifc_export.py.
3. Реализует функцию export_ifc(room_id, session_id).
4. Добавляет в UI экспорта.
5. Проверяет синтаксис.
6. Тестирует на примере.

---

## ПРАВИЛА

- Формат — стандартный (IFC 4, DXF R2013).
- Единицы — ММ (стандарт CAD/BIM).
- Иерархия — стандартная для формата.
- Слои/уровни — с понятными именами.

---

*Конец export_format.md*
