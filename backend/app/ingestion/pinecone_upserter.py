from pinecone import Pinecone
from app.config import settings

pc = Pinecone(
    api_key=settings.pinecone_api_key
)

index = pc.Index(
    settings.pinecone_index_name
)


def upsert_vector(
    vector_id: str,
    vector: list,
    metadata: dict
):
    index.upsert(
        vectors=[
            {
                "id": vector_id,
                "values": vector,
                "metadata": metadata
            }
        ]
    )


def search_vector(
    vector: list,
    top_k: int = 5
):
    return index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True
    )