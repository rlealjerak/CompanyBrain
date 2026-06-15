from __future__ import annotations

import voyageai

from app.core.config import settings

_VOYAGE_MODEL = "voyage-3"
_BATCH_SIZE = 128


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed document *texts* with Voyage AI voyage-3 (1024 dims), batched."""
    client = voyageai.Client(api_key=settings.voyage_api_key)

    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        result = client.embed(batch, model=_VOYAGE_MODEL, input_type="document")
        all_embeddings.extend(result.embeddings)

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Embed a single search query with input_type='query' for retrieval accuracy."""
    client = voyageai.Client(api_key=settings.voyage_api_key)
    result = client.embed([text], model=_VOYAGE_MODEL, input_type="query")
    return result.embeddings[0]
