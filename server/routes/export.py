"""
Ayura AI - Data Export Routes (PDF + CSV)
"""

import csv
import io
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from schemas.user_schema import UserDocument
from routes.profile import get_current_user
from database.mongodb import get_mongodb

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sanitize_csv(val) -> str:
    """Prevent CSV injection by prepending apostrophe to formula starters."""
    val_str = str(val) if val is not None else ""
    if val_str and val_str[0] in ("=", "+", "-", "@"):
        return f"'{val_str}"
    return val_str


def _build_pdf(user: UserDocument, plan_data: dict, generated_at: str) -> bytes:
    """Build a proper PDF wellness report using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2 * cm,
            title=f"Ayura AI Wellness Report — {user.name}",
            author="Ayura AI",
        )

        # ── Colour palette ────────────────────────────────
        TEAL       = HexColor("#0D9488")
        TEAL_LIGHT = HexColor("#2DD4BF")
        AMBER      = HexColor("#F59E0B")
        DARK_BG    = HexColor("#0F1917")
        CARD_BG    = HexColor("#141F1E")
        TEXT_MAIN  = HexColor("#EEF5F4")
        TEXT_SEC   = HexColor("#9DB8B4")
        VATA       = HexColor("#818CF8")
        PITTA      = HexColor("#FB923C")
        KAPHA      = HexColor("#2DD4BF")
        DOSHA_COLORS = {"vata": VATA, "pitta": PITTA, "kapha": KAPHA}

        # ── Styles ────────────────────────────────────────
        styles = getSampleStyleSheet()
        H1 = ParagraphStyle("H1", parent=styles["Title"],  textColor=white,     fontSize=26, leading=30, spaceAfter=6,  fontName="Helvetica-Bold", alignment=TA_CENTER)
        H2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=TEAL_LIGHT, fontSize=14, leading=18, spaceBefore=14, spaceAfter=4,  fontName="Helvetica-Bold")
        H3 = ParagraphStyle("H3", parent=styles["Heading3"], textColor=TEXT_MAIN,  fontSize=11, leading=14, spaceBefore=8,  spaceAfter=2,  fontName="Helvetica-Bold")
        BODY = ParagraphStyle("Body", parent=styles["Normal"], textColor=TEXT_SEC,  fontSize=9, leading=13, spaceAfter=3)
        SMALL = ParagraphStyle("Small", parent=styles["Normal"], textColor=TEXT_SEC, fontSize=8, leading=11)
        LABEL = ParagraphStyle("Label", parent=styles["Normal"], textColor=TEAL, fontSize=8, fontName="Helvetica-Bold", leading=11)
        DISCLAIMER_STYLE = ParagraphStyle("Disc", parent=styles["Normal"], textColor=AMBER, fontSize=7.5, leading=11, alignment=TA_CENTER)

        dosha = (user.dominant_dosha or "pitta").lower()
        dosha_color = DOSHA_COLORS.get(dosha, TEAL)

        story = []

        # ── Cover Block ───────────────────────────────────
        cover_data = [[
            Paragraph("🌿  Ayura AI", H1),
        ]]
        cover_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DARK_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 28),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 28),
            ("LEFTPADDING",   (0, 0), (-1, -1), 20),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
            ("BOX",           (0, 0), (-1, -1), 2, TEAL),
            ("ROUNDEDCORNERS", (0, 0), (-1, -1), [8, 8, 8, 8]),
        ])
        cover_table = Table(cover_data, colWidths=["100%"])
        cover_table.setStyle(cover_style)
        story.append(cover_table)
        story.append(Spacer(1, 0.4 * cm))

        # ── Subtitle ──────────────────────────────────────
        story.append(Paragraph("Personalised Wellness Report", ParagraphStyle("Sub", parent=styles["Normal"], textColor=TEAL_LIGHT, fontSize=12, alignment=TA_CENTER)))
        story.append(Spacer(1, 0.5 * cm))

        # ── User Summary Card ─────────────────────────────
        summary_rows = [
            [Paragraph("Name",         LABEL), Paragraph(user.name or "—", BODY)],
            [Paragraph("Dosha",        LABEL), Paragraph((user.dominant_dosha or "—").title(), BODY)],
            [Paragraph("Goal",         LABEL), Paragraph((user.goal or "—").replace("_", " ").title(), BODY)],
            [Paragraph("BMI",          LABEL), Paragraph(f"{user.bmi or '—'} ({user.bmi_category or '—'})", BODY)],
            [Paragraph("Generated",    LABEL), Paragraph(generated_at, BODY)],
        ]
        summary_tbl = Table(summary_rows, colWidths=[3 * cm, None])
        summary_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), CARD_BG),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("BOX",          (0, 0), (-1, -1), 1, dosha_color),
            ("LINEAFTER",    (0, 0), (0, -1), 0.5, TEAL),
        ]))
        story.append(summary_tbl)
        story.append(Spacer(1, 0.6 * cm))

        # ── Plan Sections ─────────────────────────────────
        PLAN_SECTIONS = [
            ("gym_plan",          "💪  Fitness & Gym Plan",       TEAL),
            ("yoga_plan",         "🧘  Yoga & Pranayama Plan",    TEAL_LIGHT),
            ("diet_plan",         "🥗  Nutrition Plan",           AMBER),
            ("panchakarma_plan",  "🌿  Panchakarma Detox Plan",   HexColor("#10B981")),
            ("home_remedies",     "🍵  Home Remedies",            HexColor("#F43F5E")),
            ("medicines",         "💊  Ayurvedic Medicines",      HexColor("#818CF8")),
        ]

        for key, title, color in PLAN_SECTIONS:
            value = plan_data.get(key)
            if not value:
                continue

            story.append(HRFlowable(width="100%", thickness=0.5, color=color, spaceAfter=4))
            story.append(Paragraph(title, H2))

            if isinstance(value, list):
                for idx, item in enumerate(value[:12]):   # cap at 12 items
                    if isinstance(item, dict):
                        item_name = (
                            item.get("remedy_name") or item.get("medicine_name") or
                            item.get("exercise") or item.get("pose") or f"Item {idx + 1}"
                        )
                        story.append(Paragraph(f"• {item_name}", H3))
                        for field, field_label in [
                            ("symptom_addressed",   "Symptom"),
                            ("preparation",         "Preparation"),
                            ("dosage",              "Dosage"),
                            ("frequency",           "Frequency"),
                            ("warnings",            "Warnings"),
                            ("anupana",             "Anupana"),
                            ("ayurvedic_rationale", "Rationale"),
                        ]:
                            field_val = item.get(field)
                            if field_val:
                                if isinstance(field_val, list):
                                    field_val = ", ".join(str(v) for v in field_val)
                                story.append(Paragraph(f"<b>{field_label}:</b> {field_val}", BODY))
                    else:
                        story.append(Paragraph(f"• {item}", BODY))
                story.append(Spacer(1, 0.3 * cm))

            elif isinstance(value, dict):
                # Render nested dict as a table (2 columns: key, value)
                rows = []
                for k, v in value.items():
                    if k in ("error",):
                        continue
                    v_str = json.dumps(v, default=str) if isinstance(v, (dict, list)) else str(v)
                    rows.append([
                        Paragraph(k.replace("_", " ").title(), LABEL),
                        Paragraph(v_str[:400], SMALL),
                    ])
                if rows:
                    tbl = Table(rows, colWidths=[4 * cm, None])
                    tbl.setStyle(TableStyle([
                        ("BACKGROUND",   (0, 0), (-1, -1), CARD_BG),
                        ("TOPPADDING",   (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
                        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("LINEAFTER",    (0, 0), (0, -1), 0.5, color),
                        ("BOX",          (0, 0), (-1, -1), 0.5, HexColor("#1C2B29")),
                    ]))
                    story.append(tbl)
                    story.append(Spacer(1, 0.3 * cm))

        # ── Disclaimer ────────────────────────────────────
        story.append(Spacer(1, 1 * cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=AMBER, spaceAfter=6))
        story.append(Paragraph(
            "⚠️  This report is generated by AI for informational purposes only. "
            "It does not constitute medical advice, diagnosis, or treatment. "
            "Always consult a qualified healthcare professional before making health decisions.",
            DISCLAIMER_STYLE
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    except ImportError:
        # ReportLab not installed — fall back to plain text
        return None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/csv")
async def export_csv(
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Export progress logs as a sanitised CSV file."""
    cursor = db.progress_logs.find({"user_id": user.id}).sort("date", -1).limit(365)
    logs = await cursor.to_list(length=365)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["date", "weight_kg", "adherence_percent", "mood", "plan_feedback"]
    )
    writer.writeheader()

    for log in logs:
        writer.writerow({
            "date":              _sanitize_csv(log["date"].isoformat() if isinstance(log["date"], datetime) else log.get("date", "")),
            "weight_kg":         _sanitize_csv(log.get("weight_kg", "")),
            "adherence_percent": _sanitize_csv(log.get("adherence_percent", "")),
            "mood":              _sanitize_csv(log.get("mood", "")),
            "plan_feedback":     _sanitize_csv(log.get("plan_feedback", "")),
        })

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ayura_progress_{user.id[:8]}.csv"},
    )


