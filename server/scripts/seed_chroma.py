from core.logger import logger
import sys
import os

# Add the server directory to the sys path so we can import from database/config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.chromadb_client import init_chromadb, get_collection

DOCUMENTS = {
    "ayurveda": [
        {
            "id": "ayur_1",
            "text": "During Vata season (Autumn/Early Winter), the environment is cold, dry, and windy. To balance Vata, favor warm, heavy, and oily foods. Sweet, sour, and salty tastes are recommended. Root vegetables, warm milk with nutmeg, and ghee are excellent.",
            "meta": {"dosha": "vata", "season": "autumn"}
        },
        {
            "id": "ayur_2",
            "text": "During Pitta season (Summer), heat accumulates. To balance Pitta, favor cooling, heavy, and dry foods. Sweet, bitter, and astringent tastes are best. Coconut water, cucumber, and mint are highly recommended.",
            "meta": {"dosha": "pitta", "season": "summer"}
        },
        {
            "id": "ayur_3",
            "text": "During Kapha season (Late Winter/Spring), the qualities are heavy, cold, and damp. To balance Kapha, favor warm, light, and dry foods. Pungent, bitter, and astringent tastes are beneficial. Ginger, black pepper, and light grains like quinoa are ideal.",
            "meta": {"dosha": "kapha", "season": "spring"}
        }
    ],
    "fitness": [
        {
            "id": "fit_1",
            "text": "For Vata dosha, intense cardiovascular exercise can deplete energy and increase anxiety. Prefer grounding activities like weight lifting with longer rest periods, cycling at a moderate pace, or slow-flow yoga. Avoid high-impact jumping.",
            "meta": {"dosha": "vata"}
        },
        {
            "id": "fit_2",
            "text": "For Pitta dosha, avoid exercising during the hottest part of the day to prevent overheating. Swimming, winter sports, and moderate weightlifting are excellent. Avoid overly competitive sports which may aggravate Pitta irritability.",
            "meta": {"dosha": "pitta"}
        },
        {
            "id": "fit_3",
            "text": "For Kapha dosha, vigorous, heat-producing exercise is highly beneficial to combat lethargy. HIIT, running, kickboxing, and fast-paced vinyasa flow are highly recommended. Kaphas have high endurance and benefit from sustained effort.",
            "meta": {"dosha": "kapha"}
        }
    ],
    "remedy": [
        {
            "id": "rem_1",
            "text": "For indigestion and bloating (Vata imbalance), chewing a small piece of fresh ginger with a pinch of rock salt 15 minutes before meals stimulates agni (digestive fire). Fennel and cumin tea post-meals helps reduce gas.",
            "meta": {"symptom": "indigestion", "dosha": "vata"}
        },
        {
            "id": "rem_2",
            "text": "For acid reflux or heartburn (Pitta imbalance), drink half a cup of cool milk or aloe vera juice. Avoid spicy, sour, and fermented foods. Chewing on fennel seeds also cools the digestive tract.",
            "meta": {"symptom": "heartburn", "dosha": "pitta"}
        },
        {
            "id": "rem_3",
            "text": "For chest congestion or heavy cough (Kapha imbalance), boil water with crushed ginger, black pepper, and tulsi (holy basil) leaves. Drink this herbal decoction warm with a teaspoon of raw honey. Avoid dairy products.",
            "meta": {"symptom": "cough", "dosha": "kapha"}
        }
    ]
}

def main():
    logger.info("Initializing ChromaDB...")
    init_chromadb()
    
    for domain, docs in DOCUMENTS.items():
        logger.info(f"Populating {domain} collection...")
        collection = get_collection(domain)
        
        # Extract lists for chromadb
        ids = [doc["id"] for doc in docs]
        documents = [doc["text"] for doc in docs]
        metadatas = [doc["meta"] for doc in docs]
        
        # Upsert documents
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"  -> Inserted {len(docs)} documents into {domain}")

    logger.info("✅ ChromaDB seeding complete!")

if __name__ == "__main__":
    main()
