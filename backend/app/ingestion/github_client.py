"""GitHub Models client — GPT-4o-mini via Azure OpenAI-compatible endpoint.

Used for: entity extraction, graph refinement, query analysis,
          KG answering, visual answering, answer fusion.

Rate limits (free tier):
  - 150 requests/day
  - 10 requests/minute
  - 8,000 tokens input / 4,000 tokens output per request

Falls back to Gemma4 via Ollama when rate-limited.
"""
from __future__ import annotations

import base64
import time
import ollama
from openai import OpenAI, RateLimitError, APIStatusError
from app.config import settings

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
_github_client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=settings.github_token,
)

_GITHUB_MODEL = "gpt-4o-mini"
_OLLAMA_FALLBACK_MODELS = ["gemma4:e4b", "gemma4:26b"]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_gpt4o_mini(
    prompt: str,
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    system: str | None = None,
) -> str:
    """
    Call GitHub GPT-4o-mini (text only).
    Falls back to Gemma4 via Ollama on rate limit or error.
    Returns the model's text response or "" on total failure.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = _github_client.chat.completions.create(
            model=_GITHUB_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except RateLimitError:
        print("[github_client] Rate limit hit — falling back to Gemma4")
    except APIStatusError as e:
        print(f"[github_client] API error {e.status_code} — falling back to Gemma4")
    except Exception as e:
        print(f"[github_client] Unexpected error: {e} — falling back to Gemma4")

    return _ollama_fallback(prompt)


def call_gpt4o_mini_vision(
    prompt: str,
    image_bytes_list: list[bytes],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
) -> str:
    """
    Call GitHub GPT-4o-mini with one or more images.
    Images are passed as base64-encoded inline data URLs.
    Falls back to Gemma4 vision on rate limit or error.
    Returns the model's text response or "" on total failure.
    """
    # Build content list: images first, then text prompt
    content: list = []
    for img_bytes in image_bytes_list:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high",
            },
        })
    content.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": content}]

    try:
        response = _github_client.chat.completions.create(
            model=_GITHUB_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
    except RateLimitError:
        print("[github_client] Rate limit hit (vision) — falling back to Gemma4")
    except APIStatusError as e:
        print(f"[github_client] API error {e.status_code} (vision) — falling back to Gemma4")
    except Exception as e:
        print(f"[github_client] Unexpected error (vision): {e} — falling back to Gemma4")

    return _ollama_vision_fallback(prompt, image_bytes_list)


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

def _ollama_fallback(prompt: str) -> str:
    """Sync Ollama fallback for text-only calls."""
    client = ollama.Client(host="http://localhost:11434")
    for model in _OLLAMA_FALLBACK_MODELS:
        try:
            response = client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"] or ""
        except Exception as e:
            print(f"[github_client] Ollama {model} error: {e}")
            continue
    print("[github_client] All fallbacks failed.")
    return ""


def _ollama_vision_fallback(prompt: str, image_bytes_list: list[bytes]) -> str:
    """Sync Ollama fallback for vision calls."""
    client = ollama.Client(host="http://localhost:11434")
    for model in _OLLAMA_FALLBACK_MODELS:
        try:
            response = client.chat(
                model=model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": image_bytes_list,
                }],
            )
            return response["message"]["content"] or ""
        except Exception as e:
            print(f"[github_client] Ollama vision {model} error: {e}")
            continue
    print("[github_client] All vision fallbacks failed.")
    return ""


async def call_gpt4o_mini_async(
    prompt: str,
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    system: str | None = None,
) -> str:
    """Async wrapper — runs sync call in thread to avoid blocking event loop."""
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: call_gpt4o_mini(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
        )
    )


async def call_gpt4o_mini_vision_async(
    prompt: str,
    image_bytes_list: list[bytes],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
) -> str:
    """Async wrapper for vision calls."""
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: call_gpt4o_mini_vision(
            prompt,
            image_bytes_list,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    )
