from core.logger import logger
"""
Ayura AI - ChromaDB Vector Store Client
Used for RAG pipeline embeddings and semantic search.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings

_chroma_client = None
_available: bool = False

# Collection names for different knowledge domains
COLLECTIONS = {
    "ayurveda": "ayurveda_knowledge",
    "fitness": "fitness_knowledge",
    "nutrition": "nutrition_knowledge",
    "remedy": "remedy_knowledge",
    "panchakarma": "panchakarma_knowledge",
}


def init_chromadb():
    """Initialize ChromaDB persistent client and create collections."""
    global _chroma_client, _available
    try:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                chroma_product_telemetry_impl="database.chroma_telemetry.NullTelemetry",
                chroma_telemetry_impl="database.chroma_telemetry.NullTelemetry",
            ),
        )

        # Ensure all collections exist
        for name in COLLECTIONS.values():
            _chroma_client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )

        _available = True
        logger.info("  ChromaDB initialized with 5 collections")
    except Exception as exc:
        _available = False
        logger.warning(f" ChromaDB initialization failed ({exc}). RAG pipeline will return empty results.")


def is_chromadb_available() -> bool:
    """Check if ChromaDB is initialized and ready."""
    return _available


def get_chroma_client():
    """Get the ChromaDB client instance."""
    if _chroma_client is None:
        raise RuntimeError("ChromaDB not initialized. Call init_chromadb() first.")
    return _chroma_client


def get_collection(domain: str) -> chromadb.Collection:
    """Get a specific ChromaDB collection by domain name."""
    client = get_chroma_client()
    collection_name = COLLECTIONS.get(domain)
    if not collection_name:
        raise ValueError(f"Unknown collection domain: {domain}. Use one of: {list(COLLECTIONS.keys())}")
    return client.get_collection(collection_name)

