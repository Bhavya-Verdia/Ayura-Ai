"""
Ayura AI - Vector Embedding Builder
Embeds knowledge base documents into ChromaDB for RAG retrieval.
Run: python scripts/build_vectors.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

import chromadb
from chromadb.config import Settings

KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "knowledge"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chromadb"


def get_embedder():
    """Try Azure OpenAI embeddings, fall back to sentence-transformers."""
    from dotenv import load_dotenv
    import os
    load_dotenv()

    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    embed_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    if azure_key and azure_endpoint:
        try:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            fn = OpenAIEmbeddingFunction(
                api_key=azure_key,
                api_base=azure_endpoint,
                api_type="azure",
                api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                model_name=embed_deployment,
            )
            # Probe the deployment before committing to it
            fn(["test"])
            print(f"  ✅ Using Azure OpenAI embeddings ({embed_deployment})")
            return fn
        except Exception as e:
            print(f"  ⚠️  Azure embedding deployment not available ({e}), falling back to local model")

    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    print("  ℹ️  Using local SentenceTransformer (all-MiniLM-L6-v2)")
    return SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


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
    remedy_data = json.loads((KNOWLEDGE_DIR / "home_remedies.json").read_text(encoding="utf-8"))
    for r in remedy_data:
        text = f"Remedy for {r.get('symptom')}: {', '.join(r.get('remedies', []))}. Doshas: {', '.join(r.get('dosha_imbalance', []))}. Precautions: {r.get('precautions')}."
        docs["remedy"].append({"text": text, "dosha": r.get('dosha_imbalance', [''])[0] if r.get('dosha_imbalance') else "", "source": "home_remedies"})

    # Ayurvedic Medicines → remedy
    if (KNOWLEDGE_DIR / "ayurvedic_medicines.json").exists():
        med_data = json.loads((KNOWLEDGE_DIR / "ayurvedic_medicines.json").read_text(encoding="utf-8"))
        for m in med_data:
            text = f"Ayurvedic Medicine: {m.get('name')} ({m.get('type')}). Uses: {', '.join(m.get('primary_uses', []))}. Dosage: {m.get('dosage')}. Safety tier: {m.get('safety_tier')}."
            docs["remedy"].append({"text": text, "dosha": "", "source": "ayurvedic_medicines", "source_credibility": "traditional"})

    # Scientific Studies → remedy & ayurveda
    if (KNOWLEDGE_DIR / "scientific_studies.json").exists():
        sci_data = json.loads((KNOWLEDGE_DIR / "scientific_studies.json").read_text(encoding="utf-8"))
        for study in sci_data:
            text = f"Scientific Study on {study.get('herb')}. Title: {study.get('title')}. Abstract: {study.get('abstract')}. Published: {study.get('publication_year')}."
            for chunk in chunk_text(text, max_chars=1000):
                meta = {"text": chunk, "dosha": "", "source": "scientific_literature", "source_credibility": "peer_reviewed", "pmid": study.get('id', '')}
                docs["remedy"].append(meta)
                docs["ayurveda"].append(meta)

    # Yoga plans → ayurveda
    yoga_data = json.loads((KNOWLEDGE_DIR / "yoga_plans.json").read_text(encoding="utf-8"))
    for pose in yoga_data:
        text = f"Yoga pose: {pose.get('name')}. Benefits: {', '.join(pose.get('benefits', []))}. Dosha balance: {', '.join(pose.get('dosha_balance', []))}. Contraindications: {', '.join(pose.get('contraindications', []))}. Instructions: {pose.get('instructions')}."
        docs["ayurveda"].append({"text": text, "dosha": pose.get('dosha_balance', [''])[0] if pose.get('dosha_balance') else "", "source": "yoga_plans"})

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
    pk_data = json.loads((KNOWLEDGE_DIR / "panchakarma_plans.json").read_text(encoding="utf-8"))
    for protocol in pk_data:
        dosha = protocol.get("target_dosha", protocol.get("primary_dosha", ""))
        classification = protocol.get("classical_classification", "")
        text_ref = protocol.get("classical_text_ref", "")
        benefits = ", ".join(protocol.get("benefits", []))
        contraindications = ", ".join(protocol.get("contraindications", []))
        text = (
            f"Panchakarma Protocol: {protocol.get('name')}. "
            f"Classification: {classification}. "
            f"Target Dosha: {dosha}. "
            f"Classical reference: {text_ref}. "
            f"Benefits: {benefits}. "
            f"Contraindications: {contraindications}. "
            f"Instructions: {protocol.get('instructions', '')}."
        )
        docs["panchakarma"].append({"text": text, "dosha": dosha, "source": "panchakarma_plans"})

    # Ritucharya → ayurveda
    ritual_data = json.loads((KNOWLEDGE_DIR / "ritucharya_seasonal.json").read_text(encoding="utf-8"))
    for season in ritual_data.get("seasons", []):
        text = f"Season {season['name']}: Dominant dosha {season['dominantDosha']}. {season['description']}. Diet: favor {season['dietGuidelines']['favor']}, avoid {season['dietGuidelines']['avoid']}. Lifestyle: {season['lifestyleGuidelines']}."
        docs["ayurveda"].append({"text": text, "dosha": season["dominantDosha"], "source": "ritucharya"})

    return docs


def build_vectors():
    print("🔄 Building ChromaDB vector store...")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    embedder = get_embedder()

    collection_map = {
        "ayurveda": "ayurveda_knowledge",
        "fitness": "fitness_knowledge",
        "nutrition": "nutrition_knowledge",
        "remedy": "remedy_knowledge",
        "panchakarma": "panchakarma_knowledge",
    }

    doc_sets = get_documents_for_collection()

    for domain, coll_name in collection_map.items():
        docs = doc_sets.get(domain, [])
        if not docs:
            print(f"  ⚠️ No docs for {domain}")
            continue

        col = client.get_or_create_collection(name=coll_name, embedding_function=embedder, metadata={"hnsw:space": "cosine"})
        col.delete(where={"source": {"$ne": ""}})  # Clear existing

        texts = [d["text"] for d in docs]
        metadatas = [
            {
                "dosha": d.get("dosha", ""), 
                "source": d.get("source", ""),
                "source_credibility": d.get("source_credibility", "general"),
                "pmid": d.get("pmid", "")
            } 
            for d in docs
        ]
        ids = [f"{domain}_{i}" for i in range(len(docs))]

        col.add(documents=texts, metadatas=metadatas, ids=ids)
        print(f"  ✅ {coll_name}: {len(docs)} chunks embedded")

    print("\n🎉 ChromaDB vector store built successfully!")


if __name__ == "__main__":
    build_vectors()
