"""Pinecone retriever — ANN vector search against the Pinecone index."""
from __future__ import annotations

from app.ingestion.gme_embedder import embed_text
from app.ingestion.pinecone_upserter import search_vector


class PineconeRetriever:
    def retrieve(self, query_text: str, top_k: int = 5) -> list[dict]:
        """
        Embed query text with Gemini, then search Pinecone.
        Returns list of metadata dicts with score, file_id, page, text.
        """
        vector = embed_text(query_text)
        return search_vector(vector, top_k=top_k)