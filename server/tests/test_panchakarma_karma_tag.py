"""Which Pradhana Karma course each therapy row belongs to.

PR #57 surfaced the second Karma the KB declares per Vikriti and could not wire it
into treatment. One of the three routes it ruled out was scoring the therapy pool
against it, the pattern PR #53 used for the triage Dosha — and that one was not a
clinical judgement at all, it was a data blocker: none of the 23 rows in
`panchakarma_therapies.json` said which Karma it belonged to.

The tag closes that, and pays for itself on the primary Karma first. Purvakarma and
Paschat rows are not interchangeable across routes — Snehapana is the mandatory
oleation of Vamana and Virechana and no part of a Basti or Nasya course, Samsarjana
Krama re-enters a Koshtha that Nasya and Raktamokshana never empty — and the pool
was ordered by Dosha, goal and preference alone. A Nasya patient and a Vamana
patient were prepared identically.

What is NOT here: the secondary Karma is still not scheduled and still not scored.
That remains the clinical decision `_secondary_karma_deferral` names — for Pitta the
secondary is Raktamokshana, and which conditions justify bloodletting is a Vaidya's
call, not a tag's. This file guards the data and the primary-Karma wiring only.
"""
from services.panchakarma_engine import (
    THERAPIES_PATH,
    _KARMA_ROWS,
    filter_and_score_therapies,
    pk_therapies,
)

KARMA_VOCAB = {"vamana", "virechana", "basti", "basti_matra", "nasya", "raktamokshana"}


def _profile(**over):
    base = dict(
        id="t", age=35, gender="female",
        dominant_dosha="pitta", vikriti_dominant="pitta",
        fitness_level="intermediate", medical_history=[],
        ama_indicator="none", ojas_level="medium", digestion_quality="moderate",
    )
    base.update(over)
    return base


def _prefs(**over):
    base = dict(
        setting="clinic", available_time_days=14, detox_experience="experienced",
        access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
        self_care_time_per_day="2+ hours", panchakarma_goal="detox",
    )
    base.update(over)
    return base


def _order(karma, phase="purvakarma", **pref_over):
    pool = filter_and_score_therapies(
        _profile(), _prefs(**pref_over), phase, pk_therapies, "pitta", None,
        pradhana_karma=karma,
    )
    return [t["id"] for t in pool]


# ── The data ──────────────────────────────────────────────────────────────────

def test_every_row_carries_a_karma():
    """A row without the tag is a row the pool cannot place, and it fails silently:
    `_ROW_KARMA.get(id, ())` simply never matches and the therapy quietly stops
    being preferred for any course."""
    untagged = [t["id"] for t in pk_therapies if not t.get("karma")]
    assert not untagged, f"rows with no `karma`: {untagged}"
    assert len(pk_therapies) == 23


def test_karma_values_come_from_the_engine_vocabulary():
    """`basti_matra` is in the vocabulary and `basti_home` is not — the key names a
    Karma, never a row. A typo here does not raise; it produces a tag that matches
    no selected Karma and never fires."""
    bad = {t["id"]: sorted(set(t["karma"]) - KARMA_VOCAB)
           for t in pk_therapies if set(t["karma"]) - KARMA_VOCAB}
    assert not bad, f"karma values outside the vocabulary: {bad}"


def test_a_pradhana_row_delivers_exactly_one_karma():
    for t in pk_therapies:
        if t["phase"] == "pradhana":
            assert len(t["karma"]) == 1, f"{t['id']} claims {t['karma']}"


def test_every_karma_has_a_row_and_every_pradhana_row_has_a_karma():
    delivered = {k for t in pk_therapies if t["phase"] == "pradhana" for k in t["karma"]}
    assert delivered == KARMA_VOCAB, f"missing routes: {KARMA_VOCAB - delivered}"


def test_the_derived_map_still_matches_the_mapping_it_replaced():
    """`_KARMA_ROWS` was a hand-written dict; it is now the `karma` tag inverted.

    Frozen here because the map is what the declared-capability gate uses to find a
    Karma's rows: an authoring slip that moved `basti_home` from `basti_matra` to
    `basti` would not fail anything else, it would just tell a home patient that
    clinical Niruha Basti is available to them.
    """
    assert _KARMA_ROWS == {
        "vamana":        ("vamana",),
        "virechana":     ("virechana_clinic", "virechana_home"),
        "basti":         ("basti_niruha", "basti_anuvasana"),
        "basti_matra":   ("basti_home",),
        "nasya":         ("nasya_clinic", "nasya_home"),
        "raktamokshana": ("raktamokshana",),
    }


def test_only_pradhana_rows_deliver_a_karma():
    """Abhyanga belongs to all six courses and delivers none of them. A Purvakarma
    row leaking into `_KARMA_ROWS` would tell the capability gate that oil massage
    is a route to Vamana."""
    mapped = {r for rows in _KARMA_ROWS.values() for r in rows}
    non_pradhana = {t["id"] for t in pk_therapies if t["phase"] != "pradhana"}
    assert not (mapped & non_pradhana)


