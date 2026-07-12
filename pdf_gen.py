"""
Generates a PDF inspection report from an inspection row + its form_data,
driven by the same declarative config in forms_config.py used for the HTML
form. One generic renderer covers all 12 inspection types.

Visual style is modeled on SCFP's own invoice / packing-slip template:
a bold colored all-caps title, plain company letterhead text (no boxes),
a soft blush info band for customer/site/report details, and clean
rule-separated tables instead of heavy gridlines.
"""
import io
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_RIGHT

from forms_config import get_type_config, CLOSING_SECTION

COMPANY_NAME = "Southern Cross Fire Protection, LLC."
COMPANY_ADDRESS = "8131 Blaikie Court, Sarasota, FL 34240"
COMPANY_PHONE = "+1 (941) 400-6635"
COMPANY_WEB = "southerncrossfirellc.com"

# Brand palette — matches the web app's red theme (static/style.css --navy / --accent)
BRAND = colors.HexColor("#7a1a1a")
BRAND_LIGHT = colors.HexColor("#9c2a24")
BAND_BG = colors.HexColor("#f7ebe9")
LABEL_GRAY = colors.HexColor("#6b6b6b")
RULE_GRAY = colors.HexColor("#e3dcdb")

PAGE_WIDTH = 7.6 * inch


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="SCFPTitle", fontName="Helvetica-Bold", fontSize=17,
                           textColor=BRAND, spaceAfter=6, leading=20))
    ss.add(ParagraphStyle(name="SCFPCompany", fontName="Helvetica-Bold", fontSize=9.5,
                           textColor=colors.black, leading=13))
    ss.add(ParagraphStyle(name="SCFPSub", fontName="Helvetica", fontSize=8.5,
                           textColor=LABEL_GRAY, leading=12.5))
    ss.add(ParagraphStyle(name="SCFPMeta", fontName="Helvetica", fontSize=8.5,
                           textColor=LABEL_GRAY, leading=12.5, alignment=TA_RIGHT))
    ss.add(ParagraphStyle(name="SCFPBandLabel", fontName="Helvetica-Bold", fontSize=8.5,
                           textColor=colors.black, leading=12))
    ss.add(ParagraphStyle(name="SCFPBandValue", fontName="Helvetica", fontSize=8.5,
                           textColor=colors.HexColor("#333333"), leading=13))
    ss.add(ParagraphStyle(name="SCFPSection", fontName="Helvetica-Bold", fontSize=11,
                           textColor=BRAND, spaceBefore=4, spaceAfter=0))
    ss.add(ParagraphStyle(name="SCFPLabel", fontName="Helvetica-Bold", fontSize=7.7,
                           textColor=LABEL_GRAY))
    ss.add(ParagraphStyle(name="SCFPValue", fontName="Helvetica", fontSize=9.5,
                           textColor=colors.black))
    ss.add(ParagraphStyle(name="SCFPCell", fontName="Helvetica", fontSize=8,
                           textColor=colors.black, leading=10.5))
    ss.add(ParagraphStyle(name="SCFPCellHdr", fontName="Helvetica-Bold", fontSize=7.3,
                           textColor=BRAND, leading=9))
    return ss


def _fmt_value(field, value):
    if value is None or value == "":
        return "—"
    if field.get("type") in ("yn", "ynna", "select"):
        return str(value)
    return str(value)


def _section_header(text, styles):
    """A colored, all-caps section heading with a thin rule underneath —
    matches the muted-red section labels in the reference invoice style."""
    t = Table([[Paragraph(text.upper(), styles["SCFPSection"])]], colWidths=[PAGE_WIDTH])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 1, BRAND),
    ]))
    return t


def _kv_grid(section_fields, data, styles, cols=2):
    """Renders simple (non-table) fields as a label/value grid."""
    simple = [f for f in section_fields if f["type"] != "table"]
    if not simple:
        return None
    rows = []
    for i in range(0, len(simple), cols):
        row = []
        for f in simple[i:i + cols]:
            val = _fmt_value(f, data.get(f["key"]))
            cell = [Paragraph(f["label"], styles["SCFPLabel"]),
                    Paragraph(val, styles["SCFPValue"])]
            row.append(cell)
        while len(row) < cols:
            row.append("")
        rows.append(row)
    grid_rows = []
    for row in rows:
        grid_rows.append([
            (Table([[c[0]], [c[1]]], colWidths=[3.3 * inch]) if c else "")
            for c in row
        ])
    col_w = PAGE_WIDTH / cols
    t = Table(grid_rows, colWidths=[col_w] * cols)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE_GRAY),
    ]))
    return t


