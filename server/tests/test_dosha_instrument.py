"""
The Prakriti instrument and the scorer that reads it must stay in step.

Prakriti is the root input to every engine in this app — diet, yoga, gym, routine and
Panchakarma all branch on it — so a trait the quiz stops asking, or one the scorer
stops weighting, propagates everywhere and shows up nowhere. Nothing goes red: an
unasked trait is simply absent from the answers, and `_TRAIT_WEIGHTS.get(trait, 1.0)`
gives an unweighted one the default.

The check has to cross the front/back boundary because that is where the risk lives:
the questions are authored in `client/src/pages/DoshaQuiz.jsx` and the weights in
`server/engine/dosha_analyzer.py`, with no shared schema between them. Parsing JSX
from a Python test is not elegant, and the structural fix is to serve the instrument
from the backend so one definition feeds both. Until that happens this is the only
place the two can be compared at all.

What made this worth writing: `data/knowledge_base/dosha_profiles.json` carried a
superseded 20-item instrument under `doshaQuizQuestions`, seeded into a collection
nothing read. Its trait ids differed from the live ones — `skin_type` for `skin`,
`body_temperature` for `temperature`, `learning` for `memory` — so comparing that copy
against `_TRAIT_WEIGHTS` showed 15 weighted axes never asked and 14 asked axes
unweighted. It reads exactly like a severe scoring bug and is entirely an artefact of
reading the dead file. The stale set is gone; this test pins the live one.
"""
import json
import re
from pathlib import Path

import pytest

from engine.dosha_analyzer import (
    DOSHA_SCORING_VERSION, _CONSISTENCY_CHECKS, _MENTAL_TRAITS, _PHYSICAL_TRAITS,
    _TRAIT_WEIGHTS,
)

_QUIZ = Path(__file__).resolve().parents[2] / "client" / "src" / "pages" / "DoshaQuiz.jsx"


@pytest.fixture(scope="module")
def quiz_ids() -> set[str]:
    """Every `id:` declared in the quiz page.

    Deliberately not scoped to one array. The page holds the constitution items, the
    Manas Prakriti block and the Vikriti symptom list, and a trait moving between
    those blocks is a change of meaning but not a loss of collection — this test is
    about whether the scorer's inputs are gathered at all.
    """
    if not _QUIZ.exists():
        pytest.skip(f"quiz page not found at {_QUIZ}")
    return set(re.findall(r"id:\s*'([a-z_]+)'", _QUIZ.read_text(encoding="utf-8")))


def test_every_weighted_trait_is_actually_asked(quiz_ids):
    """A weighted trait the quiz never asks contributes nothing, silently. The heavy
    ones make this concrete: `agni_type` carries 2.0 and `memory` 1.8, so losing
    either skews a Prakriti far more than losing `mutra_pattern` at 0.7."""
    missing = sorted(set(_TRAIT_WEIGHTS) - quiz_ids)
    assert not missing, (
        "weighted by `dosha_analyzer` but never collected by the quiz: "
        + ", ".join(f"{t} (weight {_TRAIT_WEIGHTS[t]})" for t in missing)
    )


def test_every_grouping_trait_is_asked(quiz_ids):
    """`_PHYSICAL_TRAITS` and `_MENTAL_TRAITS` decide the body-versus-mind dominance
    split that feeds Manas Prakriti. A trait missing from either group does not fail
    the scoring — it narrows the group, so the split is computed from a subset and
    still looks like an answer."""
    missing = sorted((set(_PHYSICAL_TRAITS) | set(_MENTAL_TRAITS)) - quiz_ids)
    assert not missing, f"used for the body/mind split but not collected: {missing}"


def test_the_consistency_probes_are_asked_and_their_sources_too(quiz_ids):
    """A probe exists to be compared against the trait it shadows. Either half
    missing makes the check vacuous rather than failing."""
    for probe, source in _CONSISTENCY_CHECKS.items():
        assert probe in quiz_ids, f"consistency probe {probe} is not asked"
        assert source in quiz_ids, f"{probe} shadows {source}, which is not asked"


def test_a_consistency_probe_is_never_scored_as_a_trait():
    """The probe duplicates a trait deliberately. Weighting it too would count that
    trait twice and quietly double its influence on the result."""
    doubled = sorted(set(_CONSISTENCY_CHECKS) & set(_TRAIT_WEIGHTS))
    assert not doubled, f"consistency probes also carry scoring weight: {doubled}"


def test_the_superseded_instrument_is_not_back(quiz_ids):
    """`dosha_profiles.json` held a 20-item instrument under `doshaQuizQuestions` that
    nothing read, and reading it produced a convincing false positive. If it returns,
    this fails before it can mislead anyone again."""
    profiles = json.loads(
        (Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
         / "dosha_profiles.json").read_text(encoding="utf-8"))
    assert "doshaQuizQuestions" not in profiles, (
        "the dead question set is back in dosha_profiles.json — the live instrument "
        "is client/src/pages/DoshaQuiz.jsx"
    )
    assert set(profiles) == {"doshas"}


def test_the_seeder_no_longer_writes_the_dead_collection():
    """Asserted on the write itself, not on the name. The name still appears in
    `seed_db.py` in a comment explaining why the write is gone, so a test that merely
    grepped for the string would pass whether or not the write came back."""
    seeder = (Path(__file__).resolve().parent.parent / "scripts"
              / "seed_db.py").read_text(encoding="utf-8")
    writes = re.findall(r'db\[\s*["\']([a-z_]+)["\']\s*\]\s*\.\s*(?:insert_many|insert_one)',
                        seeder)
    assert "dosha_quiz_questions" not in writes, (
        f"the dead collection is being seeded again; writes found: {sorted(set(writes))}")


def test_the_weights_are_differentiated_not_flat():
    """The whole point of a weight table is that traits carry different Prakriti
    signal. A table that has drifted to uniform would score, pass every test above,
    and quietly throw away the clinical judgement encoded in it."""
    weights = set(_TRAIT_WEIGHTS.values())
    assert len(weights) > 3, f"weights have collapsed toward uniform: {sorted(weights)}"
    assert max(_TRAIT_WEIGHTS.values()) / min(_TRAIT_WEIGHTS.values()) >= 2


def test_the_prakriti_study_is_in_the_vaidya_packet():
    """The instrument's clinical accuracy is the one thing no test here can establish,
    so it belongs in the document that goes to the BAMS. Left out, it is an open
    question nobody owns; written down with a protocol, it is a bookable task."""
    packet = (Path(__file__).resolve().parent.parent / "data" / "golden"
              / "vaidya_reviewer_packet.md").read_text(encoding="utf-8")
    assert "Prakriti instrument validation" in packet
    # The protocol's load-bearing detail: an unblinded assessment measures agreement
    # with a suggestion and cannot be re-run.
    assert "without seeing the app's output" in packet
    # And the figures must come from the scorer, not be typed into the prose.
    assert f"currently {DOSHA_SCORING_VERSION}" in packet
