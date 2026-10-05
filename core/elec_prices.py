"""core.elec_prices — Цены компонентов ЭОМ.

Источники (по приоритету):
1. elec_panel_components.price_unit (ручная цена на конкретный компонент)
2. component_prices (справочник по типу/номиналу/полюсам/бренду)
3. spec.COMPONENT_PRICES_DEFAULT (дефолтные)

Задел на будущее:
- source='marketplace' — цена получена с Ozon/WB/Leroy/Петрович
- market_url — ссылка на товар
- market_sku — артикул поставщика
"""
from core.db import fetchone, fetchall, commit
from core import spec


# ============================================================
# ПОЛУЧЕНИЕ ЦЕНЫ
# ============================================================

def get_component_price(component_type, rating=None, poles=None, brand=None):
    """Возвращает цену компонента.

    Приоритет:
    1. component_prices (точное совпадение type+rating+poles+brand)
    2. component_prices (type+rating+poles)
    3. component_prices (type+poles)
    4. component_prices (type)
    5. spec.COMPONENT_PRICES_DEFAULT
    """
    # 1-4. Ищем в БД
    queries = [
        ("component_type = ? AND rating = ? AND poles = ? AND brand = ?",
         (component_type, rating, poles, brand)),
        ("component_type = ? AND rating = ? AND poles = ?",
         (component_type, rating, poles)),
        ("component_type = ? AND poles = ?",
         (component_type, poles)),
        ("component_type = ?", (component_type,)),
    ]
    for where, params in queries:
        try:
            row = fetchone(
                "SELECT price FROM component_prices WHERE " + where + " ORDER BY updated_at DESC LIMIT 1",
                params
            )
            if row and row['price']:
                return float(row['price'])
        except Exception:
            pass

    # 5. Дефолт
    try:
        return float(spec.get_default_price(component_type, poles))
    except Exception:
        return 0.0


def get_price_info(component_type, rating=None, poles=None, brand=None):
    """Возвращает dict: price, source, market_url, market_sku, brand."""
    queries = [
        ("component_type = ? AND rating = ? AND poles = ? AND brand = ?",
         (component_type, rating, poles, brand)),
        ("component_type = ? AND rating = ? AND poles = ?",
         (component_type, rating, poles)),
        ("component_type = ? AND poles = ?",
         (component_type, poles)),
        ("component_type = ?", (component_type,)),
    ]
    for where, params in queries:
        try:
            row = fetchone(
                "SELECT * FROM component_prices WHERE " + where + " ORDER BY updated_at DESC LIMIT 1",
                params
            )
            if row and row['price']:
                return {
                    'price': float(row['price']),
                    'source': row['source'] or 'db',
                    'market_url': row['market_url'],
                    'market_sku': row['market_sku'],
                    'brand': row['brand'],
                }
        except Exception:
            pass
    # Дефолт
    try:
        return {
            'price': float(spec.get_default_price(component_type, poles)),
            'source': 'spec',
            'market_url': None,
            'market_sku': None,
            'brand': None,
        }
    except Exception:
        return {'price': 0.0, 'source': 'none', 'market_url': None,
                'market_sku': None, 'brand': None}


# ============================================================
# УСТАНОВКА ЦЕНЫ
# ============================================================

