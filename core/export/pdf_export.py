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


def _pdf_header(story, title, subtitle=None):
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, textColor=colors.grey, spaceAfter=12)
    story.append(Paragraph(title, h1))
    if subtitle:
        story.append(Paragraph(subtitle, h2))
    story.append(Paragraph("Дата: " + datetime.now().strftime("%d.%m.%Y %H:%M"), styles["Normal"]))
    story.append(Spacer(1, 6*mm))


def _pdf_table(story, rows, col_widths=None):
    if not rows:
        return
    styles = getSampleStyleSheet()
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EEEEEE")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
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
    story.append(Paragraph("Компонентов: " + str(stats.get("components_total", 0)), styles["Normal"]))
    story.append(Paragraph("Модулей занято: " + str(stats.get("modules_used", 0)), styles["Normal"]))
    story.append(Paragraph("Групп: " + str(stats.get("groups_count", 0)), styles["Normal"]))
    story.append(Paragraph("Нагрузка: " + str(stats.get("total_load_watt", 0)) + " Вт", styles["Normal"]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("ИТОГО стоимость щита: " + str(round(total, 2)) + " руб.", styles["Heading3"]))

    doc.build(story)
    return path
