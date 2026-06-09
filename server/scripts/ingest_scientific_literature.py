import os
import sys
import json
import requests
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.logger import logger

KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = KNOWLEDGE_DIR / "scientific_studies.json"

HERBS_TO_SEARCH = [
    "Ashwagandha",
    "Triphala",
    "Brahmi",
    "Shatavari",
    "Turmeric",
    "Holy Basil",
    "Guduchi",
    "Licorice Root",
    "Gotu Kola",
    "Boswellia"
]

def reconstruct_abstract(inverted_index):
    """Reconstructs the abstract text from OpenAlex's inverted index format."""
    if not inverted_index:
        return ""
    try:
        max_idx = max([idx for indices in inverted_index.values() for idx in indices])
        words = [""] * (max_idx + 1)
        for word, indices in inverted_index.items():
            for idx in indices:
                words[idx] = word
        return " ".join(words).replace("  ", " ").strip()
    except Exception as e:
        logger.error(f"Error reconstructing abstract: {e}")
        return ""

def fetch_openalex_studies(herb: str, limit: int = 5):
    """Fetch clinical trials and reviews for a specific herb from OpenAlex."""
    logger.info(f"🔍 Searching OpenAlex for: {herb}...")
    
    # Query: Herb AND (clinical OR trial OR review)
    # We sort by cited_by_count to get the most authoritative papers.
    url = "https://api.openalex.org/works"
    params = {
        "search": f'"{herb}" AND (clinical OR trial OR "systematic review")',
        "per-page": limit,
        "sort": "cited_by_count:desc",
        "filter": "has_abstract:true"
    }
    
    headers = {"User-Agent": "AyuraAI_Data_Ingestion_Script/1.0"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for work in data.get("results", []):
            abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
            if not abstract or len(abstract) < 100:
                continue
                
            results.append({
                "id": work.get("id"),
                "doi": work.get("doi"),
                "title": work.get("title"),
                "abstract": abstract,
                "publication_year": work.get("publication_year"),
                "cited_by_count": work.get("cited_by_count"),
                "herb": herb
            })
            
        return results
    except Exception as e:
        logger.error(f"Failed to fetch data for {herb}: {e}")
        return []

def main():
    logger.info("🚀 Starting Scientific Literature Ingestion Pipeline...")
    all_studies = []
    
    for herb in HERBS_TO_SEARCH:
        studies = fetch_openalex_studies(herb, limit=5)
        all_studies.extend(studies)
        # Polite rate limiting for OpenAlex (max 10 req/sec allowed, we'll do 1 sec)
        time.sleep(1)
        
    logger.info(f"✅ Successfully fetched {len(all_studies)} high-quality peer-reviewed studies.")
    
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_studies, f, indent=2, ensure_ascii=False)
        
    logger.info(f"💾 Saved scientific knowledge base to {OUT_FILE}")

if __name__ == "__main__":
    main()
