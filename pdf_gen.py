"""
Generates a PDF inspection report from an inspection row + its form_data,
driven by the same declarative config in forms_config.py used for the HTML
form. One generic renderer covers all 12 inspection types.
"""
import io
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from forms_config import get_type_config, CLOSING_SECTION

COMPANY_NAME = "Southern Cross Fire Protection"
COMPANY_ADDRESS = "8131 Blaikie Court, Sarasota, FL 34240"
COMPANY_PHONE = "(941) 400-6635"
COMPANY_WEB = "southerncrossfirellc.com"

NAVY = colors.HexColor("#12233f")
ACCENT = colors.HexColor("#c0392b")
LIGHT = colors.HexColor("#eef1f6")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="SCFPTitle", fontName="Helvetica-Bold", fontSize=16,
                           textColor=NAVY, spaceAfter=2))
    ss.add(ParagraphStyle(name="SCFPSub", fontName="Helvetica", fontSize=9,
                           textColor=colors.grey))
    ss.add(ParagraphStyle(name="SCFPSection", fontName="Helvetica-Bold", fontSize=11,
                           textColor=colors.white, spaceBefore=10, spaceAfter=0,
                           backColor=NAVY, leftIndent=4))
    ss.add(ParagraphStyle(name="SCFPLabel", fontName="Helvetica-Bold", fontSize=8,
                           textColor=colors.grey))
    ss.add(ParagraphStyle(name="SCFPValue", fontName="Helvetica", fontSize=9.5,
                           textColor=colors.black))
    ss.add(ParagraphStyle(name="SCFPCell", fontName="Helvetica", fontSize=8,
                           textColor=colors.black, leading=10))
    ss.add(ParagraphStyle(name="SCFPCellHdr", fontName="Helvetica-Bold", fontSize=7.5,
                           textColor=colors.white, leading=9))
    return ss


def _fmt_value(field, value):
    if value is None or value == "":
        return "—"
    if field.get("type") in ("yn", "ynna", "select"):
        return str(value)
    return str(value)


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
    # flatten each cell's 2-line content into a mini-table cell via nested table
    grid_rows = []
    for row in rows:
        grid_rows.append([
            (Table([[c[0]], [c[1]]], colWidths=[3.3 * inch]) if c else "")
            for c in row
        ])
    t = Table(grid_rows, colWidths=[3.55 * inch] * cols)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
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
    header = [Paragraph(c["label"], styles["SCFPCellHdr"]) for c in columns]
    body = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if not any((r.get(c["key"]) not in (None, "")) for c in columns):
            continue
        body.append([Paragraph(_fmt_value(c, r.get(c["key"])), styles["SCFPCell"]) for c in columns])
    if not body:
        return None
    col_width = 7.1 * inch / len(columns)
    t = Table([header] + body, colWidths=[col_width] * len(columns), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return Paragraph(field["label"], styles["SCFPLabel"]), t


def generate_inspection_pdf(inspection_row, client_row, site_row, asset_row=None):
    """Returns PDF bytes for the given inspection."""
    styles = _styles()
    itype = inspection_row["inspection_type"]
    cfg = get_type_config(itype)
    data = json.loads(inspection_row["form_data"] or "{}")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                             topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                             leftMargin=0.45 * inch, rightMargin=0.45 * inch)
    story = []

    # --- Header / letterhead ---
    header_tbl = Table([
        [Paragraph(COMPANY_NAME, styles["SCFPTitle"]),
         Paragraph(cfg["label"] if cfg else itype, ParagraphStyle(
             name="R", parent=styles["SCFPTitle"], alignment=TA_RIGHT, fontSize=13))],
        [Paragraph(f"{COMPANY_ADDRESS} &nbsp;|&nbsp; {COMPANY_PHONE} &nbsp;|&nbsp; {COMPANY_WEB}", styles["SCFPSub"]),
         Paragraph(f"Report #{inspection_row['id']} &nbsp;&nbsp; Date: {inspection_row['inspection_date']}",
                    ParagraphStyle(name="R2", parent=styles["SCFPSub"], alignment=TA_RIGHT))],
    ], colWidths=[4.5 * inch, 2.6 * inch])
    header_tbl.setStyle(TableStyle([
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LINEBELOW", (0, 1), (-1, 1), 1.2, ACCENT),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 10))

    # --- Client / site info block ---
    info_rows = [
        ["Customer", client_row["name"] if client_row else "—",
         "Site", site_row["name"] if site_row else "—"],
        ["Address", f"{site_row['street']}, {site_row['city']}, {site_row['state']} {site_row['zip']}" if site_row else "",
         "Inspector", inspection_row["inspector_name"] or "—"],
    ]
    if asset_row:
        info_rows.append(["Asset", asset_row["label"], "Serial #", asset_row["serial_number"] or "—"])
    info_tbl = Table(info_rows, colWidths=[0.9 * inch, 2.6 * inch, 0.9 * inch, 2.7 * inch])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 8))

    # --- Type-specific sections ---
    if cfg:
        for section in cfg["sections"]:
            block = []
            block.append(Paragraph(section["name"], styles["SCFPSection"]))
            block.append(Spacer(1, 4))
            grid = _kv_grid(section["fields"], data, styles)
            if grid:
                block.append(grid)
            for f in section["fields"]:
                if f["type"] == "table":
                    result = _table_field(f, data, styles)
                    if result:
                        label, tbl = result
                        block.append(Spacer(1, 3))
                        block.append(label)
                        block.append(tbl)
                        block.append(Spacer(1, 4))
            if len(block) > 2:
                story.append(KeepTogether(block[:2]))
                story.extend(block[2:])

    # --- Closing / sign-off section ---
    story.append(Paragraph(CLOSING_SECTION["name"], styles["SCFPSection"]))
    story.append(Spacer(1, 4))
    grid = _kv_grid(CLOSING_SECTION["fields"], data, styles)
    if grid:
        story.append(grid)

    story.append(Spacer(1, 14))
    sig_tbl = Table([
        ["Technician's Signature: ___________________________", "Date: ______________"],
        ["Manager's Signature: ______________________________", "Date: ______________"],
    ], colWidths=[5 * inch, 2.1 * inch])
    sig_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(sig_tbl)

    doc.build(story)
    return buf.getvalue()
