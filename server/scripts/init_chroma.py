import os
import sys

# Ensure we can import from server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.chromadb_client import init_chromadb, get_collection, is_chromadb_available
from core.logger import logger

MOCK_DATA = {
    "ayurveda": [
        {"id": "ay_1", "text": "Vata dosha is governed by air and space. When out of balance, it causes anxiety, dry skin, and digestive issues.", "meta": {"dosha": "vata", "source": "Mock_Text"}},
        {"id": "ay_2", "text": "Pitta dosha is governed by fire and water. When out of balance, it causes inflammation, acidity, and anger.", "meta": {"dosha": "pitta", "source": "Mock_Text"}},
        {"id": "ay_3", "text": "Kapha dosha is governed by earth and water. When out of balance, it causes lethargy, weight gain, and congestion.", "meta": {"dosha": "kapha", "source": "Mock_Text"}},
    ],
    "remedy": [
        {"id": "rem_1", "text": "For a headache caused by Vata imbalance, try warm sesame oil massage on the scalp or ginger tea.", "meta": {"symptom": "headache", "dosha": "vata", "source": "Mock_Text"}},
        {"id": "rem_2", "text": "For acidity (Pitta), drink aloe vera juice or chew fennel seeds after meals.", "meta": {"symptom": "acidity", "dosha": "pitta", "source": "Mock_Text"}},
        {"id": "rem_3", "text": "For cold and congestion (Kapha), ginger, black pepper, and honey are highly effective.", "meta": {"symptom": "congestion", "dosha": "kapha", "source": "Mock_Text"}},
    ],
    "nutrition": [
        {"id": "nut_1", "text": "Vata pacifying diet: Warm, heavy, and oily foods. Sweet, sour, and salty tastes.", "meta": {"dosha": "vata", "source": "Mock_Text"}},
        {"id": "nut_2", "text": "Pitta pacifying diet: Cooling, heavy, and dry foods. Sweet, bitter, and astringent tastes.", "meta": {"dosha": "pitta", "source": "Mock_Text"}},
        {"id": "nut_3", "text": "Kapha pacifying diet: Light, dry, and warm foods. Pungent, bitter, and astringent tastes.", "meta": {"dosha": "kapha", "source": "Mock_Text"}},
    ]
}

def seed_chromadb():
    os.environ['CHROMA_PERSIST_DIRECTORY'] = os.environ.get('CHROMA_PERSIST_DIRECTORY', '/app/data/chromadb')
    init_chromadb()
    
    if not is_chromadb_available():
        logger.error("Failed to initialize ChromaDB. Cannot seed data.")
        return

    logger.info("Checking ChromaDB collections for data...")
    
    for domain, documents in MOCK_DATA.items():
        try:
            col = get_collection(domain)
            count = col.count()
            if count == 0:
                logger.info(f"Seeding '{domain}' collection with mock data...")
                col.add(
                    ids=[d["id"] for d in documents],
                    documents=[d["text"] for d in documents],
                    metadatas=[d["meta"] for d in documents]
                )
                logger.info(f"Added {len(documents)} records to '{domain}'.")
            else:
                logger.info(f"Collection '{domain}' already has {count} records. Skipping.")
        except Exception as e:
            logger.error(f"Failed to seed {domain}: {e}")

if __name__ == "__main__":
    seed_chromadb()
