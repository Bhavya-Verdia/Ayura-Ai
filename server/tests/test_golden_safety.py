"""
Golden-case safety invariants as regression tests.

These assert the classical-safety guarantees of the deterministic engines across a
curated synthetic patient set (no LLM, no DB). If a future change reintroduces a
forceful pranayama for a hypertensive patient, a contraindicated medicine, a
Prakriti/Vikriti conflation in Pradhana Karma, etc., the build fails.

See scripts/golden_testset.py for the full grading harness and report generator.
"""
import pytest

from scripts.golden_testset import CASES, run_case, check_invariants


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_has_no_safety_violations(case):
    result = run_case(case)
    violations = check_invariants(case, result)
    assert not violations, f"{case['id']}: " + "; ".join(violations)


def test_pradhana_karma_matches_dominant_dosha():
    """Single-dosha Vikriti must map to its classical Pradhana Karma (CS Su.15):
    Vata→Basti, Pitta→Virechana, Kapha→Vamana (home-adapted to Nasya)."""
    expected = {
        "vata_anxiety_insomnia": {"basti", "basti_matra"},
        "pitta_acidity_migraine": {"virechana"},
        "kapha_obesity_hypothyroid": {"vamana", "nasya"},  # Vamana needs clinic → home Nasya
        "vata_ankylosing_spondylitis": {"basti", "basti_matra"},
    }
    by_id = {c["id"]: c for c in CASES}
    for cid, allowed in expected.items():
        result = run_case(by_id[cid])
        got = result["panchakarma"]["pradhana_karma"]
        assert got in allowed, f"{cid}: Pradhana Karma {got} not in {allowed}"
