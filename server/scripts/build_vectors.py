"""
Ayura AI - Vector Embedding Builder
Embeds knowledge base documents into ChromaDB for RAG retrieval.
Run: python scripts/build_vectors.py
"""

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # the server/ root, so app modules import

import chromadb
from chromadb.config import Settings

KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "knowledge_base"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chromadb"


def get_embedder():
    """Return the SINGLE shared embedder that the app also queries with, so seeding
    and querying can never diverge. Previously this could pick Azure embeddings
    (1536-dim) while the app queried with the default (384-dim) — that silent
    mismatch took production RAG down. Now both sides go through the same
    database.chromadb_client.get_embedding_function() (default ONNX all-MiniLM-L6-v2,
    384-dim; no external API, deterministic, identical everywhere)."""
    from database.chromadb_client import get_embedding_function
    print("  ℹ️  Using shared ChromaDB embedder (ONNX all-MiniLM-L6-v2, 384-dim)")
    return get_embedding_function()


def _metadata(doc: dict) -> dict:
    return {
        "dosha": doc.get("dosha", ""),
        "source": doc.get("source", ""),
        "source_credibility": doc.get("source_credibility", "general"),
        "pmid": doc.get("pmid", ""),
    }


def _document_id(domain: str, doc: dict) -> str:
    """A chunk's id, derived from its own content.

    Ids used to be positional (`ayurveda_282`), which made them meaningful only
    for as long as document ORDER held. Editing one pose's text left the id
    pointing at the same slot with stale content and nothing to notice it; worse,
    inserting a pose would have shifted every id after it, so a targeted repair
    could silently overwrite the wrong chunk. Hashing the text means an edited
    chunk gets a new id, so a reseed writes it and drops the old one, and an
    unchanged chunk keeps its id and is never re-embedded.

    Metadata is deliberately NOT hashed: it is derived from the same source text
    and including it would only make ids churn for cosmetic reasons.
    """
    digest = hashlib.sha256(doc["text"].encode("utf-8")).hexdigest()[:16]
    return f"{domain}_{digest}"


def _document_index(domain: str, docs: list[dict]) -> dict[str, dict]:
    """Ids → documents, with exact duplicates collapsed.

    Two identical chunks hash to one id. That is correct — they would return the
    same text to the same query — but it means the collection can legitimately
    hold fewer rows than the generator produced, so counts are compared against
    this index rather than against `len(docs)`.
    """
    return {_document_id(domain, d): d for d in docs}


EMBEDDER_WINDOW = 256


def _overflowing_chunks(embedder, doc_sets: dict[str, list[dict]]) -> list[str]:
    """Chunks the embedder will silently truncate, as `domain/source: length — text`.

    all-MiniLM-L6-v2 stops at 256 word-pieces, and everything past the cut is
    absent from the vector with nothing raised and nothing logged. That is how a
    formulation lost its dosage line off the end and how two Panchakarma
    protocols lost their entire instructions field — both invisible until
    something tokenized them.

    Characters are a bad proxy: a 999-char study abstract fits in 248
    word-pieces, while an 877-char formulation full of Latin binomials needs
    269, so a char budget loose enough for the abstract cannot catch the
    formulation. Tokenizing is the only honest check, which is why this lives in
    the seeder — where the embedder is already loaded — rather than in a test
    that would have to download a 79 MB model to run.

    Measured on a COPY of the tokenizer. The live one pads and truncates to the
    window, so every sequence measures exactly 256 and nothing ever looks too
    long; turning that off in place would break the fixed input shape the ONNX
    call depends on.
    """
    tokenizer = getattr(embedder, "tokenizer", None)
    if tokenizer is None:  # not the bundled ONNX embedder — nothing to measure with
        print("  ⚠️  Embedder exposes no tokenizer — chunk lengths unchecked")
        return []

    from tokenizers import Tokenizer

    probe = Tokenizer.from_str(tokenizer.to_str())
    probe.no_truncation()
    probe.no_padding()

    over = []
    for domain, docs in doc_sets.items():
        for doc in docs:
            length = len(probe.encode(doc["text"]).ids)
            if length > EMBEDDER_WINDOW:
                over.append(f"{domain}/{doc.get('source', '?')}: {length} word-pieces "
                            f"— {doc['text'][:70]}…")
    return over


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    """Split text into chunks for embedding."""
    sentences = text.replace(". ", ".\n").split("\n")
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) > max_chars:
            if current:
                chunks.append(current.strip())
            current = s
        else:
            current += " " + s
    if current:
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 30]


