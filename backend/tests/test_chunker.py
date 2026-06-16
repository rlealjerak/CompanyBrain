"""Functional tests for the text chunker (no database required)."""

from __future__ import annotations

import tiktoken

from app.pipeline.chunker import CHUNK_TOKENS, OVERLAP_TOKENS, chunk_text

_ENC = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    return len(_ENC.encode(text))


def test_empty_text_returns_empty_list():
    assert chunk_text("") == []


def test_short_text_produces_single_chunk():
    text = "This is a short document."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["token_count"] == _token_count(text)


def test_long_text_produces_multiple_chunks():
    # "word " is 1 token; 600 repetitions → 600 tokens → must span 2 chunks
    text = "word " * 600
    chunks = chunk_text(text)
    assert len(chunks) >= 2


def test_chunk_indices_are_sequential():
    text = "word " * 600
    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == i


def test_token_counts_match_actual_encoding():
    text = "word " * 600
    chunks = chunk_text(text)
    for chunk in chunks:
        actual = _token_count(chunk["text"])
        assert chunk["token_count"] == actual


def test_no_chunk_exceeds_chunk_size():
    text = "word " * 1000
    chunks = chunk_text(text)
    for chunk in chunks:
        assert chunk["token_count"] <= CHUNK_TOKENS


def test_overlap_preserved_between_adjacent_chunks():
    """Last OVERLAP_TOKENS of chunk N must equal first OVERLAP_TOKENS of chunk N+1."""
    text = "word " * 1000
    chunks = chunk_text(text)
    assert len(chunks) >= 2

    for i in range(len(chunks) - 1):
        tokens_a = _ENC.encode(chunks[i]["text"])
        tokens_b = _ENC.encode(chunks[i + 1]["text"])
        overlap = min(OVERLAP_TOKENS, len(tokens_a), len(tokens_b))
        assert tokens_a[-overlap:] == tokens_b[:overlap]


def test_all_tokens_covered():
    """Every token from the original text must appear in at least one chunk."""
    text = "word " * 600
    all_tokens = _ENC.encode(text)

    # Rebuild token stream from chunks; each token should appear at least once.
    covered: set[int] = set()
    start = 0
    chunks = chunk_text(text)
    for chunk in chunks:
        count = chunk["token_count"]
        covered.update(range(start, start + count))
        start += count - OVERLAP_TOKENS

    # The last chunk covers everything up to the end
    assert len(all_tokens) <= max(covered) + 1