def set_component_price(component_type, price, rating=None, poles=None,
                       brand=None, source='manual', market_url=None,
                       market_sku=None, currency='RUB'):
    """Устанавливает/обновляет цену в справочнике.

    Ищет существующую запись по (type, rating, poles, brand):
    - если есть → UPDATE
    - если нет → INSERT
    """
    # Проверяем существующую
    if brand:
        row = fetchone(
            """SELECT id FROM component_prices
               WHERE component_type = ? AND rating IS ? AND poles IS ? AND brand = ?
               LIMIT 1""",
            (component_type, rating, poles, brand)
        )
    else:
        row = fetchone(
            """SELECT id FROM component_prices
               WHERE component_type = ? AND rating IS ? AND poles IS ? AND brand IS NULL
               LIMIT 1""",
            (component_type, rating, poles)
        )

    if row:
        commit(
            """UPDATE component_prices
               SET price = ?, source = ?, market_url = ?, market_sku = ?,
                   currency = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (price, source, market_url, market_sku, currency, row['id'])
        )
        return row['id']
    else:
        return commit(
            """INSERT INTO component_prices
               (component_type, rating, poles, brand, price, currency,
                source, market_url, market_sku)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (component_type, rating, poles, brand, price, currency,
             source, market_url, market_sku)
        )


def delete_component_price(price_id):
    commit("DELETE FROM component_prices WHERE id = ?", (price_id,))
    return True


def list_component_prices(component_type=None):
    if component_type:
        rows = fetchall(
            "SELECT * FROM component_prices WHERE component_type = ? ORDER BY rating, poles, brand",
            (component_type,)
        )
    else:
        rows = fetchall(
            "SELECT * FROM component_prices ORDER BY component_type, rating, poles, brand"
        )
    return [dict(r) for r in rows]


# ============================================================
# ЗАГЛУШКИ ДЛЯ БУДУЩЕЙ ИНТЕГРАЦИИ С МАРКЕТПЛЕЙСАМИ
# ============================================================

def fetch_marketplace_prices(query, marketplace='ozon'):
    """[ЗАГЛУШКА] Получить цены с маркетплейса.

    В будущем:
    - Ozon Seller API / Ozon открытый API
    - Wildberries API
    - Leroy Merlin парсер
    - Petrovich API
    - Яндекс.Маркет

    Возвращает список: [{price, url, sku, brand, source}, ...]
    """
    return []


