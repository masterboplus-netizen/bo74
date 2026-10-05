"""core.export.spec_export — Экспорт спецификации щита (TXT).

Формат: спецификация компонентов щита (по ГОСТ-подобному виду).
"""
from datetime import datetime


def export_panel_spec(panel_id):
    """Возвращает текст спецификации щита.

    Структура:
    - Шапка (объект, щит, дата)
    - Таблица компонентов (№, тип, модель, номинал, полюса, кол-во, цена, сумма)
    - Итого
    """
    from core.elec_panels import (get_panel, get_components,
                                   calc_component_price, format_component,
                                   calc_panel_cost)
    from modules.objects import get_object

    p = get_panel(panel_id)
    if not p:
        return None

    object_id = p.get('object_id')
    obj = get_object(object_id) if object_id else None
    obj_name = obj['name'] if obj else '—'

    comps = get_components(panel_id)
    total = calc_panel_cost(panel_id)

    lines = []
    lines.append("=" * 70)
    lines.append("СПЕЦИФИКАЦИЯ ЭЛЕКТРООБОРУДОВАНИЯ (щит)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Объект:      " + str(obj_name))
    lines.append("Щит:         " + str(p.get('name') or '?'))
    lines.append("Тип щита:    " + str(p.get('panel_type') or '?'))
    lines.append("Дата:        " + datetime.now().strftime('%d.%m.%Y'))
    lines.append("")
    lines.append("-" * 70)
    lines.append("№  Наименование                          Кол-во   Цена    Сумма")
    lines.append("-" * 70)

    if not comps:
        lines.append("(компоненты отсутствуют)")
    else:
        idx = 0
        for c in comps:
            idx += 1
            name = format_component(c)
            qty = c.get('quantity') or 1
            price = c.get('price_unit')
            if price:
                unit = float(price)
            else:
                # цена за единицу из расчёта / qty
                try:
                    from core.elec_panels import calc_component_price as ccp
                    total_c = ccp(c)
                    unit = round(total_c / qty, 2) if qty else total_c
                except Exception:
                    unit = 0
            summa = round(unit * qty, 2)

            # Обрезка до 40 символов
            name_short = name[:40]
            line = (str(idx).ljust(3) + name_short.ljust(40) +
                    " " + str(qty).rjust(4) +
                    " " + str(unit).rjust(7) +
                    " " + str(summa).rjust(8))
            lines.append(line)

    lines.append("-" * 70)
    lines.append("ИТОГО:".ljust(58) + str(total).rjust(11) + " ₽")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Сформировано: Бо 7.7 · " + datetime.now().strftime('%Y-%m-%d %H:%M'))

    return "\n".join(lines)


def save_panel_spec(panel_id, path=None):
    """Сохраняет спецификацию в TXT-файл. Возвращает путь."""
    import os
    content = export_panel_spec(panel_id)
    if not content:
        return None
    if not path:
        out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tmp")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "panel_spec_" + str(panel_id) + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def export_object_spec(object_id):
    """Спецификация ЭОМ объекта (все щиты + монтаж)."""
    from core.elec_panels import get_panels, get_components, format_component, calc_component_price
    from core.elec_prices import calc_object_elec_total
    from modules.objects import get_object

    obj = get_object(object_id)
    obj_name = obj['name'] if obj else ('Объект #' + str(object_id))

    panels = get_panels(object_id)
    data = calc_object_elec_total(object_id)

    lines = []
    lines.append("=" * 72)
    lines.append("СПЕЦИФИКАЦИЯ ЭОМ ОБЪЕКТА")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Объект:  " + str(obj_name))
    lines.append("Дата:    " + datetime.now().strftime('%d.%m.%Y'))
    lines.append("")
    lines.append("-" * 72)
    lines.append("ЩИТЫ")
    lines.append("-" * 72)

    for p in panels:
        lines.append("")
        lines.append("Щит: " + str(p.get('name') or '?'))
        lines.append("Тип: " + str(p.get('panel_type') or '?'))
        comps = get_components(p['id'])
        if not comps:
            lines.append("  (нет компонентов)")
        else:
            for idx, c in enumerate(comps, start=1):
                lines.append("  " + str(idx) + ". " + format_component(c))
        try:
            cost = sum(calc_component_price(c) for c in comps)
        except Exception:
            cost = 0
        lines.append("  Итого щит: " + str(round(cost, 2)) + " ₽")

    lines.append("")
    lines.append("=" * 72)
    lines.append("СВОДКА")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Щиты: " + str(data['panels_cost']) + " ₽")
    lines.append("Электромонтаж:")
    lines.append("  Кабель: " + str(data['montage_cable_cost']) + " ₽")
    lines.append("  Расходники: " + str(data['montage_consumable_cost']) + " ₽")
    lines.append("  Итого: " + str(data['montage_total']) + " ₽")
    lines.append("")
    lines.append("ВСЕГО ЭОМ: " + str(data['total']) + " ₽")
    lines.append("")
    lines.append("Сформировано: Бо 7.7 · " + datetime.now().strftime('%Y-%m-%d %H:%M'))

    return "\n".join(lines)


