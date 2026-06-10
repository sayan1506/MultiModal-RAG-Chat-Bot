"""Visual answerer — generates answers using Gemini Vision with page screenshots.

Caps at 3 images to stay within Gemini token budget and implements
fallback model chain for quota exhaustion scenarios.
"""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types

from app.config import settings
from app.retrieval.image_fetcher import ImageFetcher


class VisualAnswerer:
    """Answers queries using Gemini Vision with up to 3 page screenshots."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.image_fetcher = ImageFetcher()
        self.primary_model = "gemini-2.0-flash-lite"
        self.fallback_model = "gemini-2.5-flash"

    async def answer_with_images(
        self,
        query: str,
        file_id: str,
        page_numbers: list[int],
    ) -> dict[str, Any]:
        """Generate an answer using visual context from page screenshots.

        Args:
            query: The user's question
            file_id: Document identifier for image retrieval
            page_numbers: List of page numbers to include

        Returns:
            Dict with 'answer' (str), 'pages_used' (list[int]), and 'model_used' (str)
        """
        # Cap at 3 images to stay within token budget
        selected_pages = page_numbers[:3]

        if not selected_pages:
            return {
                "answer": "No pages available for visual analysis.",
                "pages_used": [],
                "model_used": None,
            }

        # Fetch page images
        image_data = await self.image_fetcher.fetch_pages(
            file_id=file_id,
            page_numbers=selected_pages,
        )

        if not image_data:
            return {
                "answer": "Could not retrieve page images.",
                "pages_used": [],
                "model_used": None,
            }

        # Build the multimodal prompt
        prompt = self._build_visual_prompt(query, image_data)

        # Try primary model first, fallback on quota exhaustion
        answer, model_used = await self._generate_with_fallback(prompt, image_data)

        return {
            "answer": answer,
            "pages_used": [img["page_number"] for img in image_data],
            "model_used": model_used,
        }

    def _build_visual_prompt(
        self,
        query: str,
        image_data: list[dict],
    ) -> str:
        """Build a prompt that instructs Gemini to analyze the provided images."""
        page_list = ", ".join(str(img["page_number"]) for img in image_data)

        return f"""You are an expert document analysis assistant.

The user has asked: "{query}"

Analyze the provided page screenshots (pages {page_list}) and answer the question.

If the answer is visible in the images, describe what you see and provide a detailed response.
If the answer is not visible, state that the information could not be found in these pages.

Provide a clear, detailed answer based on the visual content.
"""

    async def _generate_with_fallback(
        self,
        prompt: str,
        image_data: list[dict],
    ) -> tuple[str, str]:
        """Generate answer with primary model, fallback to secondary on quota exhaustion.

        Returns:
            Tuple of (answer_text, model_used)
        """
        # Prepare content parts: text prompt + images
        parts = [prompt]

        for img in image_data:
            parts.append(
                types.Part.from_bytes(
                    data=img["image_bytes"],
                    mime_type="image/png",
                )
            )

        # Try primary model
        try:
            response = self.client.models.generate_content(
                model=self.primary_model,
                contents=parts,
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
                        contents=parts,
                    )
                    return response.text, self.fallback_model

                except Exception as fallback_error:
                    print(f"Fallback model also failed: {fallback_error}")
                    return (
                        "Visual analysis unavailable due to service limits.",
                        None,
                    )
            else:
                print(f"Visual answering error: {e}")
                return (
                    f"Visual analysis failed: {str(e)}",
                    None,
                )
