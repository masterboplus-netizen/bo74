# AI_INSTRUCTIONS — правила для AI-чата (читать ПЕРВЫМ)

> Для нового AI в чате с Andrey (проект Бо 8.1).
> Читать ПЕРЕД любым действием. Здесь — то, что AI обязан делать САМ.

---

## 1. ЧТО ЧИТАТЬ В НАЧАЛЕ СЕССИИ

1. docs/AI_INSTRUCTIONS.md ← этот файл
2. docs/HANDOFF.md — как войти в проект
3. docs/STATE.md — где мы сейчас
4. docs/CODE_MAP_AUTO.md — авто-карта (обновить: python3 tools/map_scan.py > docs/CODE_MAP_AUTO.md)

---

## 2. ПРАВИЛА РАБОТЫ (ЖЁСТКО)

- Один патч → py_compile → рестарт → тест → коммит.
- Одна команда — один блок. Не давать 2+ команд разом.
- Номера строк плавают. Перед патчем — свежий grep или show_structure.
- Бэкап перед риском: cp file file.bak_ИМЯ_$(date +%Y%m%d_%H%M%S)
- Откат: git checkout path/to/file.py
- Если assert упал — файл не тронут.
- ПОСЛЕ ВЫНОСА: AST-проверка + regex return→return True + grep на дубли роутеров.
- ПЕРЕД правкой роутера: python3 tools/show_structure.py file from to
- ПОСЛЕ правки роутера: python3 tools/lint_routers.py file

---

## 3. ХЕРАБОРИНА — УЧЁТ ВРЕМЕНИ (AI ДЕЛАЕТ САМ)

### Что это
worklog-app/ — PWA-трекер времени. Отдельный репо, не часть Бо.
- Репо: github.com/masterboplus-netizen/worklog
- Хостинг: https://masterboplus-netizen.github.io/worklog/
- PIN: 201186 (НЕ в git!)
- Данные: worklog.json → encrypt.py → data.encrypted.json

### КОГДА ЗАПИСЫВАТЬ
AI обязан записать сессию:
1. В конце каждого диалога (перед прощанием).
2. Когда Andrey говорит «всё, спать» / «продолжим позже».
3. При разрыве > 15 минут — закрыть старую, начать новую.
4. Если Andrey напомнил — записать немедленно.

### КАК СЧИТАТЬ (AI САМ, не спрашивает)
Время start/end:
- AI НЕ видит время сообщений в чате.
- Время берётся из СКРИНОВ — в правом верхнем углу (ЧЧ:ММ).
- Первый скрин сессии → start, последний → end.
- Если скринов нет — спросить Andrey (крайний случай).

Duration:
- end - start минус паузы > 15 мин. Округление до минут.

Events (сообщения):
- Каждое сообщение Andrey: текст=1, скрин=1, текст+скрин=1.
- AI считает сам по диалогу.

Screens:
- Отдельно каждое изображение. AI считает сам.

### ФОРМАТ
{"id": "s_ГГГГММДД_N", "date": "ГГГГ-ММ-ДД", "project": "bo81",
 "start": "ЧЧ:ММ", "end": "ЧЧ:ММ", "duration_min": ЧИСЛО,
 "events": ЧИСЛО, "screens": ЧИСЛО, "note": "..."}
N — номер сессии в этот день (1, 2, 3...).

---

### АЛГОРИТМ (4 команды, по одной)

1) Добавить сессию:
cd ~/workspace/worklog-app && python3 -c "
import json
d = json.load(open('worklog.json', encoding='utf-8'))
d['updated'] = 'ГГГГ-ММ-ДДTЧЧ:ММ:00'
new = {'id':'s_ГГГГММДД_N','date':'ГГГГ-ММ-ДД','project':'bo81','start':'ЧЧ:ММ','end':'ЧЧ:ММ','duration_min':ЧИСЛО,'events':ЧИСЛО,'screens':ЧИСЛО,'note':'...'}
ids=[s['id'] for s in d['sessions']]
if new['id'] in ids:
  for i,s in enumerate(d['sessions']):
    if s['id']==new['id']: d['sessions'][i]=new; print('REPLACED')
