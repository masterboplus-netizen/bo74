# WORKLOG — Хераборина (PWA-трекер)

> Репо: github.com/masterboplus-netizen/worklog
> Хостинг: https://masterboplus-netizen.github.io/worklog/

## ЧТО ЭТО

PWA для отслеживания времени с AI. Отдельная программа, не часть бота.

## КАК РАБОТАЕТ

1. worklog.json (локально, не публикуется).
2. encrypt.py шифрует AES-256-GCM с PIN.
3. data.encrypted.json публикуется на GitHub Pages.
4. Браузер расшифровывает по PIN.

## ДАННЫЕ

- projects — проекты с планами (11 фаз у Бо).
- sessions — сессии (дата, время, часы, сообщ, скрины).
- baseline — 336ч до 15.10.
- gap_rule_minutes — 15.

## ФУНКЦИИ

- Дашборд: метрики (сегодня, 7д, 30д, всего).
- Дневник: сессии по датам.
- Проекты: фазы с прогресс-барами, раскрытие.
- PWA: установка на телефон, офлайн.

## ОБНОВЛЕНИЕ ДАННЫХ

1. Обновить worklog.json.
2. WORKLOG_PIN='201186' .venv/bin/python encrypt.py
3. git add worklog.json data.encrypted.json
4. git commit -m "data: ..."
5. git push origin main

## ВАЖНО

- PIN: 201186 (не в git!)
- .venv/ с cryptography
- Cache-bust: index.html ?v=N
