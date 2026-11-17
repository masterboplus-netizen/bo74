# CODE_MAP — карта кода Хераборины

> Обновлять при значимых изменениях.
> Номера строк плавают — всегда сверять через grep -n.

## Файлы (по состоянию 2026-10-16)
| Файл | Строк | Что |
|---|---|---|
| app.js | 473 | логика UI |
| style.css | 509 | стили |
| index.html | 61 | разметка |
| crypto.js | 62 | AES-256-GCM |
| sw.js | — | Service Worker |
| encrypt.py | 60 | шифрование JSON |

## app.js — карта функций
| Строка | Функция | Что |
|---|---|---|
| 12 | _bootstrap() | bootstrap |
| 24 | init() | async, старт |
| 44 | setupTabs() | вкладки |
| 52 | switchTab(name) | переключение вкладок |
| 73 | renderDiary() | дневник (сессии по датам) |
| 124 | formatDiaryDate(iso) | формат даты для дневника |
| 132 | showScreen(name) | переключение экранов |
| 141 | lock() | блокировка |
| 150 | setupPinPad() | PIN-пад |
| 163 | onPinKey(key) | ввод символа |
| 179 | updatePinDisplay() | обновление индикаторов |
| 190 | submitPin(pin) | отправка PIN |
| 205 | tryUnlock(pin) | fetch + decrypt |
| 218 | renderDashboard() | дашборд |
| 233 | fmtH(min) | минуты → "Чч Мм" |
| 239 | calcTotals() | расчёты: today/week/month/total |
| 270 | renderMetrics() | 6 метрик |
| 289 | renderProjects() | карточки проектов с фазами |
| 396 | renderChart() | гистограмма 30 дней |
| 431 | renderSessions() | таблица сессий |
| 467 | renderFooter() | футер |

## style.css — ключевые классы
- .tabs / .tab / .tab-active — вкладки
- .metrics / .metric / .metric-label / .metric-value — метрики
- .project-card / .progress-bar / .progress-fill — проект
- .phases / .phase / .phase-bar / .phase-fill — фазы
- .chart-days / .chart-day / .chart-bar — гистограмма
- .sessions-table — таблица
- .diary-date / .diary-item / .diary-time / .diary-proj / .diary-note / .diary-counters — дневник

## CSS-переменные (:root)
--bg, --bg2, --bg3, --border, --fg, --fg-dim, --accent, --green, --yellow, --red

## index.html — структура
- #pin-screen — экран PIN
- #dashboard (.screen.hidden)
  - .topbar — заголовок + lock
  - .tabs — кнопки: Дашборд / Дневник
  - #content — main дашборда
  - #content-diary — main дневника
- #loading — экран расшифровки

## worklog.json — схема
- version, updated, gap_rule_minutes
- baseline: {minutes, messages, screens, note}
- projects[]: {id, name, color, status, started, plan[]: {phase, status, items[]: {text, done}}}
- sessions[]: {id, date, project, start, end, duration_min, events, screens, note}

## Логика calcTotals (важно)
- Считает today / week (7 дней) / month (30 дней) / total.
- baseline (архив) прибавляется ТОЛЬКО к total и msgs.
- Возвращает: {total, week, month, todayMin, screens, msgs, count}.

## Логика renderChart (важно)
- Фиксировано 30 дней (нельзя выбрать период).
- Строит byDay{}: date → сумма duration_min.
- max = max(60, max_duration) — минимальная шкала 60.
- Для каждого дня: h = val ? max(4, round(val/max*100)) : 2 (пустой — 2%).
- Подписи через title="date: duration".
