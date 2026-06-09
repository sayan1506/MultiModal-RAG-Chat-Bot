"""
Formats citations for UI display.
"""


def format_citations(results):
    citations = []

    for result in results:
        source = result.content

        citation = {
            "source_type": result.source,
            "content": source,
            "score": result.score,
        }

        citations.append(citation)

    return citations