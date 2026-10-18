"""
Ayura AI — The Daily Routine (Dinacharya) as a printable PDF.

Made to be printed and put on a wall: white page, dark ink, nothing that relies on
colour alone, one day per page so a single day can be printed on its own. It renders
the routine the person has now, including their own time changes and added items,
because those are rebuilt into `weekly_routine` on the server.

Everything printed comes from fields the app already shows and that have passed its
gates (condition notes, withheld practices, gated coaching). Nothing is generated here.

The PDF's built-in fonts cover Western European text only. Sanskrit in IAST (ā, ś, ṇ)
is folded to plain letters and arrows to "->" rather than printed as empty boxes.
"""
from __future__ import annotations

import io
import unicodedata
from datetime import datetime
from typing import Iterable, Optional
from xml.sax.saxutils import escape

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

_REPLACE = {"→": "->", "←": "<-", "≥": ">=", "≤": "<=", "✓": "", "✦": "*", "•": "-",
            "≈": "~", "½": "1/2", "¼": "1/4", "​": ""}


def text(value) -> str:
    """Safe for a reportlab Paragraph: XML-escaped, and only characters the built-in
    fonts can draw (cp1252), so nothing prints as a black box."""
    return escape(plain(value))


def plain(value) -> str:
    """Only characters the built-in fonts can draw; not escaped (for canvas text)."""
    s = str(value if value is not None else "")
    for a, b in _REPLACE.items():
        s = s.replace(a, b)
    out = []
    for ch in s:
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            folded = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
            try:
                folded.encode("cp1252")
                out.append(folded)
            except UnicodeEncodeError:
                continue
    return "".join(out)


