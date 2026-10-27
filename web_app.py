import threading
import uvicorn
import time
from interfaces.api.main import app

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    print("🚀 Запуск FastAPI в фоне...")
    t = threading.Thread(target=run_fastapi, daemon=True)
    t.start()
    
    # Держим главный процесс живым, чтобы Replit не убил его
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Остановлено")
