"""core.marketplaces — Маркетплейсы и импорт цен.

Сейчас:
- CSV-импорт прайса (реальный)
- Заглушки для API (Ozon, WB, Леруа, Петрович)

В будущем:
- API маркетплейсов
- Автообновление цен
- Сравнение по поставщикам
"""
import csv
import os
from datetime import datetime
from core.db import fetchall, commit


# ============================================================
# CSV-ИМПОРТ ПРАЙСА (РЕАЛЬНЫЙ)
# ============================================================

def import_prices_csv(path, source='csv', object_id=None):
    """Импорт цен из CSV.

    Формат CSV:
    component_type;rating;poles;brand;price;currency;market_url;market_sku

    Возвращает dict: {ok: bool, imported: N, skipped: M, errors: [...]}
    """
    from core.elec_prices import set_component_price

    if not os.path.exists(path):
        return {'ok': False, 'error': 'file not found', 'imported': 0, 'skipped': 0}

    imported = 0
    skipped = 0
    errors = []

    try:
        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for idx, row in enumerate(reader, start=2):
                try:
                    ctype = (row.get('component_type') or '').strip()
                    if not ctype:
                        skipped += 1
                        continue
                    price_str = (row.get('price') or '').replace(',', '.').strip()
                    if not price_str:
                        skipped += 1
                        continue
                    price = float(price_str)
                    if price <= 0:
                        skipped += 1
                        continue

                    rating = None
                    if row.get('rating'):
                        try:
                            rating = int(float(row['rating']))
                        except Exception:
                            pass
                    poles = None
                    if row.get('poles'):
                        try:
                            poles = int(float(row['poles']))
                        except Exception:
                            pass

                    set_component_price(
                        component_type=ctype,
                        price=price,
                        rating=rating,
                        poles=poles,
                        brand=(row.get('brand') or '').strip() or None,
                        source=source,
                        market_url=(row.get('market_url') or '').strip() or None,
                        market_sku=(row.get('market_sku') or '').strip() or None,
                        currency=(row.get('currency') or 'RUB').strip(),
                    )
                    imported += 1
                except Exception as e:
                    errors.append('Строка ' + str(idx) + ': ' + str(e))
    except Exception as e:
        return {'ok': False, 'error': str(e), 'imported': imported, 'skipped': skipped}

    # Лог импорта
    try:
        commit(
            "INSERT INTO price_imports (object_id, source, rows_count, note) VALUES (?, ?, ?, ?)",
            (object_id, source, imported, 'CSV: ' + os.path.basename(path))
        )
    except Exception:
        pass

    return {'ok': True, 'imported': imported, 'skipped': skipped, 'errors': errors[:5]}


# ============================================================
# ЗАГЛУШКИ ДЛЯ API
# ============================================================

def fetch_ozon_prices(query):
    """[ЗАГЛУШКА] Ozon API."""
    return []


def fetch_wb_prices(query):
    """[ЗАГЛУШКА] Wildberries API."""
    return []


def fetch_leroy_prices(query):
    """[ЗАГЛУШКА] Леруа Мерлен парсер."""
    return []


def fetch_petrovich_prices(query):
    """[ЗАГЛУШКА] Петрович API."""
    return []


# ============================================================
# ПРОСМОТР ИСТОРИИ ИМПОРТОВ
# ============================================================

def list_imports(object_id=None):
    if object_id:
        rows = fetchall(
            "SELECT * FROM price_imports WHERE object_id = ? ORDER BY imported_at DESC",
            (object_id,)
        )
    else:
        rows = fetchall("SELECT * FROM price_imports ORDER BY imported_at DESC LIMIT 50")
    return [dict(r) for r in rows]


def format_imports(object_id=None):
    imports = list_imports(object_id)
    if not imports:
        return "Импортов цен не было."
    lines = ["История импортов цен:", ""]
    for imp in imports[:10]:
        lines.append(
            str(imp.get('imported_at') or '?') +
            " · " + str(imp.get('source') or '?') +
            " · " + str(imp.get('rows_count') or 0) + " строк"
        )
    return chr(10).join(lines)


# ============================================================
# ГЕНЕРАЦИЯ ШАБЛОНА CSV
# ============================================================

def generate_csv_template(path=None):
    """Генерирует шаблон CSV для импорта."""
    if not path:
        path = '/tmp/prices_template.csv'
    with open(path, 'w', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';', lineterminator='\n')
        writer.writerow(['component_type', 'rating', 'poles', 'brand',
                         'price', 'currency', 'market_url', 'market_sku'])
        writer.writerow(['auto', '16', '1', 'EKF', '250', 'RUB',
                         'https://ozon.ru/...', 'EKF-16A-1P'])
        writer.writerow(['uzo', '63', '2', 'EKF', '1500', 'RUB', '', ''])
        writer.writerow(['cable_3x2.5', '', '', 'Кабель', '120', 'RUB', '', ''])
    return path


# ============================================================
# СРАВНЕНИЕ ЦЕН ПОСТАВЩИКОВ
# ============================================================

def compare_component_prices(component_type, rating=None, poles=None):
    """Сравнение цен одного компонента по всем поставщикам.

    Возвращает: [{source, price, market_url, brand, updated_at}, ...] (сортировка по цене).
    """
    rows = fetchall(
        """SELECT price, source, market_url, market_sku, brand, updated_at
           FROM component_prices
           WHERE component_type = ?
             AND (rating IS ? OR rating = ?)
             AND (poles IS ? OR poles = ?)
           ORDER BY price ASC""",
        (component_type, rating, rating, poles, poles)
    )
    return [dict(r) for r in rows]


def format_price_comparison(component_type, rating=None, poles=None):
    """Текстовое сравнение цен по поставщикам."""
    from core import spec
    label = spec.get_default_price(component_type, poles)
    rows = compare_component_prices(component_type, rating, poles)

    lines = [f"💱 Сравнение цен: {component_type}"]
    if rating:
        lines[-1] += f" {rating}А"
    if poles:
        lines[-1] += f" {poles}P"
    lines.append("")

    if not rows:
        lines.append(f"   В БД нет цен. Дефолт из spec: {label} ₽")
        return "\n".join(lines)

    for r in rows:
        src = r.get("source") or "?"
        price = r.get("price") or 0
        brand = r.get("brand") or "—"
        url = r.get("market_url") or ""
        line = f"   • {src}: {price} ₽ ({brand})"
        if url:
            line += f"\n     {url}"
        lines.append(line)

    lines.append("")
    lines.append(f"   Дефолт из spec: {label} ₽")
    return "\n".join(lines)


def list_marketplace_sources():
    """Список доступных источников цен."""
    rows = fetchall(
        "SELECT source, COUNT(*) as cnt FROM component_prices GROUP BY source"
    )
    return [dict(r) for r in rows]


def format_marketplace_sources():
    rows = list_marketplace_sources()
    if not rows:
        return "Источников цен в БД нет."
    lines = ["💱 Источники цен:", ""]
    for r in rows:
        lines.append(f"   • {r['source']}: {r['cnt']} позиций")
    return "\n".join(lines)
