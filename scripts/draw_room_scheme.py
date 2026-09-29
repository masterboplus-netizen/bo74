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
