from app.ingestion.parser import parse_file
from app.ingestion.gemini_embedder import embed_text
from app.ingestion.pinecone_upserter import upsert_vector


def ingest_document(file_path: str):

    pages = parse_file(file_path)

    stored_count = 0

    for page in pages:

        text = page.text.strip()

        print(
            f"Page {page.page_number}: "
            f"{len(text)} characters"
        )

        if not text:
            print(
                f"Skipping page {page.page_number} (empty)"
            )
            continue

        vector = embed_text(text)

        upsert_vector(
            vector_id=f"{page.source_file}_{page.page_number}",
            vector=vector,
            metadata={
                "page": page.page_number,
                "source": page.source_file,
                "text": text[:500]
            }
        )

        stored_count += 1

        print(
            f"Stored page {page.page_number}"
        )

    print(
        f"\nFinished. Stored {stored_count} pages."
    )