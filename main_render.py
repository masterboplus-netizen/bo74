import os
import threading
from flask import Flask

# Импортируем твоего существующего бота
from bot import main as run_telegram_bot

# Создаём Flask-приложение для healthcheck
app = Flask(__name__)

@app.route('/health')
def health():
    return {"status": "ok", "service": "bo75-bot"}, 200

@app.route('/')
def index():
    return "Bot is running", 200

if __name__ == "__main__":
    # Запускаем Telegram-бота в отдельном потоке
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()

    # Запускаем Flask-сервер на порту, который даёт Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
