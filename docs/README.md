# 📚 КАРТА ДОКУМЕНТАЦИИ «БО»

## 🚨 ГЛАВНОЕ ПРАВИЛО ДЛЯ ИИ (ЧИТАТЬ ПЕРВЫМ)

1. **Формат ссылок:** Всегда давай ссылки в виде блока кода.
2. **Получение кода:** Пользователь сам присылает Raw-ссылки (raw.githubusercontent.com). Не нужно просить его копировать текст в чат.
3. **Группировка:** Если нужно несколько ссылок, они должны быть в ОДНОМ блоке кода (каждая на новой строке). Не разбивай их на отдельные блоки.
4. **Алгоритм начала работы:** 
   - Сначала спроси пользователя: «Над каким проектом работаем?» (Ядро, Telegram, Веб, Хераборина).
   - Дождись ответа.
   - Затем пришли все Raw-ссылки на документы ЭТОГО проекта **одним блоком кода**.

**Пример правильной ссылки (одна):**
```text
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/core/geometry.py
```

**Пример правильной группировки (несколько ссылок в ОДНОМ блоке):**
```text
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/KHERABORINA_INSTRUCTIONS.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/CODE_MAP.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/TODO.md
```


> **Дата:** 2026-10-25
> **Главное правило:** Старые документы лежат в папке /docs (архив). Мы работаем только с этой новой структурой.

## 📌 ТОЧНЫЕ RAW-ССЫЛКИ ДЛЯ КАЖДОГО ПРОЕКТА

**01_BO_CORE (Ядро):**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/01_BO_CORE/MANIFEST.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/01_BO_CORE/STATE.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/01_BO_CORE/RULES.md

**02_BO_TELEGRAM (Бот):**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/02_BO_TELEGRAM/UI_MAP.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/02_BO_TELEGRAM/STATE_BOT.md

**03_BO_WEB (Веб):**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/03_BO_WEB/WEB_STATE.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/03_BO_WEB/API.md

**05_KHERABORINA (Трекер):**
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/KHERABORINA_INSTRUCTIONS.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/CODE_MAP.md
https://raw.githubusercontent.com/masterboplus-netizen/bo74/main/docs/05_KHERABORINA/TODO.md

## 1. ЯДРО (01_BO_CORE)
Здесь лежит вся бизнес-логика, архитектура и правила работы.
- MANIFEST.md — Философия, суть проекта и масштаб.
- ARCHITECTURE.md — Общая архитектура ядра.
- ARCHITECTURE_ELEC.md — Детальное описание ядра ЭОМ.
- ARCHITECTURE_ESTIMATE.md — Архитектура смет.
- RULES.md — Строгие правила работы (STRICT MODE).
- AI_INSTRUCTIONS.md — Инструкции для настройки ИИ-ассистента.
- STATE.md — Текущее состояние (сессия 20, баги, планы).
- WORKPLAN.md — План и техдолг (P1-P8).
- ROADMAP.md — Глобальный план развития (8 этапов).
- ROADMAP_FLEX.md — Гибкость архитектуры (3-6 стен, двойной свет).
- UX_PRINCIPLES.md — Философия юзабилити.
- HANDOFF.md — Протокол входа для нового ИИ.
- CHANGELOG.md — История версий (от 7.0 до 8.5).
- DEPS.md — Зависимости проекта.
- DEVELOPMENT.md — Правила разработки (git, БД).
- DEVLOG.md — Журнал всех сессий разработки.
- GLOSSARY.md — Словарь терминов.
- measurement_tools.md — ТЗ для замерщика.
- room_3d_model.md — ТЗ для 3D-модели.
- service_zones.md — Проверки габаритов и конфликтов.
- transitions.md — Логика обработки кривых углов.
- MIGRATIONS.md — Описание всех миграций БД.

## 2. TELEGRAM (02_BO_TELEGRAM)
Здесь лежит всё, что касается интерфейса бота.
- UI_MAP.md — Карта кнопок и меню.
- STATE_BOT.md — История рефакторинга кода бота.
- TELEGRAM_ARCHITECTURE.md — 3 уровня обработки callback-ов.
- STYLE_GUIDE.md — Правила оформления UI.
- MASTER_GUIDE.md — Инструкция для мастеров.
- CLIENT_GUIDE.md — Инструкция для заказчиков.

## 3. ВЕБ (03_BO_WEB)
Здесь лежит документация по веб-версии (bo-web).
- WEB_STATE.md — История разработки и ошибки с доменом.
- WEB_ARCHITECTURE.md — Как устроен API и работа с Replit.
- API.md — Черновик REST API для внешних систем.
- PWA_POSTMORTEM.md — Разбор ошибок с PWA.

## 4. ХЕРАБОРИНА (05_KHERABORINA)
Отдельный проект тайм-трекера.
- KHERABORINA_INSTRUCTIONS.md — Правила, PIN, шифрование.
- CODE_MAP.md — Карта кода (app.js, style.css).
- TODO.md — Текущие задачи и баги.
- WORKLOG.md — Краткое описание работы трекера.

## 5. АРХИВ (_ARCHIVE)
Старые снимки кода, бэкапы и устаревшие версии.

**Конец карты документации.**