def _humanise(tags: list[str]) -> str:
    """`herniated_disc` → `herniated disc`. The KB stores machine keys; the embedder
    reads English, and underscored tokens do not match how a query phrases them."""
    return ", ".join(t.replace("_", " ") for t in tags)


def _yoga_pose_docs(pose: dict) -> list[dict]:
    """One pose → a practice document and a safety/rationale document.

    Two documents rather than one because the shared embedder (all-MiniLM-L6-v2)
    truncates at 256 word-pieces: a single blob carrying names, benefits, instructions,
    contraindications AND rationale runs past that on most poses, and everything past
    the cut is silently absent from the vector. Splitting also stops a long instruction
    list from burying the contraindications.

    Every chunk re-states the pose name. A chunk retrieved on its own must say which
    pose it is describing — an anonymous "avoid in pregnancy" is worse than no context
    at all when the enricher is writing about a different asana.
    """
    label = f"{pose.get('sanskrit_name')} ({pose.get('english_name')})"
    balance = pose.get("dosha_balance", {}) or {}
    balances = [d for d, effect in balance.items() if effect == "balances"]
    aggravates = [d for d, effect in balance.items() if effect == "aggravates"]

    practice = (
        f"Yoga pose: {label}. Category: {pose.get('category')}, level: {pose.get('level')}, "
        f"role in sequence: {pose.get('sequence_role')}. "
        f"Balances: {', '.join(balances) or 'none'}. Aggravates: {', '.join(aggravates) or 'none'}. "
        # Benefits and instructions are joined with ". ", not "; " — chunk_text splits on
        # sentence boundaries, so a semicolon-joined list is one unsplittable 900-char
        # "sentence" that sails past the 256-word-piece cut with its tail unembedded.
        f"Benefits: {'. '.join(b.rstrip('.') for b in pose.get('primary_benefits', []))}. "
        f"Works: {_humanise(pose.get('body_parts', []))}. "
        f"Instructions: {'. '.join(i.rstrip('.') for i in pose.get('instructions', []))}."
    )

    contra = pose.get("contraindications", []) or []
    med_contra = pose.get("medical_conditions_contraindicated", []) or []
    beneficial = pose.get("medical_conditions_beneficial", []) or []
    safety = (
        f"Yoga pose {label} — safety and Ayurvedic basis. "
        f"Avoid with: {_humanise(contra) or 'no listed contraindications'}. "
        f"Not for: {_humanise(med_contra) or 'no listed conditions'}. "
        f"Risk mechanisms: {_humanise(pose.get('risk_tags', [])) or 'none flagged'}. "
        f"Helps with: {_humanise(beneficial) or 'no listed conditions'}. "
        f"Safe in pregnancy: {'yes' if pose.get('pregnancy_safe') else 'no'}. "
        f"Breath: {pose.get('pranayama_sync')}. "
        f"{pose.get('ayurvedic_rationale')}"
    )

    dosha = balances[0] if balances else ""
    out = []
    for body in (practice, safety):
        for chunk in chunk_text(body):
            text = chunk if chunk.startswith("Yoga pose") else f"{label}: {chunk}"
            out.append({"text": text, "dosha": dosha, "source": "yoga_poses"})
    return out


