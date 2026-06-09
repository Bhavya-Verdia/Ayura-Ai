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
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        return OpenAIEmbeddingFunction(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_base=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_type="azure",
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            model_name=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
        )
    except Exception:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        print("  ℹ️  Using local SentenceTransformer (no Azure key found)")
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
    for routine in gym_data.get("routines", []):
        dosha = routine.get("dosha", "")
        text = f"Gym routine for {dosha} dosha, {routine.get('fitnessLevel')} level, {routine.get('bmiCategory')} BMI. Ayurvedic tips: {routine.get('ayurvedicNotes')}. Safety: {routine.get('safetyNotes')}."
        docs["fitness"].append({"text": text, "dosha": dosha, "source": "gym_routines"})

    # Diet plans → nutrition
    diet_data = json.loads((KNOWLEDGE_DIR / "diet_plans.json").read_text(encoding="utf-8"))
    for plan in diet_data.get("plans", []):
        dosha = plan.get("dosha", "")
        text = f"Diet plan for {dosha} dosha, goal {plan.get('goal')}, BMI {plan.get('bmiCategory')}. Favor: {plan.get('foodsToFavor', [])}. Avoid: {plan.get('foodsToAvoid', [])}. Spices: {plan.get('ayurvedicSpices', [])}. Guidelines: {plan.get('mealTimingGuidelines', [])}."
        docs["nutrition"].append({"text": text, "dosha": dosha, "source": "diet_plans"})

    # Ayurvedic Foods → nutrition
    if (KNOWLEDGE_DIR / "ayurvedic_foods.json").exists():
        food_data = json.loads((KNOWLEDGE_DIR / "ayurvedic_foods.json").read_text(encoding="utf-8"))
        for f in food_data:
            text = f"Ayurvedic Food: {f.get('name')} ({f.get('category')}). Rasa (Taste): {', '.join(f.get('rasa', []))}. Virya (Potency): {f.get('virya')}. Vipaka (Post-digestive): {f.get('vipaka')}. Notes: {f.get('notes')}."
            docs["nutrition"].append({"text": text, "dosha": "", "source": "ayurvedic_foods"})

    # Panchakarma → panchakarma
    pk_data = json.loads((KNOWLEDGE_DIR / "panchakarma_plans.json").read_text(encoding="utf-8"))
    for protocol in pk_data:
        text = f"Panchakarma Protocol: {protocol.get('name')}. Dosha: {protocol.get('primary_dosha')}. Description: {protocol.get('description')}. Steps: {' '.join(protocol.get('steps', []))}. Contraindications: {', '.join(protocol.get('contraindications', []))}."
        docs["panchakarma"].append({"text": text, "dosha": protocol.get("primary_dosha", ""), "source": "panchakarma_plans"})

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
