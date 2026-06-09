from __future__ import annotations

import tiktoken

CHUNK_TOKENS = 512
OVERLAP_TOKENS = 64
_ENCODING = "cl100k_base"


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_TOKENS,
    overlap: int = OVERLAP_TOKENS,
) -> list[dict]:
    """Split *text* into overlapping token-bounded chunks.

    Returns a list of dicts:
        {"text": str, "chunk_index": int, "token_count": int}
    """
    enc = tiktoken.get_encoding(_ENCODING)
    tokens = enc.encode(text)

    if not tokens:
        return []

    chunks: list[dict] = []
    start = 0
    idx = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(
            {
                "text": enc.decode(chunk_tokens),
                "chunk_index": idx,
                "token_count": len(chunk_tokens),
            }
        )
        if end >= len(tokens):
            break
        start += chunk_size - overlap
        idx += 1

    return chunks
