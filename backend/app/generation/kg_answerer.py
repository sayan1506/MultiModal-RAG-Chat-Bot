"""Knowledge graph answerer — generates answers using Neo4j subgraph context.

Retrieves relevant subgraph from Neo4j and uses it as structured context
for Gemini generation. Truncates large subgraphs to stay within token limits.
"""

from __future__ import annotations

import json
from typing import Any

from google import genai

from app.config import settings
from app.retrieval.neo4j_retriever import Neo4jRetriever


class KGAnswerer:
    """Answers queries using Neo4j knowledge graph context."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.neo4j_retriever = Neo4jRetriever()
        self.primary_model = "gemini-2.0-flash-lite"
        self.fallback_model = "gemini-2.5-flash"
        self.max_subgraph_chars = 3000

    async def answer_with_graph(
        self,
        query: str,
        keywords: list[str],
    ) -> dict[str, Any]:
        """Generate an answer using knowledge graph context.

        Args:
            query: The user's question
            keywords: Entity keywords for subgraph retrieval

        Returns:
            Dict with 'answer' (str), 'subgraph' (dict), 'model_used' (str)
        """
        if not keywords:
            return {
                "answer": "No knowledge graph entities identified for this query.",
                "subgraph": {"nodes": [], "links": []},
                "model_used": None,
            }

        # Retrieve subgraph from Neo4j
        subgraph = await self.neo4j_retriever.retrieve(
            keywords=keywords,
            depth=2,
        )

        if not subgraph.get("nodes"):
            return {
                "answer": "No relevant knowledge graph entities found.",
                "subgraph": {"nodes": [], "links": []},
                "model_used": None,
            }

        # Build prompt with truncated subgraph
        prompt = self._build_kg_prompt(query, subgraph)

        # Generate answer with fallback
        answer, model_used = await self._generate_with_fallback(prompt)

        return {
            "answer": answer,
            "subgraph": subgraph,
            "model_used": model_used,
        }

    def _build_kg_prompt(
        self,
        query: str,
        subgraph: dict,
    ) -> str:
        """Build a prompt that includes knowledge graph context."""
        # Serialize subgraph to JSON
        subgraph_json = json.dumps(subgraph, indent=2)

        # Truncate if too large
        if len(subgraph_json) > self.max_subgraph_chars:
            subgraph_json = subgraph_json[: self.max_subgraph_chars] + "\n... [truncated]"

        return f"""You are an expert knowledge graph reasoning assistant.

The user has asked: "{query}"

Use the following knowledge graph subgraph to answer the question.
The subgraph contains nodes (entities) and links (relationships).

Knowledge Graph Context:
{subgraph_json}

Provide a detailed answer based on the knowledge graph structure.
If the answer cannot be determined from the graph, state that clearly.
"""

    async def _generate_with_fallback(
        self,
        prompt: str,
    ) -> tuple[str, str]:
        """Generate answer with primary model, fallback to secondary on quota exhaustion.

        Returns:
            Tuple of (answer_text, model_used)
        """
        # Try primary model
        try:
            response = self.client.models.generate_content(
                model=self.primary_model,
                contents=prompt,
            )
            return response.text, self.primary_model

        except Exception as e:
            error_msg = str(e).lower()

            # Check for quota exhaustion
            if "quota" in error_msg or "resource_exhausted" in error_msg:
                print(f"Primary model quota exhausted, falling back to {self.fallback_model}")
                try:
                    response = self.client.models.generate_content(
                        model=self.fallback_model,
                        contents=prompt,
                    )
                    return response.text, self.fallback_model

                except Exception as fallback_error:
                    print(f"Fallback model also failed: {fallback_error}")
                    return (
                        "Knowledge graph analysis unavailable due to service limits.",
                        None,
                    )
            else:
                print(f"KG answering error: {e}")
                return (
                    f"Knowledge graph analysis failed: {str(e)}",
                    None,
                )