def get_documents_for_collection() -> dict[str, list[dict]]:
    """Build document sets for each ChromaDB collection."""
    docs: dict[str, list[dict]] = {"ayurveda": [], "fitness": [], "nutrition": [], "remedy": [], "panchakarma": []}

    # Dosha profiles → ayurveda
    dosha_data = json.loads((KNOWLEDGE_DIR / "dosha_profiles.json").read_text(encoding="utf-8"))
    for dosha, attrs in dosha_data.get("doshas", {}).items():
        text = f"Dosha: {dosha.capitalize()}. Elements: {attrs['elements']}. Qualities: {attrs['qualities']}. Body: {attrs['bodyType']}. Common imbalances: {attrs['commonImbalances']}. Balancing: {attrs['balancingPrinciples']}. Ideal diet: {attrs['idealDiet']}. Ideal exercise: {attrs['idealExercise']}."
        for chunk in chunk_text(text):
            docs["ayurveda"].append({"text": chunk, "dosha": dosha, "source": "dosha_profiles"})

    # Remedies → remedy
    #
    # This read `symptom`, `dosha_imbalance` and `precautions`, none of which
    # exist in the file — the real keys are `symptom_display`, `dosha_cause` and
    # `contraindications`, and `remedies` is a dict keyed by dosha, not a list of
    # strings. Every one of the 60 entries therefore embedded as the identical
    # sentence "Remedy for None: vata, pitta, kapha. Doshas: . Precautions:
    # None." — the dosha names being the dict KEYS that `join` walked. The whole
    # home-remedy corpus was 60 copies of one meaningless string, which is the
    # same failure as the yoga poses embedding as "Yoga pose: None."
    #
    # One doc per (symptom, dosha) so a retrieved chunk is a remedy someone can
    # actually follow, plus one safety doc per symptom, because contraindications
    # and consult-a-doctor advice are properties of the symptom rather than of a
    # constitution. Both restate the symptom name — the shared embedder truncates
    # at 256 word-pieces and a chunk that only names its subject up top loses it.
    remedy_data = json.loads((KNOWLEDGE_DIR / "home_remedies.json").read_text(encoding="utf-8"))
    for r in remedy_data:
        symptom = r.get("symptom_display") or r.get("id") or "unspecified symptom"
        causes = r.get("dosha_cause") or {}

        for dosha, remedy in (r.get("remedies") or {}).items():
            if not isinstance(remedy, dict):
                continue
            ingredients = ", ".join(
                " ".join(part for part in (ing.get("amount"), ing.get("item")) if part)
                for ing in remedy.get("ingredients", []) if isinstance(ing, dict))
            text = (
                f"Home remedy for {symptom} — {dosha} constitution: {remedy.get('name')}. "
                f"Likely cause in {dosha}: {causes.get(dosha, 'not specified')}. "
                f"Ingredients: {ingredients or 'not specified'}. "
                f"Preparation: {remedy.get('preparation')} "
                f"Dosage: {remedy.get('dosage')}. Duration: {remedy.get('duration')}. "
                f"Expected relief: {remedy.get('expected_relief')}."
            )
            docs["remedy"].append({"text": text, "dosha": dosha, "source": "home_remedies"})

        universal = r.get("universal_remedy")
        if isinstance(universal, dict):
            docs["remedy"].append({
                "text": (f"Home remedy for {symptom}, suitable for any constitution: "
                         f"{universal.get('name')}. Preparation: {universal.get('preparation')} "
                         f"Dosage: {universal.get('dosage')}."),
                "dosha": "", "source": "home_remedies"})

        safety_bits = [
            f"Contraindications: {', '.join(r['contraindications'])}."
            if r.get("contraindications") else "",
            f"Safe in pregnancy: {r.get('pregnancy_safe')}."
            if r.get("pregnancy_safe") is not None else "",
            f"If pregnant, use instead: {r.get('pregnancy_alternative')}."
            if r.get("pregnancy_alternative") else "",
            f"Known drug interactions: {', '.join(r['drug_interactions'])}."
            if r.get("drug_interactions") else "",
            r.get("consult_doctor_if") or "",
        ]
        safety = " ".join(bit for bit in safety_bits if bit)
        if safety:
            docs["remedy"].append({
                "text": (f"Home remedy safety for {symptom} "
                         f"({r.get('symptom_category', 'general')}, "
                         f"tier: {r.get('safety_tier', 'unknown')}). {safety}"),
                "dosha": "", "source": "home_remedies"})

    # Ayurvedic Medicines → remedy
    #
    # `primary_uses` is on 102 of the 157 entries and absent from the other 55 —
    # it is the ONLY key that differs between the two groups, the other 28 being
    # on every entry. So `', '.join(m.get('primary_uses', []))` rendered
    # "Uses: ." for a third of the formulary: a medicine chunk that never says
    # what it treats, which is the one thing it gets retrieved for. `conditions`
    # carries the indication on all 157, in the same vocabulary the engines match
    # on, so it is the field to build from; primary_uses is prose to add when it
    # happens to be there. Same failure class as the home remedies above, and
    # `--check` cannot see it: the chunk is stable and hashes fine, it is just
    # empty of meaning. test_vector_docs asserts the shape instead.
    #
    # Three docs — what it treats, what is in it, who must not take it — split
    # for the reason the poses are: an entry carries 28 fields, one blob runs
    # past the embedder's 256 word-pieces, and everything after the cut is
    # absent from the vector with no error raised. Each names the medicine,
    # because a chunk is retrieved on its own.
    if (KNOWLEDGE_DIR / "ayurvedic_medicines.json").exists():
        med_data = json.loads((KNOWLEDGE_DIR / "ayurvedic_medicines.json").read_text(encoding="utf-8"))
        for m in med_data:
            treats = _humanise(m.get("conditions") or [])
            uses = ", ".join(m.get("primary_uses") or [])
            clinical = [
                f"Ayurvedic medicine {m.get('name')} ({m.get('type')}).",
                f"Treats: {treats}." if treats else "",
                f"Traditionally given for: {uses}." if uses else "",
                f"Classical action: {m['classical_action']}." if m.get("classical_action") else "",
                f"Dosage: {m['dosage']}." if m.get("dosage") else "",
                f"Taken with: {m['anupana']}." if m.get("anupana") else "",
                f"Timing: {_humanise([m['timing']])}." if m.get("timing") else "",
                (f"Typical course: {m['duration_min_weeks']}–{m['duration_max_weeks']} weeks."
                 if m.get("duration_min_weeks") and m.get("duration_max_weeks") else ""),
            ]
            docs["remedy"].append({
                "text": " ".join(bit for bit in clinical if bit),
                "dosha": "", "source": "ayurvedic_medicines",
                "source_credibility": "traditional"})

            # Composition is its own doc rather than a line on the clinical one:
            # Dashamoola Taila's ten roots carry a Latin binomial each and pushed
            # that chunk to 269 word-pieces, past the window, which silently cut
            # the dosage off the end. It also answers a different question — what
            # is in this, and on whose authority — so it retrieves better alone.
            composition = [
                f"Composition of the Ayurvedic medicine {m.get('name')}.",
                f"Ingredients: {', '.join(m['ingredients'])}." if m.get("ingredients") else "",
                f"Rasa (taste): {_humanise(m['rasa'])}." if m.get("rasa") else "",
                f"Virya (potency): {m['virya']}." if m.get("virya") else "",
                f"Vipaka (post-digestive effect): {m['vipaka']}." if m.get("vipaka") else "",
                f"Classical reference: {m['classical_text_reference']}."
                if m.get("classical_text_reference") else "",
                f"Ayurvedic Formulary of India: {m['afi_reference']}."
                if m.get("afi_reference") else "",
            ]
            docs["remedy"].append({
                "text": " ".join(bit for bit in composition if bit),
                "dosha": "", "source": "ayurvedic_medicines",
                "source_credibility": "traditional"})

            safety = [
                f"Do not use in: {_humanise(m['contraindications'])}."
                if m.get("contraindications") else "",
                f"Interacts with: {_humanise(m['drug_interactions'])}."
                if m.get("drug_interactions") else "",
                f"Safe in pregnancy: {'yes' if m.get('pregnancy_safe') else 'no'}."
                if m.get("pregnancy_safe") is not None else "",
                f"Avoid in the season of: {_humanise(m['season_avoid'])}."
                if m.get("season_avoid") else "",
                f"Prescribed for {m['gender_specific']} patients only."
                if m.get("gender_specific") else "",
                f"Paediatric dosage: {m['dosage_pediatric']}."
                if m.get("dosage_pediatric") else "",
                f"Safety tier: {m.get('safety_tier')}." if m.get("safety_tier") else "",
            ]
            docs["remedy"].append({
                "text": (f"Safety of the Ayurvedic medicine {m.get('name')}. "
                         + " ".join(bit for bit in safety if bit)).strip(),
                "dosha": "", "source": "ayurvedic_medicines",
                "source_credibility": "traditional"})

    # Scientific Studies → remedy & ayurveda
    if (KNOWLEDGE_DIR / "scientific_studies.json").exists():
        sci_data = json.loads((KNOWLEDGE_DIR / "scientific_studies.json").read_text(encoding="utf-8"))
        for study in sci_data:
            text = f"Scientific Study on {study.get('herb')}. Title: {study.get('title')}. Abstract: {study.get('abstract')}. Published: {study.get('publication_year')}."
            for chunk in chunk_text(text, max_chars=1000):
                meta = {"text": chunk, "dosha": "", "source": "scientific_literature", "source_credibility": "peer_reviewed", "pmid": study.get('id', '')}
                docs["remedy"].append(meta)
                docs["ayurveda"].append(meta)

    # Yoga poses → ayurveda
    #
    # Reads yoga_poses.json (113 poses, the file the yoga engine itself loads), NOT the
    # 10-entry yoga_plans.json this used to read. Those were two files with similar names
    # and different consumers: the 2026-08-12 KB overhaul rewrote the poses and left the
    # legacy summaries untouched, so RAG was serving the enricher ten stale entries —
    # including pose content that no longer exists — while the engine built plans from a
    # different set. yoga_plans.json is still seeded to Mongo by seed_db.py; it just has
    # no business being the semantic context for yoga narrative.
    yoga_data = json.loads((KNOWLEDGE_DIR / "yoga_poses.json").read_text(encoding="utf-8"))
    for pose in yoga_data:
        docs["ayurveda"].extend(_yoga_pose_docs(pose))

    # Gym routines → fitness
    gym_data = json.loads((KNOWLEDGE_DIR / "gym_routines.json").read_text(encoding="utf-8"))
    gym_list = gym_data if isinstance(gym_data, list) else gym_data.get("routines", [])
    for exercise in gym_list:
        dosha_suit = exercise.get("dosha_suitability", {})
        contraindications = ", ".join(exercise.get("contraindications", []))
        text = (
            f"Exercise: {exercise.get('name')} ({exercise.get('mechanics', '')} movement, "
            f"targets {exercise.get('target_muscle', '')}). "
            f"Dosha suitability: Vata={dosha_suit.get('vata', '')}, "
            f"Pitta={dosha_suit.get('pitta', '')}, Kapha={dosha_suit.get('kapha', '')}. "
            f"Contraindications: {contraindications or 'none'}. "
            f"Instructions: {exercise.get('instructions', '')}."
        )
        docs["fitness"].append({"text": text, "dosha": "", "source": "gym_routines"})

    # Diet plans → nutrition
    diet_data = json.loads((KNOWLEDGE_DIR / "diet_plans.json").read_text(encoding="utf-8"))
    diet_list = diet_data if isinstance(diet_data, list) else diet_data.get("plans", [])
    for plan in diet_list:
        dosha = plan.get("dosha", plan.get("dosha_effect", ""))
        name = plan.get("name", "")
        benefits = ", ".join(plan.get("benefits", []))
        contraindications = ", ".join(plan.get("contraindications", []))
        ingredients = ", ".join(plan.get("ingredients", []))
        text = (
            f"Ayurvedic diet: {name}. Dosha effect: {plan.get('dosha_effect', dosha)}. "
            f"Type: {plan.get('type', '')}. Ingredients: {ingredients}. "
            f"Benefits: {benefits}. Avoid if: {contraindications or 'none'}."
        )
        docs["nutrition"].append({"text": text, "dosha": dosha, "source": "diet_plans"})

    # Ayurvedic Foods → nutrition
    if (KNOWLEDGE_DIR / "ayurvedic_foods.json").exists():
        food_data = json.loads((KNOWLEDGE_DIR / "ayurvedic_foods.json").read_text(encoding="utf-8"))
        for f in food_data:
            text = f"Ayurvedic Food: {f.get('name')} ({f.get('category')}). Rasa (Taste): {', '.join(f.get('rasa', []))}. Virya (Potency): {f.get('virya')}. Vipaka (Post-digestive): {f.get('vipaka')}. Notes: {f.get('notes')}."
            docs["nutrition"].append({"text": text, "dosha": "", "source": "ayurvedic_foods"})

    # Classical Ayurvedic diet texts → nutrition + ayurveda
    if (KNOWLEDGE_DIR / "ayurvedic_diet_classical.json").exists():
        classical_data = json.loads((KNOWLEDGE_DIR / "ayurvedic_diet_classical.json").read_text(encoding="utf-8"))
        for entry in classical_data:
            meta = {
                "text": entry["text"],
                "dosha": entry.get("dosha", ""),
                "source": "ayurvedic_classical_texts",
                "source_credibility": "classical_reference",
                "pmid": "",
            }
            domain = entry.get("domain", "nutrition")
            docs[domain].append(meta)
            # Cross-index foundational principles into ayurveda collection too
            if domain == "nutrition" and entry.get("topic") in ("ahara_principles", "viruddha_ahara", "agni", "ama"):
                docs["ayurveda"].append(meta)

    # Panchakarma → panchakarma
    #
    # One blob per protocol put Raktamokshana at 278 word-pieces and Basti at
    # 258, both past the embedder's window — so the instructions, which sat last,
    # were cut off in exactly the two protocols with the most procedure to
    # describe. Three docs instead: what it is for, how it is done, and who must
    # not have it. Splitting also made room for duration, setting, season and the
    # oils used, which the single blob never carried at all. Each names the
    # protocol, because a chunk is retrieved on its own.
    pk_data = json.loads((KNOWLEDGE_DIR / "panchakarma_plans.json").read_text(encoding="utf-8"))
    for protocol in pk_data:
        name = protocol.get("name")
        dosha = protocol.get("target_dosha", protocol.get("primary_dosha", ""))

        indication = [
            f"Panchakarma protocol {name}.",
            f"Classification: {protocol['classical_classification']}."
            if protocol.get("classical_classification") else "",
            f"Target dosha: {dosha}." if dosha else "",
            f"Benefits: {', '.join(protocol['benefits'])}."
            if protocol.get("benefits") else "",
            f"Best season: {_humanise(protocol['recommended_season'])}."
            if protocol.get("recommended_season") else "",
            f"Session length: {protocol['duration_minutes']} minutes."
            if protocol.get("duration_minutes") else "",
            f"Setting: {_humanise(protocol['setting'])}."
            if protocol.get("setting") else "",
            f"Classical reference: {protocol['classical_text_ref']}."
            if protocol.get("classical_text_ref") else "",
        ]
        docs["panchakarma"].append({
            "text": " ".join(bit for bit in indication if bit),
            "dosha": dosha, "source": "panchakarma_plans"})

        if protocol.get("instructions"):
            oils = (f" Oils and herbs used: {', '.join(protocol['herbs_oils_used'])}."
                    if protocol.get("herbs_oils_used") else "")
            docs["panchakarma"].append({
                "text": (f"Panchakarma procedure for {name}. "
                         f"{protocol['instructions']}.{oils}"),
                "dosha": dosha, "source": "panchakarma_plans"})

        if protocol.get("contraindications"):
            docs["panchakarma"].append({
                "text": (f"Panchakarma safety for {name}. Do not perform in: "
                         f"{_humanise(protocol['contraindications'])}."),
                "dosha": dosha, "source": "panchakarma_plans"})

    # Ritucharya → ayurveda
    ritual_data = json.loads((KNOWLEDGE_DIR / "ritucharya_seasonal.json").read_text(encoding="utf-8"))
    for season in ritual_data.get("seasons", []):
        text = f"Season {season['name']}: Dominant dosha {season['dominantDosha']}. {season['description']}. Diet: favor {season['dietGuidelines']['favor']}, avoid {season['dietGuidelines']['avoid']}. Lifestyle: {season['lifestyleGuidelines']}."
        docs["ayurveda"].append({"text": text, "dosha": season["dominantDosha"], "source": "ritucharya"})

    return docs


