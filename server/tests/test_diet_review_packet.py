"""The diet review packet must describe the library that exists.

A packet is a document a Vaidya works from for a day and a half. Every count in it is
read as a commitment about how much work is left, so a stale figure is worse than no
figure: it is the one kind of error a reviewer cannot detect from inside the document.
These tests derive the numbers the same way the packet does and check the packet agrees.
"""
import csv
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_diet_review_packet as packet  # noqa: E402

GOLDEN = Path(__file__).resolve().parent.parent / "data" / "golden"
KB = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
     / "diet_foods.json").read_text(encoding="utf-8"))


def _csv(name):
    with (GOLDEN / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_every_clinical_claim_reaches_the_packet():
    """708 row-by-condition claims are the safety-critical surface: a wrong Apathya
    withholds a food from a patient. Losing one silently is the failure to guard."""
    expected = sum(len(r.get("pathya_for", [])) + len(r.get("apathya_for", []))
                   for r in KB)
    assert len(_csv("vaidya_diet_clinical_claims.csv")) == expected
    assert len(_csv("vaidya_diet_foods.csv")) == len(KB)


def test_the_packet_covers_every_extrapolated_row_and_every_prabhava():
    extrapolated = {r["id"] for r in KB
                    if (r.get("nighantu_ref") or {}).get("text") == "modern_extrapolated"}
    assert {r["food_id"] for r in _csv("vaidya_diet_extrapolations.csv")} == extrapolated

    prabhava = {r["id"] for r in KB if r["ayurvedic"].get("prabhava")}
    assert {r["food_id"] for r in _csv("vaidya_diet_prabhava.csv")} == prabhava


def test_the_screen_exempts_a_claim_that_states_its_reason():
    """The screen applies the library's own rule to the clinical tags: a claim running
    against the food's qualities needs a stated reason. A row carrying a Prabhava has
    given one, so it must not be flagged — otherwise the tier fills with rows that
    already answered the question and the reviewer stops trusting it."""
    for row in _csv("vaidya_diet_screened_claims.csv"):
        assert not row["prabhava"], f"{row['food_id']} states a Prabhava but was screened"
        assert row["screen_rule"] and row["screen_saw"], "a screened row must say why"


def test_the_screen_still_fires():
    """A screen that silently stops matching reports a clean library, which is exactly
    the false all-clear this packet exists to prevent."""
    assert len(_csv("vaidya_diet_screened_claims.csv")) > 0


def test_every_reviewable_row_has_somewhere_to_put_a_verdict():
    """A row a reviewer cannot answer is a row that ships unreviewed."""
    for name in ("vaidya_diet_screened_claims.csv", "vaidya_diet_extrapolations.csv",
                 "vaidya_diet_prabhava.csv", "vaidya_diet_viruddha.csv",
                 "vaidya_diet_clinical_claims.csv", "vaidya_diet_foods.csv"):
        rows = _csv(name)
        assert rows, f"{name} is empty"
        assert any(c.endswith("_ok") for c in rows[0]), f"{name} has no verdict column"
        assert "vaidya_notes" in rows[0], f"{name} has no notes column"
        for row in rows:
            for col in (c for c in row if c.endswith("_ok")):
                assert row[col] == "", f"{name} ships with {col} pre-filled"


def test_the_counts_in_the_packet_match_the_library():
    """The numbers a reviewer plans their day around."""
    md = (GOLDEN / "vaidya_diet_packet.md").read_text(encoding="utf-8")
    claims = sum(len(r.get("pathya_for", [])) + len(r.get("apathya_for", []))
                 for r in KB)
    for n, what in ((len(KB), "foods"), (claims, "clinical claims")):
        assert f"**{n} " in md, f"packet does not state {n} {what}"
    for name, count in (("vaidya_diet_screened_claims.csv", len(_csv("vaidya_diet_screened_claims.csv"))),
                        ("vaidya_diet_extrapolations.csv", len(_csv("vaidya_diet_extrapolations.csv"))),
                        ("vaidya_diet_prabhava.csv", len(_csv("vaidya_diet_prabhava.csv")))):
        assert re.search(rf"`{re.escape(name)}` — {count} ", md), \
            f"packet misstates the size of {name}"


def test_the_committed_packet_matches_the_library_it_describes():
    """The drift this file exists to catch.

    The CSVs are committed, and the library they describe changes underneath them. A
    packet regenerated from today's library must equal what is on disk — otherwise a
    Vaidya reviews rows that no longer exist, or misses rows added since. Nothing else
    would go red: a stale CSV parses fine.
    """
    rows = packet._load()
    committed = {
        "vaidya_diet_screened_claims.csv":
            [r for r in packet.build_clinical_claims(rows) if r["screen_rule"]],
        "vaidya_diet_extrapolations.csv": packet.build_extrapolations(rows),
        "vaidya_diet_prabhava.csv": packet.build_prabhava(rows),
        "vaidya_diet_viruddha.csv": packet.build_viruddha(rows),
        "vaidya_diet_clinical_claims.csv": packet.build_clinical_claims(rows),
        "vaidya_diet_foods.csv": packet.build_foods(rows),
    }
    for name, regenerated in committed.items():
        on_disk = _csv(name)
        assert len(on_disk) == len(regenerated), (
            f"{name} is stale — run scripts/build_diet_review_packet.py")
        for a, b in zip(on_disk, regenerated):
            assert a == {k: str(v) for k, v in b.items()}, (
                f"{name} is stale — run scripts/build_diet_review_packet.py")


def test_the_packet_does_not_claim_anything_is_reviewed():
    """`reviewed` is false on all 150. If that ever changes, this packet's framing —
    and its effort estimate — has to change with it."""
    assert not [r for r in KB if r.get("reviewed")], "a row is marked reviewed"
    md = (GOLDEN / "vaidya_diet_packet.md").read_text(encoding="utf-8")
    assert "`reviewed: false`" in md
