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
