"""core.export.estimate_export — Экспорт сметы (CSV для Excel).

Форматы:
- export_panel_estimate_csv(panel_id) — смета щита
- export_object_estimate_csv(object_id) — смета ЭОМ объекта
- save_estimate_csv(..., path)
"""
import csv
import io
from datetime import datetime


def export_panel_estimate_csv(panel_id):
    """CSV-смета щита (компоненты)."""
    from core.elec_panels import get_panel, get_components, calc_component_price, format_component
    from modules.objects import get_object

    p = get_panel(panel_id)
    if not p:
        return None

    obj = get_object(p.get('object_id')) if p.get('object_id') else None
    obj_name = obj['name'] if obj else '—'

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')

    writer.writerow(["Смета щита"])
    writer.writerow(["Объект", obj_name])
    writer.writerow(["Щит", p.get('name') or '?'])
    writer.writerow(["Тип", p.get('panel_type') or '?'])
    writer.writerow(["Дата", datetime.now().strftime('%d.%m.%Y')])
    writer.writerow([])
    writer.writerow(["№", "Наименование", "Тип", "Модель",
                     "Номинал", "Полюса", "Кол-во", "Цена", "Сумма"])

    comps = get_components(panel_id)
    total = 0.0
    for idx, c in enumerate(comps, start=1):
        try:
            price = c.get('price_unit')
            if price:
                unit = float(price)
            else:
                # ищем цену через elec_prices
                from core.elec_panels import calc_component_price as ccp
                qty = c.get('quantity') or 1
                t = ccp(c)
                unit = round(t / qty, 2) if qty else t
        except Exception:
            unit = 0
        qty = c.get('quantity') or 1
        summa = round(unit * qty, 2)
        total += summa
        writer.writerow([
            idx,
            format_component(c),
            c.get('component_type') or '',
            c.get('component_model') or '',
            c.get('rating') or '',
            c.get('poles') or '',
            qty,
            unit,
            summa,
        ])

    writer.writerow([])
    writer.writerow(["", "ИТОГО", "", "", "", "", "", "", round(total, 2)])
    return output.getvalue()


def export_object_estimate_csv(object_id):
    """CSV-смета ЭОМ объекта (щиты + монтаж)."""
    from core.elec_prices import calc_object_elec_total
    from modules.objects import get_object

    obj = get_object(object_id)
    obj_name = obj['name'] if obj else ('Объект #' + str(object_id))

    data = calc_object_elec_total(object_id)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')

    writer.writerow(["Смета ЭОМ объекта"])
    writer.writerow(["Объект", obj_name])
    writer.writerow(["Дата", datetime.now().strftime('%d.%m.%Y')])
    writer.writerow([])

    writer.writerow(["Щиты"])
    writer.writerow(["Название", "Стоимость"])
    for pid, info in data['panels_breakdown'].items():
        writer.writerow([info['name'], info['cost']])
    writer.writerow(["Итого щиты", data['panels_cost']])
    writer.writerow([])

    writer.writerow(["Электромонтаж"])
    writer.writerow(["Метраж", data['montage_meters']])
    writer.writerow([])
    writer.writerow(["Кабель"])
    for k, v in data['montage_by_cable'].items():
        writer.writerow([k, v])
    writer.writerow(["Итого кабель", data['montage_cable_cost']])
    writer.writerow([])
    writer.writerow(["Расходники"])
    for k, v in data['montage_by_route'].items():
        writer.writerow([k, v])
    writer.writerow(["Итого расходники", data['montage_consumable_cost']])
    writer.writerow([])
    writer.writerow(["Итого монтаж", data['montage_total']])
    writer.writerow([])
    writer.writerow(["Работы"])
    if data.get('works_count'):
        writer.writerow(["Всего", data['works_count']])
        writer.writerow(["Итого", data['works_total']])
    else:
        writer.writerow(["нет", 0])
    writer.writerow([])
    writer.writerow(["ВСЕГО ЭОМ", data['total']])

    return output.getvalue()


def save_estimate_csv(content, path=None, prefix='estimate'):
    """Сохраняет CSV в файл. Возвращает путь."""
    import os
    if not content:
        return None
    if not path:
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tmp")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, prefix + "_" + datetime.now().strftime('%Y%m%d_%H%M') + ".csv")
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(content)
    return path
