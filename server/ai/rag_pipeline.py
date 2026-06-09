"""
Ayura AI - RAG Pipeline
Tier 2: Embed → Search → Retrieve → Augment
Uses ChromaDB for vector search over Ayurvedic knowledge base.
"""

import asyncio

from database.chromadb_client import get_collection, COLLECTIONS


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

        # Run the synchronous ChromaDB query in a thread pool to avoid blocking the event loop
        results = await asyncio.to_thread(collection.query, **query_params)

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
            fallback_results = await asyncio.to_thread(collection.query, **fallback_params)
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
