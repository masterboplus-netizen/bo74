"""core.visualize — рендер комнаты в PNG (изометрия + план)."""
from PIL import Image, ImageDraw, ImageFont
from core.rooms import get_room
from core.measures import get_walls_ordered
from core.geometry import calc_wall_coords
from core.openings import get_openings
from core.niches import get_niches_by_room
from core.comms import get_comms
import os


def _get_font(size=14):
    """Пытается загрузить шрифт, если нет — использует дефолтный."""
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_room_plan(room_id, session_id=None, width=900, height=700):
    """Рисует план комнаты (вид сверху). Возвращает путь к PNG."""
    room = get_room(room_id)
    if not room:
        return None

    walls = get_walls_ordered(room_id)
    if not walls:
        return None

    coords = calc_wall_coords(walls)
    if not coords:
        return None

    # Границы комнаты
    all_x = [c['start_x'] for c in coords] + [c['end_x'] for c in coords]
    all_y = [c['start_y'] for c in coords] + [c['end_y'] for c in coords]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    span_x = max_x - min_x or 1
    span_y = max_y - min_y or 1

    # Поля
    pad = 80
    draw_w = width - 2 * pad
    draw_h = height - 2 * pad
    scale = min(draw_w / span_x, draw_h / span_y)

    def to_px(x, y):
        px = pad + (x - min_x) * scale
        py = height - pad - (y - min_y) * scale
        return (px, py)

    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = _get_font(16)
    font_small = _get_font(13)
    font_title = _get_font(20)

    # Заголовок
    title = f"Комната: {room.get('name', '?')}"
    draw.text((20, 20), title, fill="#111", font=font_title)
    subtitle = f"Высота: {room.get('height', '—')} см"
    draw.text((20, 50), subtitle, fill="#666", font=font_small)

    # Пол (заливка контура)
    poly_points = [to_px(c['start_x'], c['start_y']) for c in coords]
    if poly_points:
        draw.polygon(poly_points, fill="#f5f5f5")

    # Стены (линии)
    for c in coords:
        x1, y1 = to_px(c['start_x'], c['start_y'])
        x2, y2 = to_px(c['end_x'], c['end_y'])
        draw.line([x1, y1, x2, y2], fill="#000", width=4)

        # Подпись длины
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        label = f"{int(c.get('length') or 0)} см"
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        # Фон под текстом
        draw.rectangle([mx - tw/2 - 4, my - th/2 - 3, mx + tw/2 + 4, my + th/2 + 3], fill="#fffbcc")
        draw.text((mx - tw/2, my - th/2), label, fill="#333", font=font)

    # Углы (кружки)
    for c in coords:
        for (x, y) in [(c['start_x'], c['start_y']), (c['end_x'], c['end_y'])]:
            px, py = to_px(x, y)
            draw.ellipse([px-4, py-4, px+4, py+4], fill="#1e88e5")

    # Проёмы (разрывы на стенах — оранжевые линии)
    wall_by_pos = {w.get('wall_pos'): w for w in walls}
    try:
        openings = get_openings(room_id, session_id=session_id)
        for o in openings:
            w = wall_by_pos.get(o.get('wall_pos'))
            if not w:
                continue
            # Ищем стену в coords
            wc = next((c for c in coords if c.get('wall_pos') == o.get('wall_pos')), None)
            if not wc:
                continue
            length = wc['length'] or 1
            offset = o.get('offset_x') or 0
            ow = o.get('width') or 100
            # Начало проёма
            frac1 = max(0.0, min(1.0, offset / length))
            frac2 = max(0.0, min(1.0, (offset + ow) / length))
            x1 = wc['start_x'] + (wc['end_x'] - wc['start_x']) * frac1
            y1 = wc['start_y'] + (wc['end_y'] - wc['start_y']) * frac1
            x2 = wc['start_x'] + (wc['end_x'] - wc['start_x']) * frac2
            y2 = wc['start_y'] + (wc['end_y'] - wc['start_y']) * frac2
            px1, py1 = to_px(x1, y1)
            px2, py2 = to_px(x2, y2)
            draw.line([px1, py1, px2, py2], fill="#ff6f00", width=6)
    except Exception as e:
        print(f"⚠️ openings render: {e}", flush=True)

    # Коммуникации (точки)
    try:
        comms = get_comms(room_id)
        for c in comms:
            wc = next((c2 for c2 in coords if c2.get('wall_pos') == c.get('wall')), None)
            if not wc:
                continue
            length = wc['length'] or 1
            offset = c.get('offset_x') or 0
            frac = max(0.0, min(1.0, offset / length))
            x = wc['start_x'] + (wc['end_x'] - wc['start_x']) * frac
            y = wc['start_y'] + (wc['end_y'] - wc['start_y']) * frac
            px, py = to_px(x, y)
            draw.ellipse([px-6, py-6, px+6, py+6], fill="#d32f2f", outline="#000", width=2)
    except Exception as e:
        print(f"⚠️ comms render: {e}", flush=True)

    # Легенда
    legend_y = height - 40
    draw.rectangle([20, legend_y-2, 44, legend_y+12], fill="#000")
    draw.text((50, legend_y-4), "Стены", fill="#333", font=font_small)
    draw.rectangle([140, legend_y-2, 164, legend_y+12], fill="#ff6f00")
    draw.text((170, legend_y-4), "Проёмы", fill="#333", font=font_small)
    draw.ellipse([260, legend_y-1, 272, legend_y+11], fill="#d32f2f")
    draw.text((278, legend_y-4), "Коммуникации", fill="#333", font=font_small)
    draw.ellipse([430, legend_y-1, 442, legend_y+11], fill="#1e88e5")
    draw.text((448, legend_y-4), "Углы", fill="#333", font=font_small)

    # Сохраняем
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"room_{room_id}_plan.png")
    img.save(path)
    return path


def save_room_plan(room_id, session_id=None, path=None):
    """Обёртка для совместимости."""
    result = render_room_plan(room_id, session_id=session_id)
    if result and path and result != path:
        import shutil
        shutil.copy(result, path)
        return path
    return result