def import_prices_from_csv(path, source='import'):
    """[ЗАГЛУШКА] Импорт прайса из CSV.

    Формат: component_type,rating,poles,brand,price,currency,market_url,market_sku
    """
    import csv
    count = 0
    try:
        with open(path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    set_component_price(
                        component_type=row.get('component_type'),
                        price=float(row.get('price', 0)),
                        rating=int(row['rating']) if row.get('rating') else None,
                        poles=int(row['poles']) if row.get('poles') else None,
                        brand=row.get('brand') or None,
                        source=source,
                        market_url=row.get('market_url') or None,
                        market_sku=row.get('market_sku') or None,
                        currency=row.get('currency') or 'RUB',
                    )
                    count += 1
                except Exception as e:
                    print("import row error: " + str(e), flush=True)
    except Exception as e:
        print("import csv error: " + str(e), flush=True)
    return count


# ============================================================
# ОБЩАЯ СМЕТА ЭОМ ОБЪЕКТА
# ============================================================

def calc_object_panels_cost(object_id):
    """Сумма по всем щитам объекта (компоненты)."""
    from core.elec_panels import get_panels, calc_panel_cost
    panels = get_panels(object_id)
    total = 0.0
    by_panel = {}
    for p in panels:
        c = calc_panel_cost(p['id'])
        total += c
        by_panel[p['id']] = {'name': p.get('name') or '?', 'cost': c}
    return {
        'total': round(total, 2),
        'panels_count': len(panels),
        'by_panel': by_panel,
    }


def calc_object_montage_cost(object_id):
    """Сумма электромонтажа по всем щитам объекта (кабель + расходники)."""
    from core.elec_panels import get_panels
    from core import elec_routes as routes_mod
    panels = get_panels(object_id)
    total_cable = 0.0
    total_cons = 0.0
    total_m = 0.0
    by_cable = {}
    by_route = {}
    for p in panels:
        try:
            s = routes_mod.calc_montage_cost_by_panel(p['id'])
        except Exception as e:
            print("montage cost panel: " + str(e), flush=True)
            continue
        total_cable += s['total_cable_cost']
        total_cons += s['total_consumable_cost']
        total_m += s['total_m']
        for k, v in s['by_cable'].items():
            by_cable[k] = by_cable.get(k, 0) + v
        for k, v in s['by_route'].items():
            by_route[k] = by_route.get(k, 0) + v
    return {
        'total_m': round(total_m, 2),
        'total_cable_cost': round(total_cable, 2),
        'total_consumable_cost': round(total_cons, 2),
        'total': round(total_cable + total_cons, 2),
        'by_cable': {k: round(v, 2) for k, v in by_cable.items()},
        'by_route': {k: round(v, 2) for k, v in by_route.items()},
    }


def calc_object_elec_total(object_id):
    """Общая смета ЭОМ объекта = щиты + электромонтаж + работы."""
    panels = calc_object_panels_cost(object_id)
    montage = calc_object_montage_cost(object_id)
    # Работы (если модуль доступен)
    works = {'total': 0, 'works_count': 0, 'by_type': {}}
    try:
        from core import object_works as _ow
        works = _ow.calc_object_works_cost(object_id)
    except Exception:
        pass
    return {
        'panels_cost': panels['total'],
        'panels_count': panels['panels_count'],
        'panels_breakdown': panels['by_panel'],
        'montage_cable_cost': montage['total_cable_cost'],
        'montage_consumable_cost': montage['total_consumable_cost'],
        'montage_total': montage['total'],
        'montage_meters': montage['total_m'],
        'montage_by_cable': montage['by_cable'],
        'montage_by_route': montage['by_route'],
        'works_total': works['total'],
        'works_count': works['works_count'],
        'works_by_type': works['by_type'],
        'total': round(panels['total'] + montage['total'] + works['total'], 2),
    }


def format_object_elec_total(object_id):
    """Текстовая общая смета ЭОМ объекта."""
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj['name'] if obj else ('Объект #' + str(object_id))

    data = calc_object_elec_total(object_id)
    lines = ["💰 Смета ЭОМ объекта «" + str(obj_name) + "»", ""]

    # Щиты
    lines.append("Щиты:")
    lines.append("Всего щитов: " + str(data['panels_count']))
    for pid, info in data['panels_breakdown'].items():
        lines.append("  " + str(info['name']) + ": " + str(info['cost']) + " ₽")
    lines.append("Итого щиты: " + str(data['panels_cost']) + " ₽")
    lines.append("")

    # Электромонтаж
    lines.append("Электромонтаж:")
    lines.append("Метраж: " + str(data['montage_meters']) + " м")
    lines.append("")
    lines.append("Кабель:")
    if data['montage_by_cable']:
        for ctype, cost in sorted(data['montage_by_cable'].items(), key=lambda x: -x[1]):
            lines.append("  " + str(ctype) + ": " + str(cost) + " ₽")
    else:
        lines.append("  нет")
    lines.append("")
    lines.append("Расходники:")
    if data['montage_by_route']:
        for rtype, cost in sorted(data['montage_by_route'].items(), key=lambda x: -x[1]):
            lines.append("  " + str(rtype) + ": " + str(cost) + " ₽")
    else:
        lines.append("  нет")
    lines.append("")
    lines.append("Кабель: " + str(data['montage_cable_cost']) + " ₽")
    lines.append("Расходники: " + str(data['montage_consumable_cost']) + " ₽")
    lines.append("Итого монтаж: " + str(data['montage_total']) + " ₽")
    lines.append("")

    # Работы
    lines.append("Работы:")
    if data.get('works_count'):
        lines.append("Всего работ: " + str(data['works_count']))
        lines.append("Итого работы: " + str(data['works_total']) + " ₽")
    else:
        lines.append("нет")
    lines.append("")

    # Итого
    lines.append("───")
    lines.append("💰 ВСЕГО ЭОМ: " + str(data['total']) + " ₽")

    return chr(10).join(lines)
