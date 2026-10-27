"""interfaces.api.main — FastAPI для сайта Бо."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from core.rooms_logic import walls, reports
from core.rooms import get_rooms

app = FastAPI(title="Бо 8.1 — Web API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/api/summary")
async def api_summary():
    return {"status": "ok", "app": "Бо 8.1"}

@app.get("/api/rooms/{room_id}/walls")
async def api_room_walls(room_id: int):
    return walls.get_wall_state(room_id)

@app.get("/api/rooms/{room_id}/report")
async def api_room_report(room_id: int):
    return reports.get_room_report(room_id)


@app.get("/api/objects")
def get_objects():
    import sqlite3
    try:
        conn = sqlite3.connect('bo72.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Берем ВСЕ колонки, которые есть в таблице
        cursor.execute("SELECT * FROM objects ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            d = dict(row)
            # Если каких-то полей нет, подставляем дефолтные значения для сайта
            if 'balance' not in d: d['balance'] = 0
            if 'status' not in d: d['status'] = 'active'
            if 'name' not in d: d['name'] = 'Без названия'
            result.append(d)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/objects/{object_id}/rooms")
def api_get_rooms(object_id: int):
    try:
        rooms = get_rooms(object_id)
        return {"status": "ok", "rooms": rooms}
    except Exception as e:
        return {"status": "error", "message": str(e)}
