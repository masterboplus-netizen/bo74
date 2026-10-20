"""interfaces.api.main — FastAPI для сайта Бо."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from core.rooms_logic import walls, reports

app = FastAPI(title="Бо 8.1 — Web API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/summary")
async def api_summary():
    return {"status": "ok", "app": "Бо 8.1"}

@app.get("/api/rooms/{room_id}/walls")
async def api_room_walls(room_id: int):
    return walls.get_wall_state(room_id)

@app.get("/api/rooms/{room_id}/report")
async def api_room_report(room_id: int):
    return reports.get_room_report(room_id)

