"""Утилиты. Вынесено из _legacy.py (сессия 16)."""
from datetime import datetime, date, timedelta
import re


def parse_date(text):
    """Парсит дату из текста. Возвращает date или None"""
    from datetime import datetime, date, timedelta
    import re

    text = text.strip().lower()
    today = date.today()

    if text in ['сегодня', 'today']:
        return today
    if text in ['завтра', 'tomorrow']:
        return today + timedelta(days=1)
    if text in ['послезавтра']:
        return today + timedelta(days=2)
    if text in ['через неделю', 'неделя']:
        return today + timedelta(days=7)

    m = re.search(r'через\s+(\d+)\s*дн', text)
    if m:
        return today + timedelta(days=int(m.group(1)))

    m = re.match(r'^\+(\d+)д?$', text)
    if m:
        return today + timedelta(days=int(m.group(1)))

    weekdays = {
        'понедельник': 0, 'пн': 0,
        'вторник': 1, 'вт': 1,
        'среда': 2, 'ср': 2,
        'четверг': 3, 'чт': 3,
        'пятница': 4, 'пт': 4,
        'суббота': 5, 'сб': 5,
        'воскресенье': 6, 'вс': 6,
    }
    for name, num in weekdays.items():
        if text.startswith(name):
            days_ahead = (num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)

    months = {
        'января': 1, 'январь': 1, 'янв': 1,
        'февраля': 2, 'февраль': 2, 'фев': 2,
        'марта': 3, 'март': 3, 'мар': 3,
        'апреля': 4, 'апрель': 4, 'апр': 4,
        'мая': 5, 'май': 5,
        'июня': 6, 'июнь': 6, 'июн': 6,
        'июля': 7, 'июль': 7, 'июл': 7,
        'августа': 8, 'август': 8, 'авг': 8,
        'сентября': 9, 'сентябрь': 9, 'сен': 9, 'сент': 9,
        'октября': 10, 'октябрь': 10, 'окт': 10,
        'ноября': 11, 'ноябрь': 11, 'ноя': 11,
        'декабря': 12, 'декабрь': 12, 'дек': 12,
    }
    m = re.search(r'(\d{1,2})\s+([а-яё]+)(?:\s+(\d{4}))?', text)
    if m:
        day = int(m.group(1))
        month_name = m.group(2)
        year = int(m.group(3)) if m.group(3) else today.year
        for name, num in months.items():
            if month_name.startswith(name) or name.startswith(month_name):
                try:
                    result = date(year, num, day)
                    if result < today and not m.group(3):
                        result = date(year + 1, num, day)
                    return result
                except:
                    pass

    m = re.search(r'(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?', text)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_str = m.group(3)
        if year_str:
            year = int(year_str)
            if year < 100:
                year += 2000
        else:
            year = today.year
        try:
            result = date(year, month, day)
            if result < today and not year_str:
                result = date(year + 1, month, day)
            return result
        except:
            pass

    m = re.match(r'^(\d{1,2})$', text)
    if m:
        day = int(m.group(1))
        if 1 <= day <= 31:
            try:
                result = date(today.year, today.month, day)
                if result < today:
                    if today.month == 12:
                        result = date(today.year + 1, 1, day)
                    else:
                        result = date(today.year, today.month + 1, day)
                return result
            except:
                pass

        # "6дек" — день + месяц слитно
    m = re.match(r'^(\d{1,2})([а-яё]{3,})(?:\s*(\d{4}))?$', text)
    if m:
        day = int(m.group(1))
        month_name = m.group(2)
        year_str = m.group(3)
        months = {
            'января': 1, 'январь': 1, 'янв': 1,
            'февраля': 2, 'февраль': 2, 'фев': 2,
            'марта': 3, 'март': 3, 'мар': 3,
            'апреля': 4, 'апрель': 4, 'апр': 4,
            'мая': 5, 'май': 5,
            'июня': 6, 'июнь': 6, 'июн': 6,
            'июля': 7, 'июль': 7, 'июл': 7,
            'августа': 8, 'август': 8, 'авг': 8,
            'сентября': 9, 'сентябрь': 9, 'сен': 9, 'сент': 9,
            'октября': 10, 'октябрь': 10, 'окт': 10,
            'ноября': 11, 'ноябрь': 11, 'ноя': 11,
            'декабря': 12, 'декабрь': 12, 'дек': 12,
        }
        for name, num in months.items():
            if month_name.startswith(name) or name.startswith(month_name):
                year = int(year_str) if year_str else today.year
                try:
                    result = date(year, num, day)
                    if result < today and not year_str:
                        result = date(year + 1, num, day)
                    return result
                except:
                    pass

    # "20 9" — день месяц через пробел
    m = re.match(r'^(\d{1,2})\s+(\d{1,2})(?:\s+(\d{4}))?$', text)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_str = m.group(3)
        if year_str:
            year = int(year_str)
        else:
            year = today.year
        try:
            result = date(year, month, day)
            if result < today and not year_str:
                result = date(year + 1, month, day)
            return result
        except:
            pass

    return None
