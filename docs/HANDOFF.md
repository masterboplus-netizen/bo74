# HANDOFF — как войти в Хераборину

> Для нового чата с AI.
> СНАЧАЛА ЧИТАЙ: docs/AI_INSTRUCTIONS.md
> Дата: 2026-10-17. HEAD: 83becfe. Сессия: Х-2 (закрыта).

## 1. ЧТО ЭТО
PWA-трекер времени Andrey для работы с AI.
Стек: HTML/CSS/JS (vanilla) + Service Worker + AES-256-GCM.
Хостинг: GitHub Pages. Репо: masterboplus-netizen/worklog.

## 2. СТРУКТУРА ФАЙЛОВ
- index.html — входная (PIN + дашборд + дневник). ~61 строк.
- style.css — стили (тёмная тема, CSS-переменные). ~509 строк.
- app.js — вся логика UI. ~473 строк.
- crypto.js — PBKDF2 → AES-256-GCM. ~62 строк.
- sw.js — Service Worker (офлайн-кэш).
- manifest.webmanifest — PWA-манифест.
- icon.svg — иконка.
- encrypt.py — шифрование JSON (только .venv/bin/python).
- worklog.json — исходные данные (в git через add -f).
- data.encrypted.json — публикуется на GitHub Pages.

## 3. КАК ОБНОВИТЬ ДАННЫЕ
См. docs/AI_INSTRUCTIONS.md §4.
Коротко: worklog.json → json.tool → encrypt.py → git push.

## 4. CACHE-BUST
После правки app.js/style.css — увеличить ?v=N в index.html.
Проверить: grep -n "v=" index.html

## 5. ГДЕ МЫ
См. docs/STATE.md §0 (сессия Х-2, 17.10.2026).

Коротко:
- HEAD: 83becfe.
- Дневник: склейка сессий через полночь (одна карточка).
- График: дни недели (День/Неделя), календарный месяц (1-31).
- Hero ring: тап → Сегодня / Последняя сессия (SVG-иконки).
- Тапы на малые кольца: цикл периодов (День/Неделя/Месяц/Всё).
- Вкладка «Проекты»: прогресс-бары фаз + пункты.
- Формат дат: ДД.ММ (в «Последних сессиях» и дневнике).

## 6. ЧТО ДАЛЬШЕ
См. docs/STATE.md §1 (TODO на Х-3):
1. Цель в localStorage (заменить DAILY_GOAL_MIN=720 на ввод).
2. Сравнение столбиков (3 серии: время/сообщения/скрины).
3. Аналитика в «Проектах» (средние, тренды, год).

## 6.1. ГРАБЛИ Х-2 (важно!)
1. Cache-bust: при правке app.js/style.css/crypto.js — обязательно:
   - ?v=N в index.html (все синхронно).
   - CACHE = worklog-vN в sw.js.
   - updateViaCache: 'none' в register().
2. Merge через полночь: осторожно с переменной dates (если потерять — дневник пустой).
3. SVG-иконки: единый стиль (fill=none, stroke=currentColor, stroke-width=2).
4. Тап на элемент: cursor:pointer + addEventListener('click', ...).
