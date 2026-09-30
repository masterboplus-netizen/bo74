"""Рисует схему комнаты для замеров (Pillow)."""
from PIL import Image, ImageDraw, ImageFont
import os
import glob


def get_font(size=20):
    """Ищет доступный шрифт (без эмодзи)."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    for c in glob.glob("/nix/store/*/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        return ImageFont.truetype(c, size)
    for c in glob.glob("/nix/store/*/share/fonts/**/DejaVuSans.ttf", recursive=True):
        return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def draw_height_scheme(step=1, room_name="Комната"):
    """Рисует схему с 3 точками. step=1/2/3 — какая активна.
    Возвращает путь к PNG.
    """
    W, H = 900, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    font_big = get_font(30)
    font = get_font(22)
    font_sm = get_font(18)

    # Заголовок
    title = f"Высота потолка — точка {step} из 3"
    d.text((W//2, 40), title, fill="black", font=font_big, anchor="mm")

    # Имя комнаты (мелко под заголовком)
    d.text((W//2, 80), room_name, fill="gray", font=font_sm, anchor="mm")

    # Комната — прямоугольник
    x1, y1 = 180, 130
    x2, y2 = 720, 680
    # Стены (3 стороны)
    d.line([(x1, y1), (x1, y2)], fill="black", width=5)  # левая
    d.line([(x1, y1), (x2, y1)], fill="black", width=5)  # верхняя
    d.line([(x2, y1), (x2, y2)], fill="black", width=5)  # правая
    # Дверь — открытый проём внизу
    door_w = 140
    door_x1 = (W - door_w) // 2
    door_x2 = door_x1 + door_w
    d.line([(x1, y2), (door_x1, y2)], fill="black", width=5)
    d.line([(door_x2, y2), (x2, y2)], fill="black", width=5)
    # Подпись двери — текстом, крупно
    d.text(((door_x1 + door_x2)//2, y2 + 35), "ДВЕРЬ", fill="black", font=font, anchor="mm")
    # Стрелка входа (треугольник)
    mid = (door_x1 + door_x2)//2
    d.polygon([(mid-15, y2+65), (mid+15, y2+65), (mid, y2+45)], fill="black")

    # Точки — координаты (1 = центр, 2 = левый угол, 3 = правый угол)
    points = {
        1: ((x1 + x2)//2, (y1 + y2)//2),   # центр (ПЕРВАЯ)
        2: (x1 + 100, y1 + 120),           # левый угол
        3: (x2 - 100, y1 + 120),           # правый угол
    }
    labels = {
        1: ("Точка 1", "центр", "right"),
        2: ("Точка 2", "левый угол", "right"),
        3: ("Точка 3", "правый угол", "left"),
    }

    for num, (px, py) in points.items():
        color = "red" if num == step else "#999999"
        r = 22 if num == step else 16
        d.ellipse([(px-r, py-r), (px+r, py+r)], fill=color, outline="black", width=2)
        # Номер внутри
        d.text((px, py), str(num), fill="white", font=font, anchor="mm")
        # Подпись — с нужной стороны
        lab_title, lab_sub, side = labels[num]
        if side == "right":
            # Справа от точки
            tx = px + r + 10
            ax = "lm"
        else:
            # Слева от точки
            tx = px - r - 10
            ax = "rm"
        d.text((tx, py - 10), lab_title, fill="black", font=font_sm, anchor=ax)
        d.text((tx, py + 12), lab_sub, fill="gray", font=font_sm, anchor=ax)

    # Стрелка обхода: от двери к центру (точка 1) — прямая
    px1, py1 = points[1]
    start = (mid, y2 - 10)
    # Линия от двери к центру
    d.line([start, (px1, py1 + 30)], fill="#3366CC", width=4)
    # Наконечник (стрелка вверх к точке)
    d.polygon([(px1-10, py1+40), (px1+10, py1+40), (px1, py1+18)], fill="#3366CC")

    # Сохраняем
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "images")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"height_scheme_step{step}.png")
    img.save(out_path)
    return out_path


if __name__ == "__main__":
    for s in [1, 2, 3]:
        path = draw_height_scheme(step=s)
        print(f"✅ {path}")


def draw_wall_scheme(step=1, room_name="Комната"):
    """Рисует схему с 4 стенами. step=1/2/3/4 — какая активна (красная).
    Остальные — серый пунктир. Возвращает путь к PNG.
    
    Порядок стен по часовой от двери:
        1 — напротив (верхняя)
        2 — слева
        3 — у входа (нижняя, с дверью)
        4 — справа
    """
    W, H = 900, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    font_big = get_font(30)
    font = get_font(22)
    font_sm = get_font(18)

    wall_names = {
        1: "Стена 1 — напротив",
        2: "Стена 2 — слева",
        3: "Стена 3 — у входа",
        4: "Стена 4 — справа",
    }
    
    # Заголовок
    title = f"Обход стен — {wall_names.get(step, '?')}"
    d.text((W//2, 40), title, fill="black", font=font_big, anchor="mm")
    d.text((W//2, 80), room_name, fill="gray", font=font_sm, anchor="mm")
    d.text((W//2, 110), f"Шаг {step} из 4", fill="gray", font=font_sm, anchor="mm")

    # Комната — прямоугольник (как у высоты)
    x1, y1 = 180, 160
    x2, y2 = 720, 700
    
    # Дверь внизу (проём)
    door_w = 140
    door_x1 = (W - door_w) // 2
    door_x2 = door_x1 + door_w
    
    # Рисуем 4 стены
    # Стена 1 (верхняя) — напротив
    color1 = "red" if step == 1 else "#BBBBBB"
    width1 = 6 if step == 1 else 4
    if step == 1:
        d.line([(x1, y1), (x2, y1)], fill=color1, width=width1)
    else:
        # Серый пунктир
        _draw_dashed_line(d, (x1, y1), (x2, y1), fill=color1, width=width1, dash=15)
    
    # Стена 2 (левая)
    color2 = "red" if step == 2 else "#BBBBBB"
    width2 = 6 if step == 2 else 4
    if step == 2:
        d.line([(x1, y1), (x1, y2)], fill=color2, width=width2)
    else:
        _draw_dashed_line(d, (x1, y1), (x1, y2), fill=color2, width=width2, dash=15)
    
    # Стена 3 (нижняя) — с дверью
    color3 = "red" if step == 3 else "#BBBBBB"
    width3 = 6 if step == 3 else 4
    if step == 3:
        d.line([(x1, y2), (door_x1, y2)], fill=color3, width=width3)
        d.line([(door_x2, y2), (x2, y2)], fill=color3, width=width3)
    else:
        _draw_dashed_line(d, (x1, y2), (door_x1, y2), fill=color3, width=width3, dash=15)
        _draw_dashed_line(d, (door_x2, y2), (x2, y2), fill=color3, width=width3, dash=15)
    
    # Стена 4 (правая)
    color4 = "red" if step == 4 else "#BBBBBB"
    width4 = 6 if step == 4 else 4
    if step == 4:
        d.line([(x2, y1), (x2, y2)], fill=color4, width=width4)
    else:
        _draw_dashed_line(d, (x2, y1), (x2, y2), fill=color4, width=width4, dash=15)
    
    # Подпись двери
    d.text(((door_x1 + door_x2)//2, y2 + 35), "ДВЕРЬ", fill="black", font=font, anchor="mm")
    mid = (door_x1 + door_x2)//2
    d.polygon([(mid-15, y2+65), (mid+15, y2+65), (mid, y2+45)], fill="black")
    
    # Номера стен (подписи у каждой стены)
    d.text(((x1+x2)//2, y1 - 30), f"1 (напротив)", fill=color1, font=font_sm, anchor="mm")
    d.text((x1 - 30, (y1+y2)//2), f"2 (слева)", fill=color2, font=font_sm, anchor="mm")
    d.text(((x1+x2)//2, y2 + 100), f"3 (у входа)", fill=color3, font=font_sm, anchor="mm")
    d.text((x2 + 30, (y1+y2)//2), f"4 (справа)", fill=color4, font=font_sm, anchor="mm")
    
    # Сохраняем
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "images")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"wall_scheme_step{step}.png")
    img.save(out_path)
    return out_path


def _draw_dashed_line(draw, p1, p2, fill="black", width=2, dash=15):
    """Рисует пунктирную линию между двумя точками."""
    import math
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    pos = 0.0
    while pos < length:
        seg_end = min(pos + dash, length)
        sx = x1 + ux * pos
        sy = y1 + uy * pos
        ex = x1 + ux * seg_end
        ey = y1 + uy * seg_end
        draw.line([(sx, sy), (ex, ey)], fill=fill, width=width)
        pos += dash * 2  # пропуск
