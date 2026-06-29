"""GME embedder — unified multimodal embeddings via GME-Qwen2-VL-2B.

Produces 1536-dim vectors for text, images, and text+image pairs.
All modalities share the same vector space — enabling true cross-modal
retrieval between text queries and document page images.

Model: Alibaba-NLP/gme-Qwen2-VL-2B-Instruct
VRAM: ~2-3GB in 4-bit quantization (fits RTX 4050 6GB)
"""
from __future__ import annotations

import io
import torch
from PIL import Image
from transformers import (
    AutoProcessor,
    Qwen2VLForConditionalGeneration,
    BitsAndBytesConfig,
)

# ---------------------------------------------------------------------------
# Model loading — lazy singleton, loaded once on first call
# ---------------------------------------------------------------------------
_model = None
_processor = None


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model, _processor

    model_name = "Alibaba-NLP/gme-Qwen2-VL-2B-Instruct"
    print("[gme_embedder] Loading GME-Qwen2-VL-2B-Instruct (4-bit)...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    _model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    _processor = AutoProcessor.from_pretrained(model_name)
    _model.eval()
    print("[gme_embedder] GME loaded successfully.")
    return _model, _processor


# ---------------------------------------------------------------------------
# Embedding functions — public API
# ---------------------------------------------------------------------------

def embed_text(text: str) -> list[float]:
    """
    Embed a text string. Returns a 1536-dim vector.
    Used for: entity descriptions, relation keywords, query keywords,
              text chunk embeddings.
    """
    model, processor = _load_model()

    inputs = processor(
        text=text,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        outputs = model(
            **inputs,
            output_hidden_states=True,
        )
        # Use last hidden state of last token as embedding
        embedding = outputs.hidden_states[-1][0, -1, :]
        # L2-normalise
        embedding = embedding / embedding.norm()

    return embedding.float().cpu().tolist()


def embed_image_bytes(image_bytes: bytes) -> list[float]:
    """
    Embed a page image. Returns a 1536-dim vector in the same space
    as embed_text() — enabling text-to-image retrieval.

    Args:
        image_bytes: Raw PNG bytes of a document page.
    Returns:
        1536-dim float list, or [] if image cannot be processed.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        print(f"[gme_embedder] Failed to open image: {e}")
        return []

    model, processor = _load_model()

    # Build a minimal message with just the image
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": ""},  # empty text — image-only embedding
        ],
    }]

    try:
        text_input = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = processor(
            text=text_input,
            images=[image],
            return_tensors="pt",
        ).to(model.device)

        with torch.no_grad():
            outputs = model(
                **inputs,
                output_hidden_states=True,
            )
            embedding = outputs.hidden_states[-1][0, -1, :]
            embedding = embedding / embedding.norm()

        return embedding.float().cpu().tolist()

    except Exception as e:
        print(f"[gme_embedder] Image embedding failed: {e}")
        return []


def embed_text_and_image(text: str, image_bytes: bytes) -> list[float]:
    """
    Fused text+image embedding. Averages text and image vectors.
    Falls back to text-only if image embedding fails.
    Used for: Pinecone upsert of document pages (replaces old embed_text_and_image).
    """
    tv = embed_text(text)
    iv = embed_image_bytes(image_bytes)

    if not iv:
        return tv  # graceful text-only fallback

    # Average and re-normalise
    avg = [(a + b) / 2 for a, b in zip(tv, iv)]
    norm = sum(x ** 2 for x in avg) ** 0.5
    return [x / norm for x in avg] if norm else avg


# Alias for backwards compatibility with any existing callers
embed_image = embed_image_bytes
