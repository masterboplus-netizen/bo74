"""core.export.pdf_export — экспорт в PDF через reportlab.

Функции:
- export_panel_spec_pdf(panel_id) — спецификация щита
- export_object_elec_pdf(object_id) — смета ЭОМ объекта
- export_plumbing_estimate_pdf(object_id) — смета сантехники
"""
import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "fonts", "DejaVuSans.ttf")
FONT_NAME = "Helvetica"
try:
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))
        FONT_NAME = "DejaVu"
except Exception as _e:
    print("pdf font register: " + str(_e), flush=True)


def _pdf_header(story, title, subtitle=None):
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName=FONT_NAME, fontSize=16, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName=FONT_NAME, fontSize=11, textColor=colors.grey, spaceAfter=12)
    normal = ParagraphStyle("N", parent=ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME), fontName=FONT_NAME)
    story.append(Paragraph(title, h1))
    if subtitle:
        story.append(Paragraph(subtitle, h2))
    story.append(Paragraph("Дата: " + datetime.now().strftime("%d.%m.%Y %H:%M"), normal))
    story.append(Spacer(1, 6*mm))


def _pdf_table(story, rows, col_widths=None):
    if not rows:
        return
    styles = getSampleStyleSheet()
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EEEEEE")),
        ("FONTNAME", (0,0), (-1,-1), FONT_NAME),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t)


def export_panel_spec_pdf(panel_id):
    """PDF-спецификация щита. Возвращает путь к файлу."""
    from core import elec_panels as ep
    from modules.objects import get_object
    p = ep.get_panel(panel_id)
    if not p:
        return None
    obj = get_object(p.get("object_id")) if p.get("object_id") else None
    obj_name = obj["name"] if obj else "-"
    comps = ep.get_components(panel_id)
    stats = ep.get_panel_stats(panel_id)
    total = ep.calc_panel_cost(panel_id)

    path = os.path.join(tempfile.gettempdir(), "panel_" + str(panel_id) + "_spec.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, title="Спецификация щита")
    story = []
    _pdf_header(story,
        "Спецификация щита: " + str(p.get("name") or "?"),
        "Объект: " + str(obj_name))

    rows = [["№", "Тип", "Модель", "Номинал", "Кол-во", "Цена, ₽", "Сумма, ₽"]]
    total_sum = 0.0
    for i, c in enumerate(comps, 1):
        ctype = c.get("component_type") or "?"
        model = c.get("component_model") or "-"
        rating = (str(c.get("rating") or "") + "А") if c.get("rating") else "-"
        qty = c.get("quantity") or 1
        try:
            price = ep.calc_component_price(c)
        except Exception:
            price = 0
        total_sum += price
        rows.append([str(i), ctype, model, rating, str(qty), str(round(price, 2)), str(round(price, 2))])
    rows.append(["", "", "", "", "", "ИТОГО:", str(round(total_sum, 2))])
    _pdf_table(story, rows, col_widths=[10*mm, 30*mm, 40*mm, 20*mm, 15*mm, 25*mm, 30*mm])

    story.append(Spacer(1, 6*mm))
    styles = getSampleStyleSheet()
    story.append(Paragraph("Компонентов: " + str(stats.get("components_total", 0)), ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))
    story.append(Paragraph("Модулей занято: " + str(stats.get("modules_used", 0)), ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))
    story.append(Paragraph("Групп: " + str(stats.get("groups_count", 0)), ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))
    story.append(Paragraph("Нагрузка: " + str(stats.get("total_load_watt", 0)) + " Вт", ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("ИТОГО стоимость щита: " + str(round(total, 2)) + " руб.", ParagraphStyle("H3", parent=styles["Heading3"], fontName=FONT_NAME)))

    doc.build(story)
    return path



def export_object_elec_pdf(object_id):
    """PDF-смета ЭОМ объекта (щиты + монтаж + работы)."""
    from core import elec_prices as ep
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj["name"] if obj else ("Объект " + str(object_id))
    data = ep.calc_object_elec_total(object_id)
    path = os.path.join(tempfile.gettempdir(), "obj_" + str(object_id) + "_elec.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, title="Смета ЭОМ")
    story = []
    _pdf_header(story, "Смета ЭОМ: " + str(obj_name), "Электрооборудование и монтаж")

    rows = [["Раздел", "Сумма, руб."]]
    rows.append(["Щиты (компоненты)", str(round(data.get("panels_cost", 0), 2))])
    rows.append(["Кабель", str(round(data.get("montage_cable_cost", 0), 2))])
    rows.append(["Расходники", str(round(data.get("montage_consumable_cost", 0), 2))])
    rows.append(["Работы", str(round(data.get("works_total", 0), 2))])
    rows.append(["ИТОГО:", str(round(data.get("total", 0), 2))])
    _pdf_table(story, rows, col_widths=[100*mm, 60*mm])

    story.append(Spacer(1, 6*mm))
    styles = getSampleStyleSheet()
    story.append(Paragraph("Щитов: " + str(data.get("panels_count", 0)), ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))
    story.append(Paragraph("Метраж: " + str(data.get("montage_meters", 0)) + " м", ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))
    story.append(Paragraph("Работ: " + str(data.get("works_count", 0)), ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))

    doc.build(story)
    return path


def export_plumbing_estimate_pdf(object_id):
    """PDF-смета сантехники объекта (трубы + расходники + работы)."""
    from core import plumbing_panels as pp
    from modules.objects import get_object
    obj = get_object(object_id)
    obj_name = obj["name"] if obj else ("Объект " + str(object_id))
    data = pp.calc_object_cost(object_id)
    path = os.path.join(tempfile.gettempdir(), "obj_" + str(object_id) + "_plumb.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4, title="Смета сантехники")
    story = []
    _pdf_header(story, "Смета сантехники: " + str(obj_name), "Трубы, расходники, работы")

    rows = [["Раздел", "Сумма, руб."]]
    rows.append(["Трубы", str(round(data.get("total_pipe_cost", 0), 2))])
    rows.append(["Расходники", str(round(data.get("total_consumable_cost", 0), 2))])
    rows.append(["Работы", str(round(data.get("works_total", 0), 2))])
    rows.append(["ИТОГО:", str(round(data.get("total", 0), 2))])
    _pdf_table(story, rows, col_widths=[100*mm, 60*mm])

    story.append(Spacer(1, 6*mm))
    styles = getSampleStyleSheet()
    story.append(Paragraph("Коллекторов: " + str(data.get("panels_count", 0)), ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))
    story.append(Paragraph("Трасс: " + str(data.get("routes_count", 0)), ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))
    story.append(Paragraph("Метраж: " + str(data.get("total_m", 0)) + " м", ParagraphStyle("N", parent=styles["Normal"], fontName=FONT_NAME)))

    doc.build(story)
    return path
