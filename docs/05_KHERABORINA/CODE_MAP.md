# CODE_MAP — карта кода Хераборины

> Обновлять при значимых изменениях.
> Номера строк плавают — всегда сверять через grep -n.

## Файлы (по состоянию 2026-10-16)
- app.js (473 строки) — логика UI
- style.css (509 строк) — стили
- index.html (61 строка) — разметка
- crypto.js (62 строки) — AES-256-GCM
- sw.js — Service Worker
- encrypt.py (60 строк) — шифрование JSON

## app.js — карта функций
- init() — async, старт.
- setupTabs() / switchTab(name) — вкладки.
- renderDiary() — дневник (сессии по датам).
- showScreen(name) / lock() — переключение экранов и блокировка.
- setupPinPad() / onPinKey() / submitPin() / tryUnlock() — логика PIN.
- renderDashboard() — дашборд.
- calcTotals() — расчёты: today/week/month/total.
- renderProjects() — карточки проектов с фазами.
- renderChart() — гистограмма 30 дней.
- renderSessions() — таблица сессий.

## Логика calcTotals (важно)
Считает today / week (7 дней) / month (30 дней) / total. baseline (архив) прибавляется ТОЛЬКО к total и msgs.

## Логика renderChart (важно)
Фиксировано 30 дней. Строит byDay: date -> сумма duration_min. max = max(60, max_duration). Для каждого дня: h = val ? max(4, round(val/max*100)) : 2 (пустой — 2%).

**Конец CODE_MAP.md**