@router.get("/pdf")
async def export_pdf(
    user: UserDocument = Depends(get_current_user),
    db=Depends(get_mongodb),
):
    """Export the latest wellness plan as a properly formatted PDF report."""
    cursor = db.plan_history.find({"user_id": user.id}).sort("generated_at", -1).limit(1)
    plans = await cursor.to_list(length=1)

    if plans:
        plan = plans[0]
        plan_data = plan.get("plan_data", {})
        raw_ts = plan.get("generated_at", "")
        if isinstance(raw_ts, datetime):
            generated_at = raw_ts.strftime("%d %B %Y at %H:%M UTC")
        else:
            generated_at = str(raw_ts)
    else:
        plan_data = {}
        generated_at = datetime.now(timezone.utc).strftime("%d %B %Y at %H:%M UTC")

    pdf_bytes = _build_pdf(user, plan_data, generated_at)

    if pdf_bytes:
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=ayura_report_{user.id[:8]}.pdf"},
        )

    # Graceful fallback if reportlab is not installed
    lines = [
        "Ayura AI Wellness Report",
        f"Name: {user.name}",
        f"Dominant Dosha: {user.dominant_dosha or 'Not assessed'}",
        f"Goal: {user.goal or 'Not set'}",
        f"Generated: {generated_at}",
        "",
        "NOTE: Install 'reportlab' for a proper PDF export.",
        "",
        "=== Your Plan ===",
    ]
    for key, value in plan_data.items():
        if value and key not in ("user_summary", "generated_at", "model_used", "generation_method", "ratings"):
            lines.append(f"\n--- {key.replace('_', ' ').title()} ---")
            lines.append(json.dumps(value, indent=2, default=str))

    content = "\n".join(lines)
    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=ayura_report_{user.id[:8]}.txt"},
    )
