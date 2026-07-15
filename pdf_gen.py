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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image
)
from reportlab.lib.utils import ImageReader
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


def _signature_image(sig_bytes, max_width=2.4 * inch, max_height=0.65 * inch):
    """Turns saved signature-pad PNG bytes into a reportlab Image flowable,
    scaled down to fit the sign-off line while preserving aspect ratio.
    Returns None if there's nothing to draw."""
    if not sig_bytes:
        return None
    try:
        reader = ImageReader(io.BytesIO(sig_bytes))
        iw, ih = reader.getSize()
        scale = min(max_width / iw, max_height / ih)
        return Image(io.BytesIO(sig_bytes), width=iw * scale, height=ih * scale)
    except Exception:
        return None


def _thumbnail_image(file_bytes, content_type, max_size=1.3 * inch):
    """Small square-ish thumbnail for the Deficiency Report section. Only
    works for image attachments — non-image files (e.g. a stray PDF) get no
    preview, just their caption. Returns None if there's nothing to draw."""
    if not file_bytes or not (content_type or "").startswith("image/"):
        return None
    try:
        reader = ImageReader(io.BytesIO(file_bytes))
        iw, ih = reader.getSize()
        scale = min(max_size / iw, max_size / ih)
        return Image(io.BytesIO(file_bytes), width=iw * scale, height=ih * scale)
    except Exception:
        return None


def generate_inspection_pdf(inspection_row, client_row, site_row, asset_row=None, attachments=None):
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

    # --- Deficiency Report — one row per uploaded photo, thumbnail + the
    # description entered for it, so a phone photo with a one-line caption
    # becomes a documented finding on the printed report ---
    if attachments:
        story.append(Spacer(1, 14))
        story.append(_section_header("Deficiency Report / Photo Documentation", styles))
        story.append(Spacer(1, 6))
        for idx, att in enumerate(attachments, start=1):
            thumb = _thumbnail_image(att["file_data"], att["content_type"])
            caption_text = att["caption"] or "No description provided"
            item_tbl = Table(
                [[thumb or Paragraph("[No preview available]", styles["SCFPSub"]),
                  Paragraph(f"<b>{idx}.</b> {caption_text}", styles["SCFPValue"])]],
                colWidths=[1.4 * inch, PAGE_WIDTH - 1.4 * inch],
            )
            item_tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE_GRAY),
            ]))
            story.append(KeepTogether([item_tbl]))

    story.append(Spacer(1, 16))
    manager_name_text = f"Manager Name: {inspection_row['manager_name']}" if inspection_row["manager_name"] \
        else "Manager Name: ______________________________"
    manager_date_text = f"Date: {inspection_row['manager_sign_date']}" if inspection_row["manager_sign_date"] \
        else "Date: ______________"
    manager_sig_image = _signature_image(inspection_row["manager_signature"])
    tech_sig_name_text = f"Technician Name: {inspection_row['tech_signoff_name']}" if inspection_row["tech_signoff_name"] \
        else "Technician Name: ______________________________"
    tech_sig_date_text = f"Date: {inspection_row['tech_sign_date']}" if inspection_row["tech_sign_date"] \
        else "Date: ______________"
    tech_sig_image = _signature_image(inspection_row["tech_signature"])
    sig_rows = [
        [tech_sig_name_text, ""],
        [tech_sig_image or "Technician's Signature: ___________________________", tech_sig_date_text],
        [manager_name_text, ""],
        [manager_sig_image or "Manager's Signature: ______________________________", manager_date_text],
    ]
    sig_tbl = Table(sig_rows, colWidths=[5 * inch, PAGE_WIDTH - 5 * inch])
    sig_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(sig_tbl)

    doc.build(story)
    return buf.getvalue()


