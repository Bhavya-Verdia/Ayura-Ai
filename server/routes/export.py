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


def diet_report_lines(plan: dict) -> list[tuple[str, str]]:
    """The nutrition plan as (style, text) pairs, ready to be rendered.

    Separate from the PDF so the content can be asserted without a PDF parser —
    `reportlab` writes but does not read, and adding a reader to `requirements.txt`
    for a test would put a production dependency on a test-only need.

    The generic renderer in `_build_pdf` turns each plan key into one table row
    holding `json.dumps(value)[:400]`. A diet plan's `diet_weeks` is ~6 KB, so the
    practitioner got **7%** of it — four hundred characters of escaped JSON where
    twenty-eight days of meals should be — and the safety findings truncated as soon
    as there were more than about two of them. A truncated list of flagged meals is
    worse than none: it reads as the whole list.

    This is the artifact the whole clinical review depends on, and the diet plan is
    the largest thing in it.
    """
    out: list[tuple[str, str]] = []

    rx = plan.get("energy_prescription") or {}
    if rx.get("target_calories"):
        line = f"<b>Energy prescription:</b> {rx['target_calories']} kcal/day"
        if rx.get("band"):
            line += f" (acceptable {rx['band'][0]}-{rx['band'][1]})"
        if rx.get("protein_floor_g"):
            line += f", at least {rx['protein_floor_g']} g protein"
        if rx.get("basis"):
            line += f" — basis: {rx['basis']}"
        out.append(("body", line))

    arc = (plan.get("therapeutic_arc") or {}).get("weeks") or []
    if arc:
        phases = " → ".join(str(w.get("phase")) for w in arc if w.get("phase"))
        out.append(("body", f"<b>Therapeutic arc:</b> {phases}"))
    for w in (plan.get("therapeutic_arc") or {}).get("withheld") or []:
        out.append(("small", f"<b>Phase withheld:</b> {w}"))

    # Safety findings in full. These are the rows a reviewer is here for.
    for field, label in (
        ("condition_safety_alerts", "Foods flagged against a declared condition"),
        ("safety_alerts", "Allergen / intolerance flags"),
        ("dietary_type_alerts", "Dietary-type conflicts"),
        ("withheld_recommendations", "Withheld from the patient's Pathya list"),
        ("advisory_prose_alerts", "Guidance text naming a contraindicated food"),
    ):
        rows = plan.get(field) or []
        if not rows:
            continue
        out.append(("h3", f"{label} ({len(rows)})"))
        for r in rows[:25]:
            if not isinstance(r, dict):
                out.append(("small", f"• {r}"))
                continue
            where = " ".join(str(r[k]) for k in ("week", "day", "meal_slot") if r.get(k))
            # `item` before `food`: a withheld recommendation is a whole sentence and
            # the food word alone ("figs") loses what was actually removed.
            what = (r.get("item") or r.get("food")
                    or ", ".join(r.get("matched_terms") or []))
            why = r.get("condition") or r.get("reason") or ""
            out.append(("small", f"• <b>{where or 'plan'}</b>: {what} — {why}"[:600]))
        if len(rows) > 25:
            out.append(("small", f"… and {len(rows) - 25} more"))

    for field, label in (
        ("conditions_without_food_floor", "No food-safety rule could be derived for"),
        ("conditions_screened_by_terms_only",
         "Screened against a term list only, not food by food"),
    ):
        vals = plan.get(field) or []
        if vals:
            out.append(("small", f"<b>{label}:</b> "
                                 f"{', '.join(str(v).replace('_', ' ') for v in vals)}"))

    for week in plan.get("diet_weeks") or []:
        if not isinstance(week, dict):
            continue
        out.append(("h3", f"Week {week.get('week_number', '?')} — "
                          f"{week.get('phase', '')}".strip(" —")))
        for day, day_data in (week.get("daily_plan") or {}).items():
            if not isinstance(day_data, dict):
                continue
            bits = []
            for slot in ("breakfast", "lunch", "snack", "dinner"):
                meal = day_data.get(slot)
                name = (meal.get("meal_name") or meal.get("name") or ""
                        if isinstance(meal, dict) else str(meal or ""))
                if name:
                    bits.append(f"{slot[:2]}: {name}")
            drink = day_data.get("special_drink")
            if isinstance(drink, dict) and drink.get("name"):
                bits.append(f"drink: {drink['name']}")
            if bits:
                fasting = " [fasting]" if day_data.get("is_fasting") else ""
                out.append(("small", f"<b>{day}</b>{fasting} — {'; '.join(bits)}"))
        out.append(("spacer", ""))
    return out


