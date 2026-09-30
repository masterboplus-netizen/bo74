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

    # Точки — ВСЕ НА ОДНОЙ ЛИНИИ (по горизонтали, на 30% от верха)
    line_y = y1 + (y2 - y1) // 3    # на 1/3 высоты от верха
    margin = 80                     # отступ от краёв
    points = {
        2: (x1 + margin, line_y),           # левая (у левого края)
        1: ((x1 + x2)//2, line_y),          # центр
        3: (x2 - margin, line_y),           # правая (у правого края)
    }
    labels = {
        1: ("Точка 1", "центр", "center"),
        2: ("Точка 2", "левый край", "center"),
        3: ("Точка 3", "правый край", "center"),
    }

    for num, (px, py) in points.items():
        color = "red" if num == step else "#999999"
        r = 22 if num == step else 16
        d.ellipse([(px-r, py-r), (px+r, py+r)], fill=color, outline="black", width=2)
        # Номер внутри
        d.text((px, py), str(num), fill="white", font=font, anchor="mm")
        # Подпись — с нужной стороны
        lab_title, lab_sub, side = labels[num]
        if side == "center":
            # Под точкой
            tx = px
            d.text((tx, py + r + 15), lab_title, fill="black", font=font_sm, anchor="mt")
            d.text((tx, py + r + 35), lab_sub, fill="gray", font=font_sm, anchor="mt")
        elif side == "right":
            tx = px + r + 10
            d.text((tx, py - 10), lab_title, fill="black", font=font_sm, anchor="lm")
            d.text((tx, py + 12), lab_sub, fill="gray", font=font_sm, anchor="lm")
        else:
            tx = px - r - 10
            d.text((tx, py - 10), lab_title, fill="black", font=font_sm, anchor="rm")
            d.text((tx, py + 12), lab_sub, fill="gray", font=font_sm, anchor="rm")

    # Стрелка: от двери вверх к точке 1 (центр)
    px1, py1 = points[1]
    start = (mid, y2 - 30)
    d.line([start, (px1, py1 + 40)], fill="#3366CC", width=4)
    # Наконечник
    d.polygon([(px1-10, py1+45), (px1+10, py1+45), (px1, py1+25)], fill="#3366CC")

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


def _draw_wall_step_scheme(step, phase, room_name="Комната"):
    """Рисует схему для конкретного шага обхода стены.
    
    step: 1/2/3/4 — номер стены
    phase: 'flags' / 'plane' / 'length' / 'angle'
    """
    W, H = 900, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    font_big = get_font(30)
    font = get_font(22)
    font_sm = get_font(18)
    
    # Заголовки по фазе
    phase_titles = {
        'flags':  f"Стена {step} — осмотр",
        'plane':  f"Стена {step} — плоскость",
        'length': f"Стена {step} — длина",
        'angle':  f"Стена {step} — угол",
    }
    d.text((W//2, 40), phase_titles.get(phase, f"Стена {step}"),
           fill="black", font=font_big, anchor="mm")
    d.text((W//2, 80), room_name, fill="gray", font=font_sm, anchor="mm")
    
    # Прямоугольник комнаты
    x1, y1 = 180, 160
    x2, y2 = 720, 700
    
    # Дверь внизу
    door_w = 140
    door_x1 = (W - door_w) // 2
    door_x2 = door_x1 + door_w
    
    # Цвета: активная = красная, соседняя (для угла) = синяя, остальные = серые
    RED = "#DD0000"
    BLUE = "#0066CC"
    GRAY = "#BBBBBB"
    
    # Определяем соседа (для угла) — следующая стена по часовой
    next_step = step + 1 if step < 4 else 1
    
    def wall_color(s):
        if s == step:
            return RED
        if phase == 'angle' and s == next_step:
            return BLUE
        return GRAY
    
    # Стена 1 (верхняя)
    c1 = wall_color(1)
    d.line([(x1, y1), (x2, y1)], fill=c1, width=8 if c1 == RED else 5)
    
    # Стена 2 (левая)
    c2 = wall_color(2)
    d.line([(x1, y1), (x1, y2)], fill=c2, width=8 if c2 == RED else 5)
    
    # Стена 3 (нижняя, с дверью)
    c3 = wall_color(3)
    d.line([(x1, y2), (door_x1, y2)], fill=c3, width=8 if c3 == RED else 5)
    d.line([(door_x2, y2), (x2, y2)], fill=c3, width=8 if c3 == RED else 5)
    
    # Стена 4 (правая)
    c4 = wall_color(4)
    d.line([(x2, y1), (x2, y2)], fill=c4, width=8 if c4 == RED else 5)
    
    # Подписи стен
    d.text(((x1+x2)//2, y1 - 25), "1", fill=c1, font=font_sm, anchor="mm")
    d.text((x1 - 25, (y1+y2)//2), "2", fill=c2, font=font_sm, anchor="mm")
    d.text(((x1+x2)//2, y2 + 90), "3", fill=c3, font=font_sm, anchor="mm")
    d.text((x2 + 25, (y1+y2)//2), "4", fill=c4, font=font_sm, anchor="mm")
    
    # Дверь
    d.text(((door_x1 + door_x2)//2, y2 + 35), "ДВЕРЬ", fill="black", font=font, anchor="mm")
    mid = (door_x1 + door_x2)//2
    d.polygon([(mid-15, y2+70), (mid+15, y2+70), (mid, y2+50)], fill="black")
    
    # === ДОПОЛНИТЕЛЬНЫЕ ЭЛЕМЕНТЫ ПО ФАЗЕ ===
    
    if phase == 'flags':
        # Текст «осмотри» + глаз
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        d.text((cx, cy - 20), "👁 ОСМОТРИ", fill=RED, font=font, anchor="mm")
        d.text((cx, cy + 15), "ЭТУ СТЕНУ", fill=RED, font=font, anchor="mm")
    
    elif phase == 'plane':
        # Стрелка вдоль стены (в зависимости от step)
        if step == 1:  # верхняя — стрелка слева-вправо
            ay = y1 + 25
            d.line([(x1 + 30, ay), (x2 - 30, ay)], fill=RED, width=4)
            d.polygon([(x2 - 30, ay - 10), (x2 - 30, ay + 10), (x2 - 15, ay)], fill=RED)
            d.text(((x1+x2)//2, ay - 25), "проверь ровность", fill=RED, font=font_sm, anchor="mm")
        elif step == 2:  # левая — сверху-вниз
            ax = x1 + 25
            d.line([(ax, y1 + 30), (ax, y2 - 30)], fill=RED, width=4)
            d.polygon([(ax - 10, y2 - 30), (ax + 10, y2 - 30), (ax, y2 - 15)], fill=RED)
            d.text((ax + 30, (y1+y2)//2), "проверь ровность", fill=RED, font=font_sm, anchor="lm")
        elif step == 3:  # нижняя — справа-налево
            ay = y2 - 25
            d.line([(x2 - 30, ay), (x1 + 30, ay)], fill=RED, width=4)
            d.polygon([(x1 + 30, ay - 10), (x1 + 30, ay + 10), (x1 + 15, ay)], fill=RED)
            d.text(((x1+x2)//2, ay + 25), "проверь ровность", fill=RED, font=font_sm, anchor="mm")
        elif step == 4:  # правая — снизу-вверх
            ax = x2 - 25
            d.line([(ax, y2 - 30), (ax, y1 + 30)], fill=RED, width=4)
            d.polygon([(ax - 10, y1 + 30), (ax + 10, y1 + 30), (ax, y1 + 15)], fill=RED)
            d.text((ax - 30, (y1+y2)//2), "проверь ровность", fill=RED, font=font_sm, anchor="rm")
    
    elif phase == 'length':
        # Размерная линия вдоль стены
        if step == 1:
            ay = y1 + 40
            d.line([(x1, ay), (x2, ay)], fill=RED, width=3)
            d.line([(x1, ay - 10), (x1, ay + 10)], fill=RED, width=3)
            d.line([(x2, ay - 10), (x2, ay + 10)], fill=RED, width=3)
            d.text(((x1+x2)//2, ay - 25), "← длина →", fill=RED, font=font, anchor="mm")
        elif step == 2:
            ax = x1 + 40
            d.line([(ax, y1), (ax, y2)], fill=RED, width=3)
            d.line([(ax - 10, y1), (ax + 10, y1)], fill=RED, width=3)
            d.line([(ax - 10, y2), (ax + 10, y2)], fill=RED, width=3)
            d.text((ax + 50, (y1+y2)//2), "← длина →", fill=RED, font=font, anchor="lm")
        elif step == 3:
            ay = y2 - 40
            d.line([(x2, ay), (x1, ay)], fill=RED, width=3)
            d.line([(x1, ay - 10), (x1, ay + 10)], fill=RED, width=3)
            d.line([(x2, ay - 10), (x2, ay + 10)], fill=RED, width=3)
            d.text(((x1+x2)//2, ay + 30), "← длина →", fill=RED, font=font, anchor="mm")
        elif step == 4:
            ax = x2 - 40
            d.line([(ax, y2), (ax, y1)], fill=RED, width=3)
            d.line([(ax - 10, y1), (ax + 10, y1)], fill=RED, width=3)
            d.line([(ax - 10, y2), (ax + 10, y2)], fill=RED, width=3)
            d.text((ax - 50, (y1+y2)//2), "← длина →", fill=RED, font=font, anchor="rm")
    
    elif phase == 'angle':
        # Угол между текущей стеной и следующей
        # Находим координаты угла
        corners = {
            1: (x1, y1),  # верх-левый — угол 1 и 2
            2: (x1, y2),  # низ-левый — угол 2 и 3
            3: (x2, y2),  # низ-правый — угол 3 и 4
            4: (x2, y1),  # верх-правый — угол 4 и 1
        }
        # Для стены step — угол в её начале (по часовой)
        # Стена 1 начинается в левом-верхнем
        # Стена 2 начинается в правом-верхнем (если по часовой от двери)
        # НО для схемы — просто подсветим угол, смежный с активной стеной
        corner_map = {
            1: (x1, y1),  # стена 1 — левый-верхний угол
            2: (x2, y1),  # стена 2 — правый-верхний угол
            3: (x2, y2),  # стена 3 — правый-нижний угол
            4: (x1, y2),  # стена 4 — левый-нижний угол
        }
        cx, cy = corner_map[step]
        r = 30
        # Дуга (часть круга) — рисуем через ellipse
        d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=RED, width=5)
        # Точка в углу
        d.ellipse([(cx - 6, cy - 6), (cx + 6, cy + 6)], fill=RED)
        # Подпись
        d.text((cx, cy - 55), "ЭТОТ УГОЛ", fill=RED, font=font, anchor="mm")
    
    # Сохраняем
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "images")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"wall_scheme_s{step}_{phase}.png")
    img.save(out_path)
    return out_path


def draw_all_wall_step_schemes():
    """Генерирует все 16 PNG (4 стены × 4 фазы)."""
    paths = []
    for step in [1, 2, 3, 4]:
        for phase in ['flags', 'plane', 'length', 'angle']:
            p = _draw_wall_step_scheme(step, phase)
            paths.append(p)
            print(f"✅ {p}")
    return paths
