from pinecone import Pinecone, ServerlessSpec
from app.config import settings

# Gemini embedding-001 outputs 3072-dim vectors
DIMENSION = 3072


def _get_index():
    """Lazy init — only connects when first called, not at import time."""
    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing = [i.name for i in pc.list_indexes()]
    if settings.pinecone_index_name not in existing:
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return pc.Index(settings.pinecone_index_name)


def upsert_vector(vector_id: str, vector: list, metadata: dict) -> None:
    index = _get_index()
    index.upsert(
        vectors=[
            {
                "id": vector_id,
                "values": vector,
                "metadata": metadata,
            }
        ]
    )


def search_vector(vector: list, top_k: int = 5) -> list[dict]:
    """Returns normalised list of {id, score, **metadata} dicts."""
    index = _get_index()
    result = index.query(vector=vector, top_k=top_k, include_metadata=True)
    return [
        {"id": m.id, "score": m.score, **(m.metadata or {})}
        for m in result.matches
    ]