"""Парсер свободного ввода БО 7.7"""
import re
from modules.objects import get_object_by_name, get_all_objects
from modules.tasks import create_task, close_task, get_tasks_by_object, get_active_tasks
from modules.finance import add_expense, add_income, get_finance_summary


def find_all_objects_in_text(text: str):
    """Возвращает ВСЕ найденные объекты (список)"""
    text_lower = text.lower()
    objects = get_all_objects()
    found = []

    # 1. Точный поиск (полное или упрощённое имя)
    for o in objects:
        name_lower = o['name'].lower()
        simple = name_lower.split('(')[0].strip()
        if name_lower in text_lower or (simple and len(simple) > 3 and simple in text_lower):
            found.append(o)

    if found:
        return found

    # 2. Нечёткий поиск — по первым 4 буквам
    for o in objects:
        name_lower = o['name'].lower()
        simple = name_lower.split('(')[0].strip()
        for prefix in [name_lower[:4], simple[:4] if len(simple) >= 4 else simple]:
            if prefix and len(prefix) >= 4 and prefix in text_lower:
                if o not in found:
                    found.append(o)

    return found


def find_object_in_text(text: str):
    """Возвращает первый найденный объект (для обратной совместимости)"""
    found = find_all_objects_in_text(text)
    return found[0] if found else None


def parse_message(text: str) -> dict:
    """Разбирает текст и возвращает действие"""
    text_lower = text.lower().strip()

    # === СПИСКИ ===
    if any(w in text_lower for w in ['задачи', 'что делать', 'список дел']):
        return {'action': 'list_tasks'}
    if any(w in text_lower for w in ['объекты', 'мои объекты', 'стройки']):
        return {'action': 'list_objects'}

    # === ФИНАНСЫ ===
    if any(w in text_lower for w in ['сколько', 'финансы', 'бюджет', 'баланс']):
        found = find_all_objects_in_text(text)
        if found:
            return {'action': 'finance', 'object': found[0]}

    # === РАСХОД ===
    expense_words = ['потратил', 'расход', 'заплатил', 'купил', 'оплатил', 'ушло', 'отдал', 'цена']
    has_expense_word = any(w in text_lower for w in expense_words)

    amount = parse_amount(text_lower)
    found = find_all_objects_in_text(text)

    # === РАСХОД ===
    is_finance_query = any(w in text_lower for w in ['сколько', 'финансы', 'бюджет', 'баланс'])

    if amount and not is_finance_query:
        material_words = ['материал', 'метриал', 'плитк', 'клей', 'краск', 'паркет', 'панел', 'затирк', 'штукатур', 'грунт', 'кабел', 'труб']
        has_material = any(w in text_lower for w in material_words)

        category = 'прочее'
        if has_material:
            for w in material_words:
                if w in text_lower:
                    category = 'материалы'
                    break

        # Объект найден
        if found:
            if len(found) > 1:
                return {
                    'action': 'choose_object',
                    'objects': found,
                    'amount': amount,
                    'category': category,
                    'original_text': text
                }
            return {
                'action': 'expense',
                'object': found[0],
                'amount': amount,
                'category': category
            }

        # Объект НЕ найден, но есть триггер расхода — спрашиваем объект
        if has_expense_word:
            return {
                'action': 'choose_object',
                'objects': get_all_objects(),
                'amount': amount,
                'category': category,
                'original_text': text
            }

    # === ЗАКРЫТЬ ЗАДАЧУ ===
    done_words = ['сделал', 'закрыл', 'выполнил', 'готово', 'покрасил', 'положил', 'собрал', 'установил', 'смонтировал', 'отмыл']
    if any(w in text_lower for w in done_words):
        if found:
            if len(found) > 1:
                return {
                    'action': 'choose_object',
                    'objects': found,
                    'original_text': text,
                    'intent': 'done_task'
                }
            obj = found[0]
            tasks = get_tasks_by_object(obj['id'])
            for t in tasks:
                if t['status'] == 'done':
                    continue
                title_lower = t['title'].lower()
                words = [w for w in title_lower.split() if len(w) > 3]
                for w in words:
                    if w in text_lower:
                        return {'action': 'done_task', 'object': obj, 'task': t}
            return {'action': 'done_task_not_found', 'object': obj, 'query': text_lower}

    # === ДОБАВИТЬ ЗАДАЧУ ===
    add_words = ['добавь', 'добавить', 'задача', 'новая задача', 'надо', 'нужно']
    if any(w in text_lower for w in add_words):
        if found:
            if len(found) > 1:
                return {
                    'action': 'choose_object',
                    'objects': found,
                    'original_text': text,
                    'intent': 'add_task'
                }
            obj = found[0]
            title = text_lower
            for w in add_words:
                title = title.replace(w, '')
            for w in ['в', 'на', 'для']:
                title = title.replace(w, '', 1)
            title = title.replace(obj['name'].lower(), '')
            simple = obj['name'].lower().split('(')[0].strip()
            if simple:
                title = title.replace(simple, '')
            title = title.strip() or text
            return {'action': 'add_task', 'object': obj, 'title': title}

    # === ТОЛЬКО СУММА (без объекта, без триггера) ===
    # Если в тексте только число — спрашиваем: личный расход или по объекту?
    if amount and not found:
        stripped = text_lower.strip()
        # Проверяем: только цифры и пробелы
        if re.match(r'^[\d\s]+$', stripped):
            return {
                'action': 'ask_expense_type',
                'amount': amount,
                'original_text': text
            }

    return {'action': 'unknown', 'text': text}


def parse_amount(text: str):
    """Парсит сумму: 450, 5000, 5к, 5 к, 5К, 5 кк"""
    import re
    text_lower = text.lower().replace(',', '.')

    m = re.search(r'(\d+)\s*кк', text_lower)
    if m:
        return int(m.group(1)) * 1000000

    m = re.search(r'(\d+)\s*к(?!к)', text_lower)
    if m:
        return int(m.group(1)) * 1000

    m = re.search(r'(\d[\d\s]*\d|\d)', text_lower)
    if m:
        digits = re.sub(r'\s+', '', m.group(1))
        if digits.isdigit():
            amount = int(digits)
            if 0 < amount <= 100_000_000:
                return amount

    return None
