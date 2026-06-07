"""Manual smoke test for Phase 4 retrieval pipeline. Run from backend/."""
import asyncio
from app.retrieval.query_analyzer import analyze_query
from app.retrieval.pinecone_retriever import PineconeRetriever
from app.retrieval.neo4j_retriever import Neo4jRetriever
from app.retrieval.image_fetcher import ImageFetcher
from app.retrieval.reranker import rerank

QUERY = "What is machine learning?"


async def main():
    print(f"\n── Query: {QUERY}\n")

    # Step 1 — Analyze query
    print("1. Analyzing query...")
    analyzed = await analyze_query(QUERY)
    print(f"   Keywords:  {analyzed['low_level_keywords']}")
    print(f"   Concepts:  {analyzed['high_level_concepts']}")
    print(f"   Type:      {analyzed['query_type']}")

    keywords = analyzed["low_level_keywords"] + analyzed["high_level_concepts"]

    # Step 2 — Pinecone retrieval
    print("\n2. Retrieving from Pinecone...")
    pinecone_ret = PineconeRetriever()
    pinecone_results = pinecone_ret.retrieve(QUERY, top_k=5)
    print(f"   Got {len(pinecone_results)} results")
    for r in pinecone_results[:2]:
        print(f"   score={r.get('score', 0):.3f}  page={r.get('page')}  text={str(r.get('text',''))[:60]}")

    # Step 3 — Neo4j retrieval
    print("\n3. Retrieving from Neo4j...")
    neo4j_ret = Neo4jRetriever()
    neo4j_results = await neo4j_ret.retrieve(keywords)
    print(f"   Got {len(neo4j_results.get('nodes', []))} nodes, {len(neo4j_results.get('links', []))} links")

    # Step 4 — Image fetching (from first Pinecone result)
    print("\n4. Fetching page images...")
    if pinecone_results:
        file_id   = pinecone_results[0].get("file_id")
        page_nums = [r.get("page") for r in pinecone_results[:3] if r.get("file_id") == file_id]
        fetcher   = ImageFetcher()
        images    = await fetcher.fetch_pages(file_id, page_nums)
        print(f"   Fetched {len(images)} images")
    else:
        print("   No Pinecone results to fetch images from")

    # Step 5 — Re-rank
    print("\n5. Re-ranking...")
    ranked = rerank(pinecone_results, neo4j_results)
    print(f"   Final ranked results: {len(ranked)}")
    for r in ranked[:5]:
        print(f"   [{r.source}] score={r.score:.3f}")

    print("\n── Phase 4 retrieval pipeline: OK ✓\n")


asyncio.run(main())