def test_the_classical_claims_are_flagged_unreviewed_and_the_identities_are_not():
    """Which course a preparation belongs to is a clinical claim and carries
    `karma_reviewed: false`, like `contraindications_reviewed` beside it. Which
    Karma the Vamana row performs is not a claim — it is what the row is — so it
    carries no review flag for a Vaidya to be asked about."""
    for t in pk_therapies:
        if t["phase"] == "pradhana":
            assert "karma_reviewed" not in t, f"{t['id']} asks for review of an identity"
        else:
            assert t.get("karma_reviewed") is False, f"{t['id']} lacks karma_reviewed"
        assert len(t.get("karma_basis", "")) > 40, f"{t['id']} has no stated basis"


def test_the_oleation_and_re_entry_rows_are_route_specific():
    """The two authored distinctions the tag exists to express. If these ever widen
    to all six the tag still validates and stops doing anything."""
    by_id = {t["id"]: t for t in pk_therapies}
    for row in ("snehapana_home", "snehapana_clinic"):
        assert set(by_id[row]["karma"]) == {"vamana", "virechana"}
    for row in ("samsarjana_krama_strict", "samsarjana_krama_mild"):
        assert "nasya" not in by_id[row]["karma"]
        assert "raktamokshana" not in by_id[row]["karma"]


def test_the_file_is_authored_not_generated():
    """`scripts/seed_panchakarma_therapies.py` is a refusing stub. It held a Python
    copy of these rows and would delete every authored field on a run."""
    src = (THERAPIES_PATH.parent.parent.parent / "scripts"
           / "seed_panchakarma_therapies.py").read_text(encoding="utf-8")
    assert "RETIRED" in src and "sys.exit(1)" in src


# ── The wiring ────────────────────────────────────────────────────────────────

def test_the_purvakarma_pool_is_ordered_by_the_karma_it_prepares_for():
    """The defect this fixes: identical preparation for every route.

    Shirodhara is Murdha Taila and belongs to the Nasya course; Snehapana is the
    internal oleation of Vamana and Virechana and no part of Nasya. On the same
    profile they must swap.
    """
    for_nasya = _order("nasya")
    for_virechana = _order("virechana")

    assert for_nasya.index("shirodhara") < for_nasya.index("snehapana_clinic")
    assert for_virechana.index("snehapana_clinic") < for_virechana.index("shirodhara")


def test_basti_does_not_lead_with_internal_oleation():
    """Basti's own Purvakarma is Abhyanga plus Swedana; its internal sneha is
    delivered as Anuvasana, not as Snehapana."""
    for_basti = _order("basti")
    assert for_basti.index("abhyanga_clinic") < for_basti.index("snehapana_clinic")


def test_the_karma_never_outranks_dosha_suitability():
    """+1, the same weight as the triage Dosha. A therapy that aggravates the
    vitiated Dosha (-2) must not be promoted past one that pacifies it (+2) by
    belonging to the right course — Udvartana is tagged to Vamana and raises Pitta,
    and a Pitta patient's Vamana prep must not open with it."""
    for_vamana = _order("vamana")
    assert for_vamana.index("udvartana") > for_vamana.index("abhyanga_self")
    assert for_vamana[0] == "abhyanga_self"


def test_a_shamana_plan_prepares_for_nothing():
    """Shamana performs no Karma, so no row may be marked as preparing for one."""
    pool = filter_and_score_therapies(_profile(), _prefs(), "purvakarma", pk_therapies,
                                      "pitta", None, pradhana_karma=None)
    assert not [t for t in pool if "karma_match" in t]


def test_the_tag_is_read_from_the_bundled_kb_not_the_row_handed_in():
    """In production the route hands the engine rows out of Mongo
    (`kb_cache.panchakarma_protocols`). A collection seeded before this tag existed
    has no `karma` on any row — and reading the tag off the row would then match
    nothing, switch the whole mechanism off, and look exactly like a corpus where
    every therapy happened to suit every Karma.

    This is the failure `_therapy_contraindications` already avoids by looking its
    data up by id, and the one the seeder guard in PR #56 was fixed for.
    """
    stale = [{k: v for k, v in t.items() if k != "karma"} for t in pk_therapies]
    assert all("karma" not in t for t in stale)

    pool = filter_and_score_therapies(_profile(), _prefs(), "purvakarma", stale,
                                      "pitta", None, pradhana_karma="nasya")
    ids = [t["id"] for t in pool]
    assert ids.index("shirodhara") < ids.index("snehapana_clinic")
    assert {"shirodhara"} <= {t["id"] for t in pool if t.get("karma_match") == "nasya"}


def test_the_plan_actually_passes_its_karma_to_the_pool(monkeypatch):
    """The parameter defaults to None, so an unpassed argument is not a type error —
    it is the whole feature quietly reverting to the old ordering."""
    from services import panchakarma_engine as eng

    seen = []
    real = eng.filter_and_score_therapies

    def spy(*args, **kwargs):
        seen.append((args[2], kwargs.get("pradhana_karma")))
        return real(*args, **kwargs)

    monkeypatch.setattr(eng, "filter_and_score_therapies", spy)
    plan = eng.generate_panchakarma_plan(
        _profile(vikriti_dominant="kapha", dominant_dosha="kapha"), _prefs())

    karma = plan["clinical_decisions"]["pradhana_karma_selected"]["primary"]
    assert karma, "profile did not reach a Shodhana verdict; the spy proves nothing"
    assert ("purvakarma", karma) in seen, seen
