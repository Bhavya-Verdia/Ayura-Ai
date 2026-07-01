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
    """Initialize ChromaDB client and create collections."""
    global _chroma_client, _available
    try:
        if settings.CHROMA_HOST:
            logger.info(f"Connecting to ChromaDB Server at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
            _chroma_client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    chroma_product_telemetry_impl="database.chroma_telemetry.NullTelemetry",
                    chroma_telemetry_impl="database.chroma_telemetry.NullTelemetry",
                ),
            )
        else:
            logger.info(f"Connecting to embedded ChromaDB at {settings.CHROMA_PERSIST_DIRECTORY}")
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


def warm_embeddings() -> None:
    """Force ChromaDB's default embedding model (MiniLM ONNX) to load now.

    The model is loaded lazily on the first `collection.query(query_texts=...)`,
    which otherwise adds several seconds to the first user's chat request. Running
    one throwaway query at startup pays that cost up front. Synchronous and safe to
    call in a background thread; failures are non-fatal (RAG still degrades gracefully).
    """
    if not _available:
        return
    try:
        get_collection("ayurveda").query(query_texts=["warmup"], n_results=1)
        logger.info("  ChromaDB embedding model warmed up")
    except Exception as exc:
        logger.warning(f"ChromaDB embedding warm-up skipped ({exc}).")