def export_plumbing_panel_spec(panel_id):
    """Спецификация сантехники по коллектору (TXT)."""
    from core.plumbing_panels import (get_panel, get_routes_by_panel,
                                       get_pipe_label, get_pipe_price,
                                       calc_montage_cost_by_panel,
                                       get_panel_type_label)
    from modules.objects import get_object
    p = get_panel(panel_id)
    if not p:
        return None
    obj = get_object(p.get('object_id')) if p.get('object_id') else None
    obj_name = obj['name'] if obj else '—'

    routes = get_routes_by_panel(panel_id)
    data = calc_montage_cost_by_panel(panel_id)

    lines = []
    lines.append("=" * 70)
    lines.append("СПЕЦИФИКАЦИЯ САНТЕХНИКИ (коллектор)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Объект:      " + str(obj_name))
    lines.append("Коллектор:   " + str(p.get('name') or '?'))
    lines.append("Тип:         " + str(get_panel_type_label(p.get('panel_type'))))
    lines.append("Дата:        " + datetime.now().strftime('%d.%m.%Y'))
    lines.append("")
    lines.append("-" * 70)
    lines.append("№  Труба                    Длина   Цена/м   Сумма")
    lines.append("-" * 70)

    if not routes:
        lines.append("(нет трасс)")
    else:
        for idx, r in enumerate(routes, start=1):
            pipe_label = get_pipe_label(r.get('pipe_type'))
            length = r.get('length_m') or 0
            price_m = get_pipe_price(r.get('pipe_type'))
            summa = round(length * price_m, 2)
            lines.append(
                str(idx).ljust(3) +
                pipe_label[:22].ljust(23) +
                str(length).rjust(6) +
                str(price_m).rjust(9) +
                str(summa).rjust(10)
            )

    lines.append("-" * 70)
    lines.append("Трубы:".ljust(55) + str(data['total_pipe_cost']).rjust(14) + " ₽")
    lines.append("Расходники:".ljust(55) + str(data['total_consumable_cost']).rjust(14) + " ₽")
    lines.append("ИТОГО:".ljust(55) + str(data['total']).rjust(14) + " ₽")
    lines.append("=" * 70)
    return chr(10).join(lines)


def export_plumbing_panel_spec(panel_id):
    """Спецификация сантехники по коллектору (TXT)."""
    from core.plumbing_panels import (get_panel, get_routes_by_panel,
                                       get_pipe_label, get_pipe_price,
                                       calc_montage_cost_by_panel,
                                       get_panel_type_label)
    from modules.objects import get_object
    p = get_panel(panel_id)
    if not p:
        return None
    obj = get_object(p.get('object_id')) if p.get('object_id') else None
    obj_name = obj['name'] if obj else '—'

    routes = get_routes_by_panel(panel_id)
    data = calc_montage_cost_by_panel(panel_id)

    lines = []
    lines.append("=" * 70)
    lines.append("СПЕЦИФИКАЦИЯ САНТЕХНИКИ (коллектор)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Объект:      " + str(obj_name))
    lines.append("Коллектор:   " + str(p.get('name') or '?'))
    lines.append("Тип:         " + str(get_panel_type_label(p.get('panel_type'))))
    lines.append("Дата:        " + datetime.now().strftime('%d.%m.%Y'))
    lines.append("")
    lines.append("-" * 70)
    lines.append("№  Труба                    Длина   Цена/м   Сумма")
    lines.append("-" * 70)

    if not routes:
        lines.append("(нет трасс)")
    else:
        for idx, r in enumerate(routes, start=1):
            pipe_label = get_pipe_label(r.get('pipe_type'))
            length = r.get('length_m') or 0
            price_m = get_pipe_price(r.get('pipe_type'))
            summa = round(length * price_m, 2)
            lines.append(
                str(idx).ljust(3) +
                pipe_label[:22].ljust(23) +
                str(length).rjust(6) +
                str(price_m).rjust(9) +
                str(summa).rjust(10)
            )

    lines.append("-" * 70)
    lines.append("Трубы:".ljust(55) + str(data['total_pipe_cost']).rjust(14) + " ₽")
    lines.append("Расходники:".ljust(55) + str(data['total_consumable_cost']).rjust(14) + " ₽")
    lines.append("ИТОГО:".ljust(55) + str(data['total']).rjust(14) + " ₽")
    lines.append("=" * 70)
    return chr(10).join(lines)
