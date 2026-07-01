"""
Ayura AI - RAG Pipeline
Tier 2: Embed → Search → Retrieve → Augment
Uses ChromaDB for vector search over Ayurvedic knowledge base.
"""

import asyncio
import time

from core.logger import logger
from database.chromadb_client import get_collection, COLLECTIONS

# --- Query result cache (in-process, TTL + size bounded) ---------------------
# Embedding + vector search is pure CPU and identical for identical inputs, so we
# memoize by the full query signature. In-process (not Redis) keeps it dependency
# free and correct per worker; the short TTL bounds staleness if the KB is rebuilt.
_QUERY_CACHE: dict[tuple, tuple[float, list[dict]]] = {}
_CACHE_TTL = 300      # seconds
_CACHE_MAX = 256      # entries


def _cache_get(key: tuple) -> list[dict] | None:
    hit = _QUERY_CACHE.get(key)
    if not hit:
        return None
    ts, data = hit
    if time.time() - ts > _CACHE_TTL:
        _QUERY_CACHE.pop(key, None)
        return None
    return data


def _cache_put(key: tuple, data: list[dict]) -> None:
    if len(_QUERY_CACHE) >= _CACHE_MAX:
        # evict the oldest entry (approximate LRU by insertion timestamp)
        oldest = min(_QUERY_CACHE, key=lambda k: _QUERY_CACHE[k][0])
        _QUERY_CACHE.pop(oldest, None)
    _QUERY_CACHE[key] = (time.time(), data)


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for grounded health knowledge."""

    async def query(
        self,
        query_text: str,
        domain: str,
        n_results: int = 8,
        dosha_filter: str | None = None,
        symptom_filter: str | None = None,
    ) -> list[dict]:
        """
        Search the vector store for relevant knowledge chunks.

        Args:
            query_text: Natural language query
            domain: Knowledge domain (ayurveda, fitness, nutrition, remedy, panchakarma)
            n_results: Number of results to return
            dosha_filter: Filter by dosha type
            symptom_filter: Filter by symptom

        Returns:
            List of relevant document chunks with metadata
        """
        # Serve identical queries from the short-lived cache (embedding + search
        # is deterministic for the same inputs).
        cache_key = (domain, query_text, n_results, dosha_filter, symptom_filter)
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        collection = get_collection(domain)

        # Build metadata filter
        where_filter = {}
        if dosha_filter:
            where_filter["dosha"] = dosha_filter
        if symptom_filter:
            where_filter["symptom"] = symptom_filter

        # Query ChromaDB
        query_params = {
            "query_texts": [query_text],
            "n_results": n_results,
        }
        if where_filter:
            query_params["where"] = where_filter

        # Run the synchronous ChromaDB query in a thread pool to avoid blocking the
        # event loop. RAG is ENRICHMENT, never essential — if the vector store errors
        # (e.g. an embedding-dimension mismatch, or the server being down), degrade to
        # no context rather than breaking the caller (chat, plans, …).
        try:
            results = await asyncio.to_thread(collection.query, **query_params)
        except Exception as exc:
            logger.warning("RAG query failed for domain '%s' — returning no context: %s", domain, exc)
            return []

        # Format results with relevance threshold
        MAX_DISTANCE = 1.5  # cosine distance > 1.5 = likely irrelevant
        documents = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                if distance > MAX_DISTANCE:
                    continue  # skip low-relevance chunks
                documents.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": distance,
                    "id": results["ids"][0][i] if results["ids"] else "",
                })

        # If dosha filter returned nothing, retry without filter
        if not documents and where_filter:
            fallback_params = {"query_texts": [query_text], "n_results": n_results}
            try:
                fallback_results = await asyncio.to_thread(collection.query, **fallback_params)
            except Exception as exc:
                logger.warning("RAG fallback query failed for domain '%s': %s", domain, exc)
                fallback_results = None
            if fallback_results and fallback_results["documents"]:
                for i, doc in enumerate(fallback_results["documents"][0]):
                    distance = fallback_results["distances"][0][i] if fallback_results["distances"] else 0
                    if distance > MAX_DISTANCE:
                        continue
                    documents.append({
                        "content": doc,
                        "metadata": fallback_results["metadatas"][0][i] if fallback_results["metadatas"] else {},
                        "distance": distance,
                        "id": fallback_results["ids"][0][i] if fallback_results["ids"] else "",
                    })

        _cache_put(cache_key, documents)
        return documents

    async def multi_domain_query(
        self,
        query_text: str,
        domains: list[str],
        n_per_domain: int = 5,
        dosha_filter: str | None = None,
    ) -> dict[str, list[dict]]:
        """
        Search across multiple knowledge domains simultaneously using asyncio.gather.
        """
        valid_domains = [d for d in domains if d in COLLECTIONS]
        tasks = [
            self.query(query_text, domain, n_per_domain, dosha_filter)
            for domain in valid_domains
        ]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            domain: result if not isinstance(result, Exception) else []
            for domain, result in zip(valid_domains, results_list)
        }

    def format_context(self, documents: list[dict], max_chars: int = 6000) -> str:
        """Format retrieved documents into a context string for the LLM prompt."""
        context_parts = []
        total_chars = 0

        for doc in documents:
            content = doc["content"]
            if total_chars + len(content) > max_chars:
                break

            meta = doc.get("metadata", {})
            source = meta.get("source", "knowledge_base")
            credibility = meta.get("source_credibility", "")
            pmid = meta.get("pmid", "")

            header = f"[Source: {source}]"
            if credibility == "peer_reviewed":
                header += " [CREDIBILITY: PEER-REVIEWED SCIENTIFIC STUDY]"
                if pmid:
                    header += f" [PMID: {pmid}]"

            context_parts.append(f"{header}\n{content}")
            total_chars += len(content)

        return "\n\n---\n\n".join(context_parts)


# Singleton instance
rag_pipeline = RAGPipeline()
