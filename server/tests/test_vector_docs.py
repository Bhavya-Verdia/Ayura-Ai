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
