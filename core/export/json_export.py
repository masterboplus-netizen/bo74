"""core.export.json — экспорт модели комнаты в JSON."""
import json
from core.model_3d import get_room_model


def export_json(room_id, session_id=None):
    """Возвращает JSON-строку модели комнаты."""
    model = get_room_model(room_id, session_id=session_id)
    if not model:
        return None
    return json.dumps(model, ensure_ascii=False, indent=2, default=str)


def save_json(room_id, session_id=None, path=None):
    """Сохраняет модель в файл. Возвращает путь."""
    content = export_json(room_id, session_id=session_id)
    if not content:
        return None
    if not path:
        path = f"/tmp/room_{room_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
