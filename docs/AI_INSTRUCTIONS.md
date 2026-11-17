# AI_INSTRUCTIONS — правила для AI-чата (читать ПЕРВЫМ)

> Хераборина — PWA-трекер времени Andrey. Отдельный проект, НЕ часть Бо 8.1.

## 1. ЧТО ЧИТАТЬ В НАЧАЛЕ СЕССИИ
1. docs/AI_INSTRUCTIONS.md ← этот файл
2. docs/HANDOFF.md — как войти
3. docs/STATE.md — где мы
4. docs/CODE_MAP.md — карта кода

**ПЕРВОЕ СООБЩЕНИЕ НОВОГО ЧАТА (ОБЯЗАТЕЛЬНО):**
Выдать пользователю ОДНИМ блоком raw-ссылки на все доки ВСЕХ активных проектов (Хераборина, Бо 8.1, Бо Веб, ФК Богородское) — чтобы он открыл их одним link box. Никаких cat/curl, никаких нескольких блоков. Один блок, все ссылки, копируется целиком.

## 2. ПРАВИЛА РАБОТЫ
- Один патч → тест в браузере → коммит.
- Одна команда — один блок.
- Перед патчем — свежий grep/sed (номера строк плавают).
- Бэкап перед риском: cp file file.bak_ИМЯ_$(date +%Y%m%d_%H%M%S).
- Откат: git checkout path/to/file.

## 2.1. ПРАВИЛО ПОЛУНОЧИ (КРИТИЧНО)

Сессия НЕ может пересекать полночь. Если Andrey работал с 20:24 до 00:44:
- Создать ДВЕ сессии:
  - s_YYYYMMDD_N (дата старта): 20:24 → 23:59.
  - s_YYYYMMDD+1_1 (следующий день): 00:00 → 00:44.
- Дневник = СЕССИИ (могут быть множественные в один день).
- Вкладка «Время» = ДНИ (уникальные даты, не количество сессий).
- Среднее/день = сумма реальных часов / кол-во уникальных дней.

Пример: s_20261016_3 (20:24→23:59, 215мин) + s_20261017_1 (00:00→00:44, 44мин).

## 3. PIN И ДАННЫЕ
- PIN: 201186 (НЕ в git!).
- worklog.json → encrypt.py → data.encrypted.json.
- encrypt.py — только .venv/bin/python (системный python3 не имеет cryptography).
- Команда шифрования: WORKLOG_PIN='201186' .venv/bin/python encrypt.py

## 4. ОБНОВЛЕНИЕ ДАННЫХ (4 шага)
1) Добавить/правка сессии в worklog.json.
2) Проверка: python3 -m json.tool worklog.json > /dev/null && echo "JSON OK"
3) Шифрование: WORKLOG_PIN='201186' .venv/bin/python encrypt.py
4) Push: git add worklog.json data.encrypted.json && git commit -m "data: ..." && git push origin main

## 5. CACHE-BUST — ВАЖНО
Браузер держит старый app.js/style.css.
После правки app.js/style.css → увеличить ?v=N в index.html.
Сейчас v=3.

## 6. ГРАБЛИ
1. Cache-bust: забыл поднять ?v=N → пользователь видит старый UI.
2. encrypt.py системным python3 → ModuleNotFoundError: cryptography.
3. worklog.json в .gitignore, но закоммичен через git add -f ранее → правки требуют git add (просто, без -f, т.к. уже отслеживается).
4. PIN показывать через showScreen('pin-screen') (не 'pin').
5. Сервис-воркер sw.js — исключает data.encrypted.json из кэша (иначе не расшифруется).
6. sed -i на Android (busybox) ломает UTF-8 (кириллица превращается в кракозябры). Для записи русских строк использовать python3 (Path.read_text/write_text с encoding='utf-8').

## 7. ЧЕГО AI НЕ ДЕЛАЕТ
- НЕ коммитит worklog.json без data.encrypted.json (иначе данные разъедутся).
- НЕ даёт 2+ команд разом, если могут упасть.
- НЕ патчит вслепую — сначала grep/sed.

## 8. ССЫЛКИ
- Репо: github.com/masterboplus-netizen/worklog
- Хостинг: https://masterboplus-netizen.github.io/worklog/
- Локально: ~/workspace/worklog-app/