def generate_service_call_pdf(call):
    """Returns PDF bytes for a service call — a printable work order the
    office can hand to a technician or keep on file. Pre-fills everything
    known at scheduling time, and leaves blank fill-in lines for the
    on-site completion details (arrival/departure, work performed,
    tag/compliance, signatures) modeled on SCFP's own paper work order."""
    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                             topMargin=0.55 * inch, bottomMargin=0.5 * inch,
                             leftMargin=0.45 * inch, rightMargin=0.45 * inch)
    story = []

    # --- Letterhead ---
    title_text = (call["call_type"] or "Service Call").upper()
    wo = call["work_order_number"] or f"SCFP-{call['id']}"
    header_tbl = Table([
        [Paragraph(title_text, styles["SCFPTitle"]),
         Paragraph(f"Work Order #{wo}<br/>Date: {call['scheduled_date']}"
                    f"{' at ' + call['scheduled_time'] if call['scheduled_time'] else ''}",
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

    # --- Blush info band: Customer / Site / Work Order Details ---
    if call["site_id"]:
        customer_lines = [call["client_name"] or "—"]
        addr_bits = [call["site_street"], call["site_city"], call["site_state"], call["site_zip"]]
        site_lines = [call["site_name"] or "—",
                      ", ".join(b for b in addr_bits if b)]
    else:
        customer_lines = [call["customer_name"] or "—"]
        site_lines = [call["location_address"] or "—"]

    detail_lines = [f"Status: {call['status']}", f"Assigned To: {call['assigned_to_name'] or 'Unassigned'}"]

    band = Table([[
        _band_cell("Customer", customer_lines, styles),
        _band_cell("Site / Location", site_lines, styles),
        _band_cell("Work Order Details", detail_lines, styles),
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

    # --- Contact ---
    contact_fields = [
        {"key": "contact_name", "label": "Contact Name", "type": "text"},
        {"key": "contact_phone", "label": "Contact Phone", "type": "text"},
    ]
    contact_data = {"contact_name": call["contact_name"], "contact_phone": call["contact_phone"]}
    story.append(_section_header("Contact", styles))
    story.append(Spacer(1, 6))
    grid = _kv_grid(contact_fields, contact_data, styles)
    if grid:
        story.append(grid)
    story.append(Spacer(1, 4))

    # --- Reason for call ---
    story.append(_section_header("Reason for Call", styles))
    story.append(Spacer(1, 6))
    story.append(Paragraph(call["description"] or "—", styles["SCFPValue"]))
    if call["notes"]:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Office Notes: " + call["notes"], styles["SCFPSub"]))
    story.append(Spacer(1, 10))

    # --- On-site completion — uses what the tech recorded in the app when
    # available, otherwise falls back to blank fill-in lines for hand-writing ---
    story.append(_section_header("On-Site Verification — To Be Completed by Technician", styles))
    story.append(Spacer(1, 6))
    arrival_text = f"Arrival Time: {call['check_in_time']}" if call["check_in_time"] else "Arrival Time: _______________"
    departure_text = f"Departure Time: {call['check_out_time']}" if call["check_out_time"] else "Departure Time: _______________"
    num_tech_text = f"Number of Technicians: {call['num_technicians']}" if call["num_technicians"] \
        else "Number of Technicians: _______"
    tech_names_text = f"Name(s) of Technician(s): {call['technician_names']}" if call["technician_names"] \
        else "Name(s) of Technician(s): ___________________"
    onsite_tbl = Table([
        [arrival_text, departure_text],
        [num_tech_text, tech_names_text],
    ], colWidths=[PAGE_WIDTH / 2] * 2)
    onsite_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(onsite_tbl)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Description of Work Completed (include all work done and materials used):",
                            styles["SCFPLabel"]))
    story.append(Spacer(1, 4))
    if call["work_performed"]:
        work_box = Table([[Paragraph(call["work_performed"], styles["SCFPValue"])]],
                          colWidths=[PAGE_WIDTH])
        work_box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, RULE_GRAY),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(work_box)
    else:
        blank_box = Table([[""]], colWidths=[PAGE_WIDTH], rowHeights=[0.9 * inch])
        blank_box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, RULE_GRAY)]))
        story.append(blank_box)
    story.append(Spacer(1, 10))

    def _yn_line(value):
        yes_mark = "X" if value == "Yes" else " "
        no_mark = "X" if value == "No" else " "
        return f"[ {yes_mark} ] Yes     [ {no_mark} ] No"

    tagged_line = "Is this system properly tagged and/or compliant?   " + _yn_line(call["system_tagged_compliant"])
    return_trip_line = "Is a return trip needed?   " + _yn_line(call["return_trip_needed"])
    return_trip_line += "     Note: " + (call["return_trip_note"] or "______________________________")
    yn_tbl = Table([
        [tagged_line],
        [return_trip_line],
    ], colWidths=[PAGE_WIDTH])
    yn_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, RULE_GRAY),
    ]))
    story.append(yn_tbl)

    # --- Sign-off — uses the manager name/signature/date captured in the app
    # when available, otherwise leaves blank fill-in lines ---
    story.append(Spacer(1, 14))
    story.append(_section_header("Sign-Off", styles))
    story.append(Spacer(1, 8))
    manager_name_text = f"Customer / Manager Name: {call['manager_name']}" if call["manager_name"] \
        else "Customer / Manager Name: _________________________"
    manager_date_text = f"Date: {call['manager_sign_date']}" if call["manager_sign_date"] else "Date: ______________"
    manager_sig_image = _signature_image(call["manager_signature"])
    tech_sig_name_text = f"Technician Name: {call['tech_signoff_name']}" if call["tech_signoff_name"] \
        else "Technician Name: ___________________________"
    tech_sig_date_text = f"Date: {call['tech_sign_date']}" if call["tech_sign_date"] else "Date: ______________"
    tech_sig_image = _signature_image(call["tech_signature"])
    sig_rows = [
        [tech_sig_name_text, ""],
        [tech_sig_image or "Technician's Signature: ___________________________", tech_sig_date_text],
        [manager_name_text, ""],
        [manager_sig_image or "Customer / Manager Signature: _____________________", manager_date_text],
    ]
    sig_tbl = Table(sig_rows, colWidths=[5 * inch, PAGE_WIDTH - 5 * inch])
    sig_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(sig_tbl)

    doc.build(story)
    return buf.getvalue()
