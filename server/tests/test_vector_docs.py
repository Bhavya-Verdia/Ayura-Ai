"""
Regression tests for the RAG corpus that build_vectors.py seeds.

These lock in the failure that shipped silently on 2026-08-12: the yoga KB was
rewritten in yoga_poses.json (113 poses) while build_vectors.py went on reading
yoga_plans.json (10 legacy summaries). Nothing failed, no test broke, and the
enricher kept receiving semantic context describing poses that no longer existed.
Two files with similar names and different consumers drift apart quietly, so the
corpus is asserted against the file the engine actually loads.

Only document construction is exercised — no ChromaDB client, no embedding.
"""
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_vectors import KNOWLEDGE_DIR, get_documents_for_collection  # noqa: E402

# all-MiniLM-L6-v2 truncates at 256 word-pieces. Anything past that is absent from
# the vector with no error, so chunks are held to a char budget that stays inside it.
MAX_CHUNK_CHARS = 900


@pytest.fixture(scope="module")
def poses():
    return json.loads((KNOWLEDGE_DIR / "yoga_poses.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def yoga_docs():
    return [d for d in get_documents_for_collection()["ayurveda"] if d["source"] == "yoga_poses"]


def test_corpus_is_built_from_the_pose_kb_the_engine_reads(yoga_docs):
    """The engine imports yoga_poses.json directly; RAG must describe the same set."""
    from services.yoga_plan_engine import yoga_poses as engine_poses

    engine_names = {p["sanskrit_name"] for p in engine_poses}
    described = {n for n in engine_names for d in yoga_docs if n in d["text"]}
    assert described == engine_names, f"missing from RAG: {sorted(engine_names - described)}"


def test_no_legacy_yoga_plans_documents():
    """yoga_plans.json is still seeded to Mongo by seed_db.py, but it is not the
    semantic context for yoga narrative and must not re-enter the corpus."""
    docs = get_documents_for_collection()
    assert not [d for d in docs["ayurveda"] if d.get("source") == "yoga_plans"]


def test_every_chunk_names_its_pose(yoga_docs, poses):
    """A chunk is retrieved alone. 'Avoid in pregnancy' with no asana attached is
    worse than no context — the enricher may be writing about a different pose."""
    names = {p["sanskrit_name"] for p in poses}
    unnamed = [d["text"][:80] for d in yoga_docs if not any(n in d["text"][:140] for n in names)]
    assert not unnamed, f"anonymous chunks: {unnamed}"


def test_chunks_stay_inside_the_embedder_window(yoga_docs):
    oversized = [(len(d["text"]), d["text"][:60]) for d in yoga_docs if len(d["text"]) > MAX_CHUNK_CHARS]
    assert not oversized, f"chunks past the embedder cut: {oversized}"


def test_safety_information_survives_chunking(yoga_docs, poses):
    """Contraindications must reach the corpus attached to a named pose, not be
    stranded in an instruction chunk's overflow."""
    contraindicated = [p for p in poses if p.get("contraindications")]
    assert contraindicated, "fixture assumption broken: no pose lists contraindications"

    for pose in contraindicated:
        label = pose["sanskrit_name"]
        safety = [d["text"] for d in yoga_docs if label in d["text"] and "Avoid with:" in d["text"]]
        assert safety, f"{label} has contraindications but no safety document"
        first = pose["contraindications"][0].replace("_", " ")
        assert any(first in s for s in safety), f"{label}: '{first}' missing from its safety document"


def test_pose_documents_carry_dosha_metadata(yoga_docs):
    """Retrieval filters on the dosha metadata field; empty values silently narrow it."""
    tagged = [d for d in yoga_docs if d["dosha"]]
    assert len(tagged) / len(yoga_docs) > 0.75
    assert {d["dosha"] for d in tagged} <= {"vata", "pitta", "kapha"}


# ── Pose imagery provenance ──────────────────────────────────────────────────

def test_no_pose_hotlinks_third_party_imagery(poses):
    """64 poses hotlinked artwork belonging to Pocket Yoga — 32 from pocketyoga.com
    and 32 via a third-party Cloudinary account that had copied the same assets —
    on a public product. Removed 2026-08-13; poses render the category schematic
    until licensed or commissioned imagery exists.

    This asserts provenance, not emptiness: self-hosted or properly licensed URLs
    are fine, someone else's CDN is not.
    """
    from urllib.parse import urlparse

    disallowed = {"pocketyoga.com", "www.pocketyoga.com", "res.cloudinary.com"}
    offenders = [
        (p["sanskrit_name"], p["image_url"]) for p in poses
        if p.get("image_url") and urlparse(p["image_url"]).netloc in disallowed
    ]
    assert not offenders, f"third-party imagery back in the KB: {offenders[:5]}"


# ── Home remedies ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def remedy_docs():
    return [d for d in get_documents_for_collection()["remedy"]
            if d["source"] == "home_remedies"]


def test_every_home_remedy_reaches_the_corpus(remedy_docs):
    """The builder read `symptom`, `dosha_imbalance` and `precautions`, none of
    which exist in home_remedies.json — the real keys are `symptom_display`,
    `dosha_cause` and `contraindications`, and `remedies` is a dict keyed by
    dosha rather than a list. All 60 entries therefore embedded as the SAME
    string, "Remedy for None: vata, pitta, kapha. Doshas: . Precautions: None.",
    the dosha names being the dict keys that join() walked. Same failure as the
    yoga poses embedding as "Yoga pose: None."
    """
    raw = json.loads((KNOWLEDGE_DIR / "home_remedies.json").read_text(encoding="utf-8"))
    corpus = " ".join(d["text"] for d in remedy_docs)
    missing = [r["symptom_display"] for r in raw if r["symptom_display"] not in corpus]
    assert not missing, f"symptoms absent from the corpus: {missing[:5]}"


def test_no_home_remedy_doc_is_a_stub(remedy_docs):
    """The tell for a generator reading keys that do not exist: literal "None"
    in the rendered text, and a corpus of near-identical documents."""
    stubs = [d["text"] for d in remedy_docs if "None" in d["text"]]
    assert not stubs, f"unrendered fields: {stubs[:3]}"
    assert len(set(d["text"] for d in remedy_docs)) == len(remedy_docs)


def test_home_remedy_docs_name_their_symptom(remedy_docs):
    """A chunk is retrieved on its own, so it has to say what it is about — the
    embedder truncates and a subject named only in a heading is lost."""
    for d in remedy_docs:
        assert d["text"].lower().startswith("home remedy"), d["text"][:60]


# ── Content-addressed ids ────────────────────────────────────────────────────

def test_ids_follow_content_not_position():
    """Ids were positional (`ayurveda_282`), so they only meant anything while
    document ORDER held: editing one pose left the id pointing at the same slot
    with stale text, and inserting a pose would have shifted every id after it.
    A content hash makes an edited chunk a new id, so a reseed writes it and
    drops the old one instead of overwriting a neighbour.
    """
    from build_vectors import _document_id, _document_index

    a = {"text": "Pose X — breathe steadily."}
    b = {"text": "Pose X — breathe deeply."}
    assert _document_id("ayurveda", a) == _document_id("ayurveda", a)
    assert _document_id("ayurveda", a) != _document_id("ayurveda", b)
    # Same text in different collections stays distinct.
    assert _document_id("ayurveda", a) != _document_id("remedy", a)
    # Position must not participate.
    assert _document_index("ayurveda", [a, b]) == _document_index("ayurveda", [b, a])


def test_the_corpus_has_no_bulk_duplication():
    """60 identical remedy chunks is what a broken generator looks like from the
    outside. Exact duplicates collapse to one id, so this guards the input."""
    from collections import Counter

    for domain, docs in get_documents_for_collection().items():
        worst = Counter(d["text"] for d in docs).most_common(1)
        if worst:
            text, count = worst[0]
            assert count <= 3, f"{domain}: {count} copies of {text[:70]!r}"


# ── Ayurvedic medicines ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def medicines():
    return json.loads((KNOWLEDGE_DIR / "ayurvedic_medicines.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def medicine_docs():
    return [d for d in get_documents_for_collection()["remedy"]
            if d["source"] == "ayurvedic_medicines"]


def test_every_medicine_says_what_it_treats(medicines, medicine_docs):
    """The builder rendered indications from `primary_uses` alone, which is on
    102 of the 157 entries and absent from the other 55 — the only key that
    differs between the two groups. A third of the formulary therefore embedded
    as "Uses: .": a medicine chunk that never states what it is for, which is
    the one thing it gets retrieved for. `conditions` carries the indication on
    every entry, in the vocabulary the engines already match on.
    """
    corpus = {d["text"] for d in medicine_docs}
    for m in medicines:
        clinical = [t for t in corpus if t.startswith(f"Ayurvedic medicine {m['name']} ")]
        assert clinical, f"no clinical document for {m['name']}"
        assert "Treats:" in clinical[0], f"{m['name']} does not say what it treats"
        first = m["conditions"][0].replace("_", " ")
        assert first in clinical[0], f"{m['name']} omits its own indication {first!r}"


def test_medicine_docs_name_their_medicine(medicine_docs):
    """A chunk is retrieved alone, so "do not use in pregnancy" attached to no
    formulation is worse than nothing — the enricher may attribute it anywhere."""
    for d in medicine_docs:
        assert d["text"].startswith((
            "Ayurvedic medicine ", "Composition of the Ayurvedic medicine ",
            "Safety of the Ayurvedic medicine ")), d["text"][:70]


# ── Panchakarma ──────────────────────────────────────────────────────────────

def test_every_panchakarma_protocol_keeps_its_instructions():
    """Instructions sat last in a single blob per protocol, and Raktamokshana
    (278 word-pieces) and Basti (258) ran past the embedder's window — so the
    two protocols with the most procedure to describe were the two that lost it.
    """
    raw = json.loads((KNOWLEDGE_DIR / "panchakarma_plans.json").read_text(encoding="utf-8"))
    corpus = " ".join(d["text"] for d in get_documents_for_collection()["panchakarma"])
    for protocol in raw:
        if protocol.get("instructions"):
            assert protocol["instructions"] in corpus, f"{protocol['name']} lost its procedure"


# ── Shape of every chunk, in every collection ────────────────────────────────

def test_no_chunk_ships_an_unrendered_field():
    """The guard that would have caught all three of these at once.

    Both corpus bugs found so far — the home remedies reading keys that do not
    exist, and the medicines reading a key that only two thirds of the entries
    have — left the same fingerprint in the text: a label with nothing after it,
    or a literal "None" where a value should be. Nothing else notices, because
    plans come from the deterministic engines and a hollow chunk embeds, stores
    and retrieves exactly like a real one. `--check` cannot see it either: the
    text is stable, so its content hash matches and it reports in sync.
    """
    import re

    # "None" only counts where it is the WHOLE value — `Precautions: None.` or
    # `Remedy for None:`. The Panchakarma eligibility criteria legitimately read
    # "Ama: None or mild (Ama must be cleared by Deepana-Pachana first)", which a
    # bare \bNone\b flagged. A guard that cries wolf is a guard someone switches
    # off, so it is narrowed to the shape the real failures took.
    empty_field = re.compile(
        r":\s*[.,;]|\(\)|\[\]|:\s*None\s*(?:[.,;]|$)|\bNone\s*:|\bnan\b")
    for domain, docs in get_documents_for_collection().items():
        offenders = [d["text"][:100] for d in docs if empty_field.search(d["text"])]
        assert not offenders, f"{domain}: unrendered fields — {offenders[:3]}"


def test_the_window_guard_measures_without_disarming_the_tokenizer():
    """`_overflowing_chunks` is the seeder's stop on silent truncation, and it
    has one trap: the live tokenizer pads and truncates to 256, so measuring
    with it reports 256 for everything and never fires. It must measure on a
    copy — and must leave the original truncating, since the ONNX call depends
    on that fixed input shape.

    Built here on a toy word-level vocabulary rather than the real embedder,
    which would mean downloading a 79 MB model inside CI.
    """
    from tokenizers import Tokenizer, models, pre_tokenizers

    from build_vectors import EMBEDDER_WINDOW, _overflowing_chunks

    toy = Tokenizer(models.WordLevel({"word": 0, "[UNK]": 1}, unk_token="[UNK]"))
    toy.pre_tokenizer = pre_tokenizers.Whitespace()
    toy.enable_truncation(max_length=EMBEDDER_WINDOW)

    class _Embedder:
        tokenizer = toy

    long_doc = {"text": "word " * (EMBEDDER_WINDOW + 20), "source": "toy"}
    short_doc = {"text": "word " * 10, "source": "toy"}

    flagged = _overflowing_chunks(_Embedder(), {"remedy": [long_doc, short_doc]})
    assert len(flagged) == 1 and "remedy/toy" in flagged[0]
    assert not _overflowing_chunks(_Embedder(), {"remedy": [short_doc]})
    # The embedder's own tokenizer still truncates, or inference breaks.
    assert len(toy.encode(long_doc["text"]).ids) == EMBEDDER_WINDOW


def test_the_real_corpus_fits_the_embedder_window():
    """The same guard over the shipped corpus, when the model happens to be
    cached locally or baked into the API image. Skipped in CI, where it would
    have to download 79 MB — the seeder runs it unconditionally before it
    writes, so the check is never actually absent where it matters.
    """
    from build_vectors import _overflowing_chunks

    from build_vectors import _embedder_tokenizer

    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        embedder = DefaultEmbeddingFunction()
        # Liveness only: can we obtain a tokenizer at all (i.e. is the 79 MB model
        # present)? This probed `embedder.tokenizer` directly, which chromadb 1.x
        # relocates — so on 1.x the probe raises, this test skips itself, and the
        # assertion below quietly stops running. Ask the seeder's own resolver
        # instead, so the test can only skip for the reason it documents.
        _embedder_tokenizer(embedder)
    except Exception as exc:  # noqa: BLE001 — model not present is the only case
        pytest.skip(f"ONNX embedder unavailable: {exc}")

    assert not _overflowing_chunks(embedder, get_documents_for_collection())


# ── The corpus and the engines must read the same files ──────────────────────

# Engine KB files deliberately absent from the corpus, with the reason. Anything
# NOT listed here has to be ingested — that is the point of the test below.
NOT_IN_CORPUS = {
    # Only the pose KB's `pranayama_sync` line reaches RAG. The technique list is
    # prescribed by the engine, never retrieved as narrative context.
    "pranayama.json",
    # Read by the condition filter as a lookup table, not as prose worth
    # retrieving. Candidate for ingestion — an open decision, not an oversight.
    "drug_herb_interactions.json",
    "condition_protocols.json",
    "medical_constraints.json",
    # A gate, deliberately not narrative. The engine already attaches each matched
    # mechanism to the plan it hands the enricher, so embedding the file would only
    # let RAG surface contraindications for procedures the plan does not contain —
    # the LLM reciting why Vamana is barred in a plan that never proposed Vamana.
    "panchakarma_clinical.json",
}


def _json_files_referenced(path):
    import re
    return set(re.findall(r'"([a-z_]+\.json)"', Path(path).read_text(encoding="utf-8")))


def test_the_corpus_is_built_from_the_files_the_engines_read():
    """The most expensive bug in this file's history, four times over.

    `build_vectors.py` seeded yoga from `yoga_plans.json` (10 legacy summaries)
    while the engine prescribed from `yoga_poses.json` (113). That was found and
    fixed for yoga in August — and the identical split was still live in three
    more domains six days later:

        gym          engine gym_exercises.json (893)   corpus gym_routines.json (10)
        diet         engine diet_foods.json (150)      corpus ayurvedic_foods.json (25)
        panchakarma  engine panchakarma_therapies.json corpus panchakarma_plans.json

    Only four of the ten gym routines even exist in the engine's file, so most of
    what RAG could say about fitness described exercises no plan can contain.

    Comparing the two lists is the check nobody was doing. A file an engine reads
    is either in the corpus or in NOT_IN_CORPUS with a reason.
    """
    engine_dir = Path(__file__).resolve().parent.parent / "services"
    seeded = _json_files_referenced(SCRIPTS / "build_vectors.py")

    missing = {}
    for engine in sorted(engine_dir.glob("*_engine.py")):
        for kb_file in _json_files_referenced(engine) - seeded - NOT_IN_CORPUS:
            missing.setdefault(kb_file, []).append(engine.name)

    assert not missing, (
        "engines read knowledge-base files the RAG corpus never sees: "
        + "; ".join(f"{f} (read by {', '.join(sorted(who))})" for f, who in missing.items()))


def test_every_exercise_the_engine_can_prescribe_is_described():
    """The corpus held ten summaries, six of which were not in the engine's file
    at all.

    The floor here used to be 800, for a library of 893 imported rows. The
    library is now authored — 173 curated movements — so the floor guards what it
    was always for: the corpus collapsing back to a handful of legacy summaries.
    It is not a target, and a curation that removes a movement should not have to
    argue with it."""
    raw = json.loads((KNOWLEDGE_DIR / "gym_exercises.json").read_text(encoding="utf-8"))
    exercises = raw if isinstance(raw, list) else raw.get("exercises", [])
    corpus = " ".join(d["text"] for d in get_documents_for_collection()["fitness"])

    assert len(exercises) > 120, f"the engine's exercise file has shrunk to {len(exercises)}"
    missing = [e["name"] for e in exercises if e["name"] not in corpus]
    assert not missing, f"exercises absent from the corpus: {missing[:5]}"


def test_every_food_the_engine_plates_is_described():
    raw = json.loads((KNOWLEDGE_DIR / "diet_foods.json").read_text(encoding="utf-8"))
    foods = raw if isinstance(raw, list) else raw.get("foods", [])
    corpus = " ".join(d["text"] for d in get_documents_for_collection()["nutrition"])

    missing = [f["name"] for f in foods if f["name"] not in corpus]
    assert not missing, f"foods absent from the corpus: {missing[:5]}"


def test_every_panchakarma_therapy_the_engine_schedules_is_described():
    raw = json.loads((KNOWLEDGE_DIR / "panchakarma_therapies.json").read_text(encoding="utf-8"))
    therapies = raw if isinstance(raw, list) else raw.get("therapies", [])
    corpus = " ".join(d["text"] for d in get_documents_for_collection()["panchakarma"])

    missing = [t["name"] for t in therapies if t["name"] not in corpus]
    assert not missing, f"therapies absent from the corpus: {missing[:5]}"


def test_no_legacy_gym_routines_documents():
    """gym_routines.json stays in seed_db.py for Mongo, as yoga_plans.json does.
    It must not come back as semantic context."""
    assert not [d for d in get_documents_for_collection()["fitness"]
                if d.get("source") == "gym_routines"]


def test_panchakarma_procedures_reach_the_corpus_without_braces():
    """The step-by-step instructions used to be string literals inside
    `panchakarma_engine.py`, so they could not be retrieved at all. They are the most
    concrete text the domain has — what is actually done, in what order — and are
    what the enricher should be grounded on rather than paraphrasing from memory.

    They are templates, so the seeder has to render them as generic prose: a chunk
    reading "Administer 6-8 drops of {oil_name}" would surface a brace to whatever
    reads it.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("_bv", SCRIPTS / "build_vectors.py")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except SystemExit:
        pass

    procedures = json.loads(
        (KNOWLEDGE_DIR / "panchakarma_procedures.json").read_text(encoding="utf-8"))
    rendered = [
        module._strip_placeholders(step)
        for key, entry in procedures.items()
        if not key.startswith("_") and isinstance(entry, dict)
        for step in entry.get("steps", [])
    ]
    assert rendered
    for text in rendered:
        assert "{" not in text and "}" not in text, f"brace survived: {text}"
        assert "_" not in text, f"raw placeholder name survived: {text}"


# ── The overflow guard must fail loudly when it cannot measure ────────────────

class _NoTokenizer:
    """An embedder with no `.tokenizer` — the shape chromadb 1.x's
    DefaultEmbeddingFunction has. Before the fix this made the guard return
    "nothing overflows"."""


def test_the_guard_refuses_to_pass_when_it_cannot_measure(monkeypatch):
    """The regression that motivated these two tests.

    `_overflowing_chunks` used to answer "no tokenizer" with a warning and `[]`,
    which the seeder reads as a clean corpus. So a chromadb upgrade that moved
    `.tokenizer` would not have failed anything — it would have quietly stopped
    checking, and the next over-long chunk would have lost its tail in the store
    with nothing logged. A guard that cannot run must not report success.
    """
    import build_vectors

    monkeypatch.setattr(
        build_vectors, "_embedder_tokenizer",
        lambda e: (_ for _ in ()).throw(RuntimeError("no tokenizer")),
    )
    with pytest.raises(RuntimeError):
        build_vectors._overflowing_chunks(_NoTokenizer(), {})


def test_the_tokenizer_resolver_finds_the_bundled_onnx_one():
    """Resolves on the pinned 0.6.3, where `.tokenizer` is on the embedder itself.
    It moves to `onnx_mini_lm_l6_v2.ONNXMiniLM_L6_V2` in 1.x and the resolver follows
    it there, so this passes on both — which is the point: the pin can move without
    the guard going quiet."""
    from build_vectors import _embedder_tokenizer

    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        tokenizer = _embedder_tokenizer(DefaultEmbeddingFunction())
    except Exception as exc:  # noqa: BLE001 — 79 MB model absent in CI
        pytest.skip(f"ONNX embedder unavailable: {exc}")
    assert tokenizer.encode("triphala").ids


def test_the_declared_window_matches_the_constant():
    """chromadb 1.x publishes the model's token budget; 0.6.3 does not. If an upgrade
    moves the window, every length is measured against the wrong number and over-long
    chunks pass. Both shapes are exercised so the check is correct before and after."""
    from build_vectors import _assert_window_matches_embedder, EMBEDDER_WINDOW

    class _Declares:
        def __init__(self, n): self._n = n
        def max_tokens(self): return self._n

    _assert_window_matches_embedder(_Declares(EMBEDDER_WINDOW))  # agrees: no raise
    with pytest.raises(RuntimeError, match="window"):
        _assert_window_matches_embedder(_Declares(EMBEDDER_WINDOW + 1))
    _assert_window_matches_embedder(_NoTokenizer())  # 0.6.x shape: nothing to check
