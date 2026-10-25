# ХЕРАБОРИНА — Инструкции для AI (Правила, данные, шифрование)

> **Хераборина (worklog-app)** — это PWA-трекер времени Andrey. 
> **Важно:** Это отдельный проект, НЕ часть Бо 8.1. 
> Читать перед началом работы с тайм-трекером.

## 1. ЧТО ЧИТАТЬ В НАЧАЛЕ СЕССИИ (по Хераборине)
1. documenty/05_KHERABORINA/KHERABORINA_INSTRUCTIONS.md ← этот файл
2. documenty/01_BO_CORE/HANDOFF.md — как войти в проекты

## 2. ОБЩИЕ ПРАВИЛА РАБОТЫ
- Один патч → тест в браузере → коммит.
- Одна команда — один блок.
- Перед патчем — свежий grep/sed (номера строк плавают).
- Бэкап перед риском: cp file file.bak_ИМЯ_20261025_132751.
- Откат: git checkout path/to/file.

## 3. ПРАВИЛО ПОЛУНОЧИ (КРИТИЧНО)
Сессия НЕ может пересекать полночь. Если Andrey работал с 20:24 до 00:44:
- Создать ДВЕ сессии:
  - s_YYYYMMDD_N (дата старта): 20:24 → 23:59.
  - s_YYYYMMDD+1_1 (следующий день): 00:00 → 00:44.
- Дневник = СЕССИИ (могут быть множественные в один день).
- Вкладка «Время» = ДНИ (уникальные даты, не количество сессий).
- Среднее/день = сумма реальных часов / кол-во уникальных дней.

*Пример: s_20261016_3 (20:24→23:59, 215мин) + s_20261017_1 (00:00→00:44, 44мин).*

## 4. PIN И ДАННЫЕ
- **PIN:** 201186 (НЕ в git!).
- **Данные:** worklog.json → encrypt.py → data.encrypted.json.
- encrypt.py — только .venv/bin/python (системный python3 не имеет cryptography).
- **Команда шифрования:** WORKLOG_PIN='201186' .venv/bin/python encrypt.py

## 5. ОБНОВЛЕНИЕ ДАННЫХ (4 шага)
1) Добавить/правка сессии в worklog.json.
2) Проверка: python3 -m json.tool worklog.json > /dev/null && echo JSON OK
3) Шифрование: WORKLOG_PIN='201186' .venv/bin/python encrypt.py
4) Push: git add worklog.json data.encrypted.json && git commit -m data: ... && git push origin main

## 6. CACHE-BUST — ВАЖНО
Браузер держит старый app.js/style.css.
После правки app.js/style.css → увеличить ?v=N в index.html.
Сейчас v=3.

## 7. ГРАБЛИ
1. **Cache-bust:** забыл поднять ?v=N → пользователь видит старый UI.
2. **encrypt.py системным python3** → ModuleNotFoundError: cryptography.
3. **sed -i на Android (busybox) ломает UTF-8.** Для записи русских строк использовать python3 (Path.read_text/write_text с encoding='utf-8').

## 8. ЧЕГО AI НЕ ДЕЛАЕТ
- НЕ коммитит worklog.json без data.encrypted.json.
- НЕ даёт 2+ команд разом, если могут упасть.
- НЕ патчит вслепую — сначала grep/sed.

## 9. ССЫЛКИ
- Репо: github.com/masterboplus-netizen/worklog
- Хостинг: https://masterboplus-netizen.github.io/worklog/

**Конец инструкций.**