def _table_field(field, data, styles):
    columns = field["columns"]
    rows = data.get(field["key"]) or []
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except Exception:
            rows = []
    if not rows:
        return None
    header = [Paragraph(c["label"].upper(), styles["SCFPCellHdr"]) for c in columns]
    body = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if not any((r.get(c["key"]) not in (None, "")) for c in columns):
            continue
        body.append([Paragraph(_fmt_value(c, r.get(c["key"])), styles["SCFPCell"]) for c in columns])
    if not body:
        return None
    col_width = PAGE_WIDTH / len(columns)
    t = Table([header] + body, colWidths=[col_width] * len(columns), repeatRows=1)
    style = [
        ("LINEBELOW", (0, 0), (-1, 0), 1, BRAND),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(style))
    return Paragraph(field["label"], styles["SCFPLabel"]), t


def _band_cell(label, lines, styles):
    """One column of the blush info band: a bold label + stacked value lines."""
    value_html = "<br/>".join(l for l in lines if l) or "—"
    return [Paragraph(label, styles["SCFPBandLabel"]),
            Spacer(1, 2),
            Paragraph(value_html, styles["SCFPBandValue"])]


def generate_inspection_pdf(inspection_row, client_row, site_row, asset_row=None):
    """Returns PDF bytes for the given inspection."""
    styles = _styles()
    itype = inspection_row["inspection_type"]
    cfg = get_type_config(itype)
    data = json.loads(inspection_row["form_data"] or "{}")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                             topMargin=0.55 * inch, bottomMargin=0.5 * inch,
                             leftMargin=0.45 * inch, rightMargin=0.45 * inch)
    story = []

    # --- Letterhead: colored all-caps title, then plain company info ---
    title_text = (cfg["label"] if cfg else itype).upper()
    header_tbl = Table([
        [Paragraph(title_text, styles["SCFPTitle"]),
         Paragraph(f"Report #{inspection_row['id']}<br/>Date: {inspection_row['inspection_date']}",
                    styles["SCFPMeta"])],
    ], colWidths=[5.0 * inch, PAGE_WIDTH - 5.0 * inch])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_tbl)
    story.append(Paragraph(COMPANY_NAME, styles["SCFPCompany"]))
    story.append(Paragraph(COMPANY_ADDRESS, styles["SCFPSub"]))
    story.append(Paragraph(f"{COMPANY_PHONE} &nbsp;|&nbsp; {COMPANY_WEB}", styles["SCFPSub"]))
    story.append(Spacer(1, 12))

    # --- Blush info band: Customer / Site / Report Details ---
    customer_lines = [client_row["name"] if client_row else "—"]
    site_lines = [site_row["name"] if site_row else "—"]
    if site_row:
        site_lines.append(f"{site_row['street']}, {site_row['city']}, {site_row['state']} {site_row['zip']}")
    detail_lines = [f"Inspector: {inspection_row['inspector_name'] or '—'}"]
    if asset_row:
        detail_lines.append(f"Asset: {asset_row['label']}")
        if asset_row["serial_number"]:
            detail_lines.append(f"Serial #: {asset_row['serial_number']}")

    band = Table([[
        _band_cell("Customer", customer_lines, styles),
        _band_cell("Site", site_lines, styles),
        _band_cell("Report Details", detail_lines, styles),
    ]], colWidths=[PAGE_WIDTH / 3] * 3)
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BAND_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(band)
    story.append(Spacer(1, 14))

    # --- Type-specific sections ---
    if cfg:
        for section in cfg["sections"]:
            block = []
            block.append(_section_header(section["name"], styles))
            block.append(Spacer(1, 6))
            grid = _kv_grid(section["fields"], data, styles)
            if grid:
                block.append(grid)
            for f in section["fields"]:
                if f["type"] == "table":
                    result = _table_field(f, data, styles)
                    if result:
                        label, tbl = result
                        block.append(Spacer(1, 4))
                        block.append(label)
                        block.append(Spacer(1, 2))
                        block.append(tbl)
                        block.append(Spacer(1, 6))
            if len(block) > 2:
                story.append(KeepTogether(block[:2]))
                story.extend(block[2:])
            story.append(Spacer(1, 4))

    # --- Closing / sign-off section ---
    story.append(_section_header(CLOSING_SECTION["name"], styles))
    story.append(Spacer(1, 6))
    grid = _kv_grid(CLOSING_SECTION["fields"], data, styles)
    if grid:
        story.append(grid)

    story.append(Spacer(1, 16))
    sig_tbl = Table([
        ["Technician's Signature: ___________________________", "Date: ______________"],
        ["Manager's Signature: ______________________________", "Date: ______________"],
    ], colWidths=[5 * inch, PAGE_WIDTH - 5 * inch])
    sig_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(sig_tbl)

    doc.build(story)
    return buf.getvalue()
