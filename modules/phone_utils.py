"""Утилиты для валидации и нормализации телефонов (умные варианты)."""
import re

COUNTRY_CODES = ['7', '1', '44', '49', '33', '39', '34', '48', '90', '380', '375', '995', '972', '971', '86', '81', '82', '66', '84', '91']

def _clean(raw):
    """Оставляет только цифры."""
    if not raw:
        return ''
    return re.sub(r'[^\d]', '', str(raw).strip())

def _is_valid(digits):
    """10-15 цифр, начинается с известного кода."""
    if not (10 <= len(digits) <= 15):
        return False
    return any(digits.startswith(cc) for cc in COUNTRY_CODES)

def parse_phone(raw):
    """Возвращает dict:
    {'status': 'ok', 'phone': '+7...'} — норм
    {'status': 'suggest', 'variants': ['+7...', ...]} — предложить варианты
    {'status': 'invalid', 'reason': '...'} — плохо
    """
    if not raw:
        return {'status': 'invalid', 'reason': 'пусто'}

    digits = _clean(raw)
    if not digits:
        return {'status': 'invalid', 'reason': 'нет цифр'}

    # 11 цифр с 8 → +7XXXXXXXXXX
    if len(digits) == 11 and digits.startswith('8'):
        return {'status': 'ok', 'phone': '+7' + digits[1:]}

    # 11 цифр с 7 → +7XXXXXXXXXX
    if len(digits) == 11 and digits.startswith('7'):
        return {'status': 'ok', 'phone': '+' + digits}

    # 10 цифр с 9 → +79XXXXXXXXX (мобильный РФ)
    if len(digits) == 10 and digits.startswith('9'):
        return {'status': 'ok', 'phone': '+7' + digits}

    # 10 цифр с 7 в начале — возможно, человек забыл одну цифру.
    # Показываем варианты: +7XXXXXXXXXX и 7XXXXXXXXX (без +)
    if len(digits) == 10 and digits.startswith('7'):
        return {'status': 'suggest', 'variants': ['+7' + digits, '+' + digits]}

    # 10-15 цифр с известным кодом — как есть (для +44, +49 и т.д.)
    if len(digits) >= 11 and _is_valid(digits):
        return {'status': 'ok', 'phone': '+' + digits}

    # 8-9 цифр — слишком короткий. Не угадываем.
    if len(digits) < 10:
        return {'status': 'invalid', 'reason': f'слишком короткий ({len(digits)} цифр)'}

    # Всё остальное — invalid
    return {'status': 'invalid', 'reason': f'слишком короткий ({len(digits)} цифр)'}

def normalize_phone(raw, default_country='7'):
    """Совместимость со старым API: возвращает номер или None."""
    result = parse_phone(raw)
    if result.get('status') == 'ok':
        return result.get('phone')
    return None

def get_country_label(phone):
    """Определяет страну по коду."""
    if not phone:
        return '—'
    p = phone.lstrip('+')
    codes = {
        '7': '🇷🇺 Россия/Казахстан', '1': '🇺🇸 США/Канада',
        '44': '🇬🇧 Великобритания', '49': '🇩🇪 Германия',
        '33': '🇫🇷 Франция', '39': '🇮🇹 Италия',
        '34': '🇪🇸 Испания', '48': '🇵🇱 Польша',
        '90': '🇹🇷 Турция', '380': '🇺🇦 Украина',
        '375': '🇧🇾 Беларусь', '995': '🇬🇪 Грузия',
        '972': '🇮🇱 Израиль', '971': '🇦🇪 ОАЭ',
        '86': '🇨🇳 Китай', '81': '🇯🇵 Япония', '82': '🇰🇷 Корея',
    }
    for code in sorted(codes.keys(), key=len, reverse=True):
        if p.startswith(code):
            return codes[code]
    return '🌍 Другая'