def _lines(value) -> list[str]:
    """A field that may be a string, a list, or a dict of strings, as lines."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out = []
        for k, v in value.items():
            if isinstance(v, (str, int, float)) and str(v).strip():
                out.append(f"{str(k).replace('_', ' ').capitalize()}: {v}")
            elif isinstance(v, list):
                out += [str(x) for x in v if isinstance(x, (str, int, float))]
        return out
    if isinstance(value, list):
        out = []
        for x in value:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                item = x.get("item") or x.get("name") or x.get("practice") or ""
                reason = x.get("reason") or x.get("note") or ""
                if item or reason:
                    out.append(f"{item} — {reason}" if item and reason else item or reason)
        return out
    return [str(value)]


def exercise_limit_lines(limits) -> list[str]:
    """Worded as RoutineView words it; the field itself is flags, not prose."""
    if not isinstance(limits, dict):
        return []
    if limits.get("reasons"):
        pace = "gentle" if limits.get("cap") == "gentle" else "to a pace you can talk through"
        impact = " and low impact" if limits.get("low_impact") else ""
        return [f"Exercise is kept {pace}{impact}, because of {' and '.join(map(str, limits['reasons']))}."]
    if limits.get("low_impact"):
        return ["Exercise is kept low impact — no running or jumping."]
    return []


def select_days(plan: dict, day: str, today_index: int) -> list[dict]:
    days = [d for d in plan.get("weekly_routine") or [] if isinstance(d, dict)]
    if day == "all":
        return days
    idx = today_index if day == "today" else int(day)
    return [d for d in days if int(d.get("day", -1)) == idx] or days[idx:idx + 1]


def build_routine_pdf(plan: dict, name: str, day: str = "all", today_index: int = 0,
                      generated_on: Optional[datetime] = None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (KeepInFrame, KeepTogether, PageBreak, Paragraph,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)

    MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 1.8 * cm, 1.3 * cm, 1.8 * cm
    FRAME_W = A4[0] - 2 * MARGIN_X - 12          # SimpleDocTemplate's frame padding
    FRAME_H = A4[1] - MARGIN_TOP - MARGIN_BOTTOM - 12
    INK = colors.HexColor("#1f2421")
    MUTED = colors.HexColor("#5b615d")
    ACCENT = colors.HexColor("#9a4a12")      # terracotta, AA on white
    RULE = colors.HexColor("#d9d4cb")
    SHADE = colors.HexColor("#f5f1ea")

    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=20,
                        textColor=INK, alignment=TA_LEFT, spaceAfter=2)
    SUB = ParagraphStyle("Sub", parent=ss["Normal"], fontSize=10, textColor=MUTED, spaceAfter=10)
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13,
                        textColor=ACCENT, spaceBefore=10, spaceAfter=6)
    BODY = ParagraphStyle("Body", parent=ss["Normal"], fontSize=9, leading=11.6, textColor=INK)
    SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8, leading=10.2, textColor=MUTED)
    NOTE = ParagraphStyle("Note", parent=SMALL, fontName="Helvetica-Oblique", textColor=ACCENT)
    CELL_B = ParagraphStyle("CellB", parent=BODY, fontName="Helvetica-Bold")

    proto = plan.get("dinacharya_protocol") or {}
    summary = plan.get("user_summary") or {}
    story: list = []

    def P(s, style=BODY):
        return Paragraph(text(s), style)

    def bullets(items: Iterable[str], style=BODY):
        for it in items:
            story.append(Paragraph("- " + text(it), style))

    def table(rows, widths, header=True):
        t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
        style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                 ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), SHADE), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT)]
        t.setStyle(TableStyle(style))
        return t

    # ── Cover: who, when, the shape of the day ─────────────────────────────
    story.append(Paragraph("Daily Routine — Dinacharya", H1))
    meta = [name or "", f"{str(summary.get('dominant_dosha') or '').title()} constitution" if summary.get("dominant_dosha") else "",
            proto.get("season_label") or "", (generated_on or datetime.now()).strftime("%d %b %Y")]
    story.append(P(" · ".join(m for m in meta if m), SUB))

    facts = [["Wake", "Sleep", "Sleep length", "Agni"],
             [proto.get("wake_time") or "—", proto.get("sleep_time") or "—",
              f"{proto.get('sleep_hours')} h" if proto.get("sleep_hours") else "—",
              str(proto.get("agni_type") or summary.get("agni_type") or "—").title()]]
    story.append(table([[P(c, CELL_B) for c in facts[0]], [P(c) for c in facts[1]]], [4.2 * cm] * 4))
    story.append(Spacer(1, 6))

    for s in (plan.get("plan_description"), plan.get("motivational_note"), proto.get("key_principle")):
        if s:
            story.append(P(s))
            story.append(Spacer(1, 3))
    notices = (_lines(proto.get("wake_notice")) + _lines(proto.get("sleep_notice")) +
               _lines(proto.get("pregnancy_notices")) + _lines(plan.get("fasting_notice")) +
               exercise_limit_lines(plan.get("exercise_limits")))
    notices = [n for n in notices if n and n != "None"]
    if notices:
        story.append(Paragraph("Please note", H2))
        bullets(notices, NOTE)

    def rituals(title, items):
        items = [r for r in items or [] if isinstance(r, dict)]
        if not items:
            return
        story.append(Paragraph(title, H2))
        rows = [[P("Practice", CELL_B), P("Min", CELL_B), P("How", CELL_B)]]
        rows += [[P(r.get("name")), P(r.get("duration_min") or ""), P(r.get("instruction"))] for r in items]
        story.append(table(rows, [4.2 * cm, 1.3 * cm, 11.3 * cm]))

    rituals("Morning rituals", proto.get("morning_rituals"))
    rituals("Evening rituals", proto.get("evening_rituals"))
    withheld = _lines(proto.get("withheld_practices"))
    if withheld:
        story.append(P("Left out of your routine:", SMALL))
        bullets(withheld, SMALL)

    # ── One page per day ───────────────────────────────────────────────────
    for d in select_days(plan, day, today_index):
        story.append(PageBreak())
        page: list = []
        label = d.get("day_name") or DAY_NAMES[int(d.get("day", 0)) % 7]
        tags = [d.get("exercise_label")] + (["Fasting day"] if d.get("is_fasting_day") else []) + \
               (["Rest day"] if d.get("is_rest_day") else [])
        page.append(Paragraph(text(label), H1))
        page.append(P(" · ".join(t for t in tags if t) + f" · wake {d.get('wake_time') or proto.get('wake_time')}"
                      f" · sleep {d.get('sleep_time') or proto.get('sleep_time')}", SUB))
        rows = [[P("Time", CELL_B), P("", CELL_B), P("What to do", CELL_B)]]
        for it in d.get("timeline") or []:
            if not isinstance(it, dict):
                continue
            detail = [Paragraph(text(it.get("description")), BODY)] if it.get("description") else []
            notes = _lines(it.get("condition_notes")) or _lines(it.get("condition_note"))
            for n in dict.fromkeys(notes + _lines(it.get("agni_note"))):
                detail.append(Paragraph(text(n), NOTE))
            rows.append([P(it.get("time"), CELL_B), P("[  ]", SMALL),
                         [Paragraph(text(it.get("activity")), CELL_B)] + detail])
        page.append(table(rows, [2.2 * cm, 0.9 * cm, 13.7 * cm]))
        if d.get("sleep_notice"):
            page.append(Spacer(1, 4))
            page.append(P(d["sleep_notice"], NOTE))
        # One day, one sheet: a day with many condition notes is scaled down slightly
        # rather than leaving its last row (always "Sleep") alone on a second page.
        story.append(KeepInFrame(FRAME_W, FRAME_H, page, mode="shrink"))

    # ── Food, season, coaching ─────────────────────────────────────────────
    meals = plan.get("meal_guidance") or {}
    seasonal = plan.get("seasonal_ritucharya") or {}
    coaching = [(t, plan.get(k)) for t, k in (("Your constitution", "dosha_coaching"),
                                               ("Your digestion (Agni)", "agni_coaching"),
                                               ("Sleep", "sleep_coaching"),
                                               ("How your plans fit together", "integration_note"),
                                               ("This season", "seasonal_rationale")) if plan.get(k)]
    if meals or seasonal or coaching:
        story.append(PageBreak())
    if meals:
        story.append(Paragraph("Meals", H2))
        if meals.get("general"):
            story.append(P(meals["general"]))
            story.append(Spacer(1, 4))
        rows = [[P("Meal", CELL_B), P("Time", CELL_B), P("Favour", CELL_B), P("Avoid", CELL_B)]]
        for slot in ("breakfast", "lunch", "snack", "dinner"):
            m = meals.get(slot)
            if isinstance(m, dict):
                rows.append([P(slot.title(), CELL_B), P(m.get("ideal_time") or ""),
                             P(", ".join(map(str, m.get("favour") or []))),
                             P(", ".join(map(str, m.get("avoid") or [])))])
        if len(rows) > 1:
            story.append(table(rows, [2.4 * cm, 2.2 * cm, 6.1 * cm, 6.1 * cm]))
        for k in ("agni_note", "seasonal_note"):
            if meals.get(k):
                story.append(Spacer(1, 3))
                story.append(P(meals[k], SMALL))
        if _lines(meals.get("withheld")):
            story.append(P("Left out of the food guidance for you:", SMALL))
            bullets(_lines(meals.get("withheld")), SMALL)
    if seasonal:
        block = [Paragraph(text(f"Season — {seasonal.get('season') or ''}"), H2)]
        for label, key in (("Favour", "recommended_foods"), ("Avoid", "foods_to_avoid"),
                           ("Practices", "seasonal_practices")):
            vals = _lines(seasonal.get(key))
            if vals:
                block.append(Paragraph(f"<b>{label}:</b> " + text(", ".join(vals)), BODY))
        if _lines(seasonal.get("withheld")):
            block.append(Paragraph(text("Left out for you: " + "; ".join(_lines(seasonal.get("withheld")))), SMALL))
        story.append(KeepTogether(block))
    for title, body in coaching:
        story.append(Paragraph(text(title), H2))
        for line in _lines(body):
            story.append(P(line))

    story.append(Spacer(1, 12))
    story.append(P(plan.get("disclaimer") or "Wellness guidance, not a substitute for examination by a "
                   "registered Vaidya or physician.", SMALL))

    footer_name = plain(name or "")

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(1.8 * cm, 1.0 * cm, f"Ayura AI · Daily Routine{' for ' + footer_name if footer_name else ''}")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X,
                            topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
                            title="Daily Routine — Ayura AI", author="Ayura AI")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
