"""Рисует схему комнаты для замеров (Pillow)."""
from PIL import Image, ImageDraw, ImageFont
import os

def get_font(size=20):
    """Ищет доступный шрифт."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/nix/store/*/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    import glob
    for c in candidates:
        if '*' in c:
            for f in glob.glob(c):
                return ImageFont.truetype(f, size)
        elif os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def draw_height_scheme(step=1, room_name="Комната"):
    """Рисует схему с 3 точками. step=1/2/3 — какая активна.
    Возвращает путь к PNG.
    """
    W, H = 800, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    font_big = get_font(28)
    font = get_font(20)
    font_sm = get_font(16)

    # Заголовок
    title = f"Высота потолка — точка {step} из 3"
    d.text((W//2, 30), title, fill="black", font=font_big, anchor="mm")

    # Комната — прямоугольник (отступы 100 по бокам, 120/150 сверху/снизу)
    x1, y1 = 150, 100
    x2, y2 = 650, 650
    # Стены (3 стороны)
    d.line([(x1, y1), (x1, y2)], fill="black", width=4)  # левая
    d.line([(x1, y1), (x2, y1)], fill="black", width=4)  # верхняя
    d.line([(x2, y1), (x2, y2)], fill="black", width=4)  # правая
    # Дверь — открытый проём внизу
    door_w = 100
    door_x1 = (W - door_w) // 2
    door_x2 = door_x1 + door_w
    d.line([(x1, y2), (door_x1, y2)], fill="black", width=4)  # левая часть низа
    d.line([(door_x2, y2), (x2, y2)], fill="black", width=4)  # правая часть низа
    # Подпись двери
    d.text(((door_x1 + door_x2)//2, y2 + 30), "🚪 Дверь", fill="black", font=font, anchor="mm")

    # Точки
    points = {
        1: (x1 + 80, y1 + 80),       # левый верхний угол (у левой стены)
        2: (x2 - 80, y1 + 80),       # правый верхний угол (у правой стены)
        3: ((x1 + x2)//2, (y1 + y2)//2),  # центр
    }
    labels = {1: "Точка 1\n(левая стена)", 2: "Точка 2\n(правая стена)", 3: "Точка 3\n(центр)"}

    for num, (px, py) in points.items():
        color = "red" if num == step else "gray"
        r = 18 if num == step else 12
        d.ellipse([(px-r, py-r), (px+r, py+r)], fill=color, outline="black", width=2)
        # Номер внутри
        d.text((px, py), str(num), fill="white", font=font, anchor="mm")

    # Подписи под точками
    d.text((points[1][0], y1 + 130), labels[1], fill="black", font=font_sm, anchor="mm")
    d.text((points[2][0], y1 + 130), labels[2], fill="black", font=font_sm, anchor="mm")
    d.text((points[3][0], points[3][1] + 50), labels[3], fill="black", font=font_sm, anchor="mm")

    # Стрелка обхода от двери: от двери → точка 1 → точка 3 → точка 2
    arrow_y = y2 - 30
    d.line([(door_x1 - 30, arrow_y), (points[1][0], arrow_y)], fill="blue", width=2)
    d.line([(points[1][0], arrow_y), (points[1][0], points[1][1] + 30)], fill="blue", width=2)

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
