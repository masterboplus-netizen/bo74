# PROMPTS/review.md

> Как делать ревью кода перед push.

---

## ШАБЛОН

Перед коммитом:

1. Проверить синтаксис:
   python -c "import ast; ast.parse(open('file').read())"

2. Проверить импорты:
   python -c "import handlers.commands; print('OK')"

3. Проверить на дубли:
   grep -c "def handle_rooms_callback" file.py

4. Перезапустить бота:
   pkill -9 -f "bot.py"; sleep 2; ./start_all.sh

5. Проверить логи:
   tail -10 bot_start.log

6. Тест в Telegram.

7. Коммит:
   git add -A && git commit -m "..." && git push

---

## ЧЕК-ЛИСТ

- [ ] Синтаксис OK.
- [ ] Импорты OK.
- [ ] Нет дублей функций.
- [ ] Бот перезапущен.
- [ ] Логи чистые.
- [ ] В Telegram проверил.
- [ ] Коммит с понятным сообщением.
- [ ] Docs обновлены (если нужно).

---

## АНТИПАТТЕРНЫ

- ❌ Коммит без проверки.
- ❌ Push без pull.
- ❌ Force push.
- ❌ Магические строки.
- ❌ Дубли.
- ❌ print без flush=True.
- ❌ Хардкод путей.

---

*Конец review.md*