else:
  d['sessions'].append(new); print('APPENDED')
json.dump(d, open('worklog.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)
print('sessions total:', len(d['sessions']))
"

2) Проверка JSON:
cd ~/workspace/worklog-app && python3 -m json.tool worklog.json > /dev/null && echo "JSON OK"

3) Шифрование:
cd ~/workspace/worklog-app && WORKLOG_PIN='201186' .venv/bin/python encrypt.py

4) Push:
cd ~/workspace/worklog-app && git add worklog.json data.encrypted.json && git commit -m "data: session ГГГГ-ММ-ДД #N" && git push origin main 2>&1 | tail -3

### ПРОЕКТЫ И ФАЗЫ
- worklog.json → projects[].plan[] — 11 фаз Бо, 44 пункта.
- Формат: {"text": "...", "done": true|false}.

### BASELINE
- worklog.json → baseline: {minutes: 20160, messages: 7473, screens: 0}.
- Оценка июль–сентябрь 2026: 7473 msg × 2.7 мин.

### ВАЖНО
- PIN 201186 — НЕ в git.
- .venv/bin/python — обязательно (cryptography).
- После правки worklog.json → encrypt.py → push.
- Cache-bust: index.html ?v=N для app.js/style.css.

---

## 4. ГРАБЛИ (ОСНОВНЫЕ)

1. Висячий return True вне if — вернёт True для ЛЮБОГО callback.
   Проверка: python3 tools/lint_routers.py <file>
2. Локальные from modules.X import Y внутри функций → NameError.
3. Голый return вместо return True → задвоение.
4. Дубли роутеров — дважды вызывается try_handle.
5. Плавающие номера строк после патча.
6. Отступ 4 vs 8 в роутерах — критично для if/return.

---

## 5. ИНСТРУМЕНТЫ

| Инструмент | Назначение |
|---|---|
| tools/show_structure.py <file> <from> <to> | Файл с отступами |
| tools/map_scan.py > docs/CODE_MAP_AUTO.md | Авто-карта колбэков |
| tools/lint_routers.py <file> | Линтер роутеров |

---

## 6. ЧЕГО AI НЕ ДЕЛАЕТ

- НЕ спрашивает Andrey «во сколько начали?» — считает по скринам.
- НЕ спрашивает «сколько сообщений?» — считает сам.
- НЕ откладывает запись в Хераборину — пишет в конце сессии.
- НЕ даёт 2+ команды в одном блоке.
- НЕ патчит без свежего grep/show_structure.
- НЕ коммитит без теста.

---

*Обновлять при изменении процессов.*

---

## 7. АРХИТЕКТУРА РОУТИНГА (3 УРОВНЯ)

Callback'и в Бо обрабатываются в ТРЁХ местах:

### Уровень 1: bot.py — прямые CallbackQueryHandler
app.add_handler(CallbackQueryHandler(handler, pattern="^prefix"))

Здесь живут: recognize_receipt, receipt_*, photofilt_*, cat_*, task_*,
photo_*, menu_add, add_*, choose_obj_*, confirmdate_*.
Парсится сканером map_scan.py (с версии 3).

---

### Уровень 2: _legacy.py → callbacks/*.py
handle_callback → _try_<domain>_cb(data, query, context).
Роутеры: tasks, estimates, kpi, finance, objects, reports, misc, personal.

### Уровень 3: _legacy.py → text/*.py
handle_text → try_handle(update, context, text).
Домены: fallback, crm, finances, misc, objects, personal, rooms, tasks.

### ПРАВИЛО
- Прежде чем искать роутер — обнови карту: python3 tools/map_scan.py > docs/CODE_MAP_AUTO.md
- Если префикса нет в карте — возможно, он в bot.py (см. выше).
- НЕ патчить роутеры вслепую — сначала grep по всем трём уровням.
