"""Query pipeline: embed → retrieve → rerank → generate.

Redis cache keyed by corpus version ensures results are invalidated
automatically whenever a new document is committed by the ingestion pipeline.
"""

from __future__ import annotations

import hashlib
import json
from typing import Generator

import anthropic
import redis as redis_lib
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.config import settings
from app.pipeline.embedder import embed_query

_CHAT_MODEL = "claude-sonnet-4-6"
_CACHE_TTL = 300  # seconds — 5-minute cache
_TOP_K = 5
_OVER_FETCH = 15  # retrieve more candidates than needed to allow reranking

_SYSTEM_PROMPT = (
    "You are Company Brain, an AI assistant for organizational knowledge. "
    "Answer using ONLY the provided source documents. Cite each source by name. "
    "If two sources contradict each other, explicitly flag the contradiction, "
    "identify which source is more recent, and state which one is authoritative."
)


# ────────────────────────────────────────────────────────── cache helpers


def _redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.redis_url, decode_responses=True)


def _corpus_version(db: Session) -> int:
    return db.execute(sa.text("SELECT version FROM corpus_version")).scalar() or 0


def _cache_key(version: int, query: str) -> str:
    h = hashlib.sha256(query.encode()).hexdigest()
    return f"search:{version}:{h}"


# ────────────────────────────────────────────────────────── core pipeline


def search(query: str, db: Session, top_k: int = _TOP_K) -> list[dict]:
    """Embed → retrieve → rerank. Results are cached by corpus version for 5 min."""
    r = _redis()
    version = _corpus_version(db)
    key = _cache_key(version, query)

    cached = r.get(key)
    if cached:
        return json.loads(cached)

    q_vec = embed_query(query)
    vec_str = "[" + ",".join(str(v) for v in q_vec) + "]"

    rows = db.execute(
        sa.text(
            "SELECT e.chunk_id, e.source_id, e.source_type, e.source_timestamp, "
            "       c.text, c.chunk_index, "
            "       1 - (e.vector <=> CAST(:vec AS vector)) AS similarity "
            "FROM embeddings e "
            "JOIN chunks c ON c.id = e.chunk_id "
            "ORDER BY e.vector <=> CAST(:vec AS vector) "
            f"LIMIT {_OVER_FETCH}"
        ),
        {"vec": vec_str},
    ).fetchall()

    if not rows:
        r.setex(key, _CACHE_TTL, json.dumps([]))
        return []

    # Normalise source_timestamp for recency scoring within this result set.
    # An older source ingested after a newer one still ranks below it because
    # we rerank on source_timestamp, never on created_at (ingestion time).
    timestamps = [row[3] for row in rows if row[3] is not None]
    if len(timestamps) >= 2:
        min_ts = min(t.timestamp() for t in timestamps)
        max_ts = max(t.timestamp() for t in timestamps)
        ts_range = max_ts - min_ts
    else:
        min_ts = timestamps[0].timestamp() if timestamps else 0.0
        ts_range = 1.0  # single timestamp → recency irrelevant, use neutral value

    results = []
    for row in rows:
        sim = float(row[6])
        ts = row[3]
        if ts and ts_range:
            recency = (ts.timestamp() - min_ts) / ts_range
        else:
            recency = 0.5
        combined = 0.7 * sim + 0.3 * recency
        results.append({
            "chunk_id": str(row[0]),
            "source_id": row[1],
            "source_type": row[2],
            "source_timestamp": row[3].isoformat() if row[3] else None,
            "text": row[4],
            "chunk_index": int(row[5]),
            "similarity": round(sim, 4),
            "recency_score": round(recency, 4),
            "combined_score": round(combined, 4),
        })

    results.sort(key=lambda x: x["combined_score"], reverse=True)
    top = results[:top_k]

    r.setex(key, _CACHE_TTL, json.dumps(top))
    return top


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[Source {i}: {c['source_id']} ({c['source_type']}), "
            f"dated {c['source_timestamp'] or 'unknown'}]\n{c['text']}"
        )
    return "\n\n---\n\n".join(parts)


def _sources_payload(chunks: list[dict]) -> list[dict]:
    return [
        {
            "source_id": c["source_id"],
            "source_type": c["source_type"],
            "source_timestamp": c["source_timestamp"],
            "excerpt": c["text"][:300],
            "similarity": c["similarity"],
        }
        for c in chunks
    ]


def chat(query: str, db: Session) -> dict:
    """Full RAG: search → generate → return answer with citations."""
    chunks = search(query, db)
    if not chunks:
        return {"answer": "No relevant documents found in the knowledge base.", "sources": []}

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=_CHAT_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n\n{_build_context(chunks)}\n\nQuestion: {query}",
            }
        ],
    )

    return {"answer": response.content[0].text, "sources": _sources_payload(chunks)}


def stream_chat(query: str, db: Session) -> Generator[str, None, None]:
    """Yield JSON-encoded streaming events for the WebSocket chat endpoint.

    Event shapes:
      {"type": "token",  "content": "<text fragment>"}
      {"type": "done",   "sources": [...]}
      {"type": "error",  "content": "<message>"}
    """
    chunks = search(query, db)
    sources = _sources_payload(chunks)

    if not chunks:
        yield json.dumps({"type": "token", "content": "No relevant documents found."})
        yield json.dumps({"type": "done", "sources": []})
        return

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    with client.messages.stream(
        model=_CHAT_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n\n{_build_context(chunks)}\n\nQuestion: {query}",
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            yield json.dumps({"type": "token", "content": text})

    yield json.dumps({"type": "done", "sources": sources})