def _build_pdf(user: UserDocument, plan_data: dict, generated_at: str) -> bytes:
    """Build a proper PDF wellness report using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.colors import HexColor, white
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
        story.append(Paragraph("Personalised Wellness & Vaidya Handoff Summary", ParagraphStyle("Sub", parent=styles["Normal"], textColor=TEAL_LIGHT, fontSize=12, alignment=TA_CENTER)))
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

        # ── Ayurvedic Clinical Profile (Vaidya Handoff) ───
        # The constitutional + current-state assessment is what a registered Vaidya
        # actually needs — far more than a plan dump. Sourced from the user document.
        def _fmt_scores(scores):
            if not isinstance(scores, dict) or not scores:
                return None
            ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
            return ",   ".join(f"{d.title()} {v}%" for d, v in ordered)

        _AGNI_DISPLAY = {
            "sama": "Sama — balanced",
            "vishama": "Vishama — irregular (Vata)",
            "tikshna": "Tikshna — sharp (Pitta)",
            "manda": "Manda — slow (Kapha)",
            "vata": "Vishama — irregular (Vata)",
            "pitta": "Tikshna — sharp (Pitta)",
            "kapha": "Manda — slow (Kapha)",
        }

        if getattr(user, "dosha_scores", None) or getattr(user, "vikriti_scores", None):
            story.append(HRFlowable(width="100%", thickness=0.5, color=dosha_color, spaceAfter=4))
            story.append(Paragraph("🩺  Ayurvedic Clinical Profile (Vaidya Handoff)", H2))

            clinical_rows = []

            def _row(label, value):
                if value:
                    clinical_rows.append([Paragraph(label, LABEL), Paragraph(str(value), BODY)])

            _row("Prakriti (Constitution)",
                 getattr(user, "prakriti_classical_name", None)
                 or (getattr(user, "dosha_constitution_type", "") or "").replace("_", "-").title() or None)
            _row("Prakriti Scores", _fmt_scores(getattr(user, "dosha_scores", None)))
            vik = (getattr(user, "vikriti_dominant", "") or "").title()
            if getattr(user, "vikriti_secondary", None):
                vik += f"  (secondary: {user.vikriti_secondary.title()})"
            _row("Vikriti (Current Imbalance)", vik or None)
            _row("Vikriti Scores", _fmt_scores(getattr(user, "vikriti_scores", None)))
            if getattr(user, "dosha_confidence", None) is not None:
                _row("Assessment Confidence", f"{user.dosha_confidence}%")
            _row("Agni (Digestive Fire)", _AGNI_DISPLAY.get((getattr(user, "agni_type", "") or "").lower()))
            if getattr(user, "ama_indicator", None) and user.ama_indicator != "none":
                _row("Ama (Metabolic Toxins)", user.ama_indicator.title())
            if getattr(user, "ojas_level", None):
                ojas = user.ojas_level.title()
                if getattr(user, "ojas_score", None) is not None:
                    ojas += f"  ({user.ojas_score}/100)"
                _row("Ojas (Vitality)", ojas)
            mp = getattr(user, "manasa_prakriti", None)
            if isinstance(mp, dict) and mp:
                _row("Manasa Prakriti (Triguna)",
                     f"{mp.get('label', '')} — Satva {mp.get('satva', 0)}%, "
                     f"Rajas {mp.get('rajas', 0)}%, Tamas {mp.get('tamas', 0)}%")
            if getattr(user, "primary_gunas", None):
                _row("Dominant Gunas", ", ".join(user.primary_gunas))
            if getattr(user, "medical_history", None):
                _row("Diagnosed Conditions",
                     ", ".join(c.replace("_", " ").title() for c in user.medical_history))
            if getattr(user, "current_medications", None):
                _row("Current Medications", ", ".join(user.current_medications))
            if getattr(user, "allergies", None):
                _row("Allergies", ", ".join(user.allergies))

            if clinical_rows:
                ctbl = Table(clinical_rows, colWidths=[5 * cm, None])
                ctbl.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
                    ("TOPPADDING",    (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
                    ("LINEAFTER",     (0, 0), (0, -1), 0.5, TEAL),
                    ("BOX",           (0, 0), (-1, -1), 1, dosha_color),
                ]))
                story.append(ctbl)
                story.append(Spacer(1, 0.4 * cm))

            # Recent Vikriti trend — last up to 6 weekly check-in snapshots
            hist = getattr(user, "vikriti_history", None) or []
            if hist:
                story.append(Paragraph("Recent Vikriti Trend (weekly check-ins)", H3))
                for entry in hist[-6:]:
                    if not isinstance(entry, dict):
                        continue
                    ts = entry.get("ts") or entry.get("date") or ""
                    if isinstance(ts, datetime):
                        ts = ts.strftime("%d %b %Y")
                    dom = (entry.get("dominant") or "").title()
                    sc = _fmt_scores(entry.get("scores")) or "—"
                    syms = entry.get("symptoms") or []
                    sym_txt = (f"  ·  symptoms: {', '.join(s.replace('_', ' ') for s in syms[:4])}"
                               if syms else "")
                    story.append(Paragraph(f"<b>{ts}</b> — {dom}: {sc}{sym_txt}", SMALL))
                story.append(Spacer(1, 0.5 * cm))

        # ── Plan Sections ─────────────────────────────────
        PLAN_SECTIONS = [
            ("gym_plan",          "💪  Fitness & Gym Plan",       TEAL),
            ("yoga_plan",         "🧘  Yoga & Pranayama Plan",    TEAL_LIGHT),
            ("diet_plan",         "🥗  Nutrition Plan",           AMBER),
            ("panchakarma_plan",  "🌿  Panchakarma Detox Plan",   HexColor("#10B981")),
            ("home_remedies",     "🍵  Home Remedies",            HexColor("#F43F5E")),
            ("medicines",         "💊  Ayurvedic Medicines",      HexColor("#818CF8")),
        ]

        def _render_diet(plan: dict) -> None:
            styles_by_name = {"h3": H3, "body": BODY, "small": SMALL}
            for style, text in diet_report_lines(plan):
                if style == "spacer":
                    story.append(Spacer(1, 0.2 * cm))
                else:
                    story.append(Paragraph(text, styles_by_name[style]))

        for key, title, color in PLAN_SECTIONS:
            value = plan_data.get(key)
            if not value:
                continue

            story.append(HRFlowable(width="100%", thickness=0.5, color=color, spaceAfter=4))
            story.append(Paragraph(title, H2))

            if key == "diet_plan" and isinstance(value, dict):
                _render_diet(value)
                story.append(Spacer(1, 0.3 * cm))
                continue

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
            "⚠️  This summary is generated by AI from self-reported data and a deterministic "
            "Ayurvedic assessment engine. It is intended to be shared with a registered "
            "Ayurvedic physician (Vaidya) or qualified healthcare professional — it does not "
            "constitute medical advice, diagnosis, or treatment. Prakriti and Vikriti are screening "
            "estimates; definitive determination requires in-person examination (including Nadi Pareeksha).",
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
