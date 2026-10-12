# HANDOFF — как войти в проект «Бо 8.1»

> Для нового чата с AI. Прочитай ПЕРВЫМ.
> Дата: 2026-10-12 22:20. Сессия: 15.

---

## 1. ЧТО ЭТО

«Бо 8.1» — цифровая экосистема для строительной компании. Telegram-бот + SQLite + Python 3.13.
Стек: python-telegram-bot[job-queue], APScheduler, reportlab, openpyxl, rapidfuzz.
Andrey — автор, работает с мобилы через Replit Shell + VPN, скрин = 40 строк.
AI — ведёт патчи, следит за архитектурой, разбивает God Objects.

---

## 2. ПРАВИЛА (ЖЁСТКО)

- Один патч → один py_compile → один скрин → один коммит.
- НЕ давать 2+ команд в одном сообщении, если могут упасть.
- Номера строк УСТАРЕВАЮТ после каждого патча. Перед патчем — ВСЕГДА свежий grep -n.
- Перед рискованным патчем — cp file file.bak_name_$(date +%s)
- Если OLD_NOT_FOUND — не гадать, прислать sed -n + cat -A.
- 30 минут без движения → СТОП, откат, читаем STATE.md.
- git checkout — наш бэкап.
- Максимум 3 вопроса за раз.

---

## 3. ГДЕ МЫ (сессия 15)

Сделано: handlers/commands.py (4736 строк) → пакет handlers/commands/ с 13 модулями.

Модули (все живые, реэкспорт через __init__.py):
- start.py — start, help_command, _help_text
- personal.py — personal_command, format_personal_summary, personal_keyboard
- receipt.py — 5 receipt-хендлеров
- photos.py — 8 photos-хендлеров
- crm.py — 4 crm-функции
- finance.py — 6 finance-функций
- objects.py — 7 objects-функций
- tasks.py — 15 tasks-функций
- choose_expense.py — 4 функции выбора объекта
- document.py — handle_document (CSV/XLSX)
- keyboards.py — main_menu_keyboard
- add_menu.py — handle_add_menu
- _legacy.py — ЧТО ОСТАЛОСЬ: handle_callback (2055), handle_text (975), parse_date (156)

Стратегия разреза (проверена):
1. Вырезать блок строк из _legacy.py → новый файл модуля
2. В _legacy.py — импорт: from handlers.commands.X import Y
3. __init__.py — дописать реэкспорт
4. py_compile → перезапуск → тест → коммит

---

## 4. ТЕХДОЛГ

A. parse_date (156 строк) — циклический импорт (_legacy.py:2538 импортирует сам себя). Вынести в utils.py.

B. handle_callback (2055) и handle_text (975) — монстры. Резать по доменам отдельной сессией. НЕ в спешке.

C. rooms.py (7638 строк) — следующий God Object. Домены: walls, openings, comms, elec, plumbing, reports, core.

D. Универсальный приёмник файлов — handle_document сейчас только CSV/XLSX-прайсы. Нужно: определять тип (прайс / счёт комплектации / счёт оплаты / накладная / чек) → роутить.

E. modules/ → core/ — 176 импортов. Стратегия: шим.

---

## 5. ГЛАВНЫЕ ГРАБЛИ

UnboundLocalError из-за локальных импортов:
- Внутри функции есть from modules.X import Y
- Вызов Y() ВЫШЕ этого импорта → UnboundLocalError
- Фикс: удалить локальные импорты, глобальный покрывает
- Уже пофикшено: 18+5+1 (коммиты 0eec77b, 6949b1b, 69c8070)

Номера строк меняются после каждого патча — grep -n перед патчем.

Бэкапы — перед рискованным патчем. git checkout — откат.

---

## 6. КАК РАБОТАТЬ С ANDREY

- Мобила, Replit Shell, VPN моргает — процесс может упасть, это норма.
- Восстановить: ./start_all.sh
- Максимум 3 вопроса.
- Не давать 2+ команд разом.
- Если патч не сработал — sed -n X,Yp file | cat -A.
- «Бо 7.7» / «Бо 8.1» — версии. Сейчас 8.1.

---

## 7. ЕСЛИ СЛОМАЛОСЬ

1. tail -40 bot_start.log — трейсбек
2. Если не запускается: py_compile → git checkout → ./start_all.sh
3. Если кнопка не работает: смотрим callback в логе → grep -n по коду → проверяем pattern в bot.py
4. Message is not modified — try/except с игнором

---

## 8. КОММИТЫ

Формат: feat(модуль): ..., fix(модуль): ..., refactor(модуль): ..., docs(state): ...
git push — через GITHUB_TOKEN в Replit Secrets, не всегда работает.

---

## 9. ЧТО ЧИТАТЬ

1. docs/STATE.md — где мы сейчас
2. docs/BO_MANIFEST.md — манифест
3. docs/HANDOFF.md — этот файл
4. docs/WORKPLAN.md — план
5. docs/UX_PRINCIPLES.md — 18 принципов

---

Всё. Ты в курсе. Погнали.
