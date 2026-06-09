from app.retrieval.query_analyzer import analyze_query
from app.retrieval.pinecone_retriever import PineconeRetriever
from app.retrieval.neo4j_retriever import Neo4jRetriever
from app.retrieval.reranker import rerank

from app.generation.prompt_builder import build_prompt
from app.generation.answer_generator import generate_answer
from app.generation.citation_formatter import format_citations


async def run_generation_pipeline(
    query: str,
):
    print("Analyzing query...")

    analysis = await analyze_query(query)

    print("Analysis:", analysis)

    pinecone = PineconeRetriever()
    neo4j = Neo4jRetriever()

    print("Retrieving from Pinecone...")

    pinecone_results = pinecone.retrieve(
        query_text=query,
        top_k=5,
    )

    print("Retrieving from Neo4j...")

    neo4j_results = await neo4j.retrieve(
        analysis["low_level_keywords"]
    )

    ranked_results = rerank(
        pinecone_results,
        neo4j_results,
        top_k=5,
    )

    prompt = build_prompt(
        query,
        ranked_results,
    )

    answer = await generate_answer(
        prompt
    )

    citations = format_citations(
        ranked_results
    )

    return {
        "answer": answer,
        "citations": citations,
    }