def build_vectors(check_only: bool = False):
    print("🔍 Checking ChromaDB for drift..." if check_only
          else "🔄 Building ChromaDB vector store...")

    # Seed the same store the app reads from: a remote Chroma server when
    # CHROMA_HOST is set (Docker/staging/prod), else the embedded persistent dir.
    chroma_host = os.environ.get("CHROMA_HOST")
    if chroma_host:
        chroma_port = int(os.environ.get("CHROMA_PORT", "8000"))
        print(f"   → Seeding remote ChromaDB at {chroma_host}:{chroma_port}")
        client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
            settings=Settings(anonymized_telemetry=False),
        )
    else:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        print(f"   → Seeding embedded ChromaDB at {CHROMA_DIR}")
        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    embedder = get_embedder()

    # Prove the embedder works BEFORE the first delete_collection.
    #
    # Learned on production 2026-08-13: the loop deletes a collection, recreates it, then
    # calls add() — and add() is where the ONNX model is first pulled. On a container that
    # had never embedded anything, the download raced its own sha256 check and threw, which
    # left ayurveda_knowledge deleted, recreated and EMPTY. The seeder had taken production
    # RAG down before doing a single useful thing. Warming here turns that class of failure
    # into a clean exit with the corpus untouched.
    try:
        embedder(["warm the model before anything is deleted"])
    except Exception as exc:
        raise SystemExit(
            f"❌ Embedder unavailable, refusing to touch the corpus: {exc}\n"
            "   The model downloads on first use — check egress and disk, then re-run."
        ) from exc

    collection_map = {
        "ayurveda": "ayurveda_knowledge",
        "fitness": "fitness_knowledge",
        "nutrition": "nutrition_knowledge",
        "remedy": "remedy_knowledge",
        "panchakarma": "panchakarma_knowledge",
    }

    doc_sets = get_documents_for_collection()

    # Refuse to seed a corpus that would be truncated on the way in. Fails in
    # --check too: a chunk past the window is wrong in the store as much as it is
    # wrong on the way to it, and it reports identical to a healthy one.
    overflowing = _overflowing_chunks(embedder, doc_sets)
    if overflowing:
        raise SystemExit(
            f"❌ {len(overflowing)} chunk(s) run past the embedder's {EMBEDDER_WINDOW} "
            "word-pieces and everything after the cut would be dropped silently:\n  "
            + "\n  ".join(overflowing[:10])
            + "\n   Split the document instead of trusting the truncation.")

    drifted: list[str] = []

    for domain, coll_name in collection_map.items():
        docs = doc_sets.get(domain, [])
        if not docs:
            print(f"  ⚠️ No docs for {domain}")
            continue

        col = client.get_or_create_collection(
            name=coll_name, embedding_function=embedder,
            metadata={"hnsw:space": "cosine"})

        wanted = _document_index(domain, docs)
        existing = set(col.get(include=[])["ids"])

        to_write = [cid for cid in wanted if cid not in existing]
        to_drop = sorted(existing - set(wanted))

        if check_only:
            if to_write or to_drop:
                drifted.append(
                    f"{coll_name}: {len(to_write)} missing/changed, {len(to_drop)} stale")
                print(f"  ❌ {coll_name}: {len(to_write)} chunks missing or changed, "
                      f"{len(to_drop)} stale — reseed needed")
            else:
                print(f"  ✅ {coll_name}: {len(wanted)} chunks, in sync")
            continue

        # Write BEFORE dropping, so the collection is never smaller than it
        # started. A crash between the two leaves duplicates, which retrieval
        # tolerates; the reverse order leaves a hole, which it does not.
        if to_write:
            batch = [wanted[cid] for cid in to_write]
            col.upsert(
                ids=to_write,
                documents=[d["text"] for d in batch],
                metadatas=[_metadata(d) for d in batch],
            )
        if to_drop:
            col.delete(ids=to_drop)

        unchanged = len(wanted) - len(to_write)
        print(f"  ✅ {coll_name}: {len(wanted)} chunks "
              f"({len(to_write)} written, {len(to_drop)} removed, {unchanged} unchanged)")

    if check_only:
        if drifted:
            raise SystemExit(
                "\n❌ The embedded corpus is behind the knowledge base:\n  "
                + "\n  ".join(drifted)
                + "\n   Run `python scripts/build_vectors.py` to bring it in sync — it now "
                  "writes only what changed and never empties a collection.")
        print("\n✅ Every collection matches the knowledge base.")
        return

    print("\n🎉 ChromaDB vector store built successfully!")


if __name__ == "__main__":
    # `--check` reports drift and exits non-zero without writing anything, so
    # "nothing detects this" stops being true. Editing a knowledge-base file the
    # seeder ingests used to leave the corpus stale in total silence: no test
    # failed and no error logged, because plans are built by the deterministic
    # engines and only RAG context went quietly out of date.
    build_vectors(check_only="--check" in sys.argv)
