# Продолжение работы — ЭОМ (для нового чата)

## Проект
**Бо 7.7** — цифровая экосистема для строительства.
Python 3.13 + SQLite + python-telegram-bot 22.8 + Pillow. Replit.

**Репозиторий:** https://github.com/masterboplus-netizen/bo74
**Админ tg_id:** 1821030188
**Токен:** env BOT_TOKEN

## Что готово (04.10.2026)
Последний коммит: `caa67fa`

- Комнаты: замеры, обход стен, ниши, проёмы, коммуникации
- Помещения (этажи/зоны) — создание, карточка, комнаты
- **ЭОМ:**
  - core/elec.py (521 строка) — группы, автоматы, кабели, фазы L1/L2/L3
  - Миграции 034, 035, 036
  - Создание группы этажа (назначение → фаза → мощность → автоподбор)
- Экспорт: DXF, JSON, CSV, PNG
- Отчёты: 7 листов

## Архитектура

Объект (objects)
  ├─ ЭОМ объекта: ВРУ, ввод, счётчик, вводной автомат
  └─ Помещения (floors) — 1..N
       ├─ ЭОМ этажа: щит + группы этажа
       └─ Комнаты (rooms) — 1..N
            └─ Точки (room_comms) → привязаны к группе этажа

Правила:
- Группа = НА ЭТАЖЕ (elec_groups.floor_id), не в комнате
- Одна группа → много точек в разных комнатах (через room_comms.group_id)
- Одна группа = один автомат в щите этажа

## Что делать
1. Привязка точки к группе — при добавлении розетки в комнату → выбор группы этажа
2. ЭОМ комнаты — группы, обслуживающие комнату
3. ЭОМ этажа — щит + группы + фазы
4. ЭОМ объекта — ВРУ + сводка
5. Кабельный журнал
6. PDF-ЭОМ

## Ключевые файлы
- core/elec.py (521 строка) — ЭОМ
- core/floors.py (109 строк) — помещения
- core/spec.py — справочники (9 групп, 9 кабелей, 15 кухонных)
- core/visualize.py — рендер плана
- interfaces/telegram/rooms.py (~4500 строк) — UI
- handlers/commands.py (~4300 строк) — роутинг

## Функции core/elec.py
- create_group(object_id, floor_id, name, ...)
- get_groups_by_floor(floor_id)
- get_groups_by_room(room_id)
- get_rooms_by_group(group_id)
- assign_comm_to_group(comm_id, group_id)
- calc_balance(object_id)
- pick_breaker / pick_cable

## Правила работы
- Бо на мобиле, nano не работает
- Команды одной строкой
- venv/bin/python3 для проверок
- Перезапуск: pkill -9 -f "python bot.py" ; pkill -9 -f "watchdog" ; sleep 2 ; ./start_all.sh
- Коммит: git add -A ; git commit -m "..." ; git push

## Первый запрос
Прочитай core/elec.py, core/floors.py, interfaces/telegram/rooms.py.
Погнали: привязка точки к группе + ЭОМ этажа.
