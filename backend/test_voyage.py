"""Debug: find which ticket embed is actually failing."""
import sys
sys.path.insert(0, '.')

import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.core.config import settings
from app.pipeline.chunker import chunk_text
from app.pipeline.embedder import embed_texts
from app.connectors import TicketConnector
from pathlib import Path

engine = sa.create_engine("postgresql://company_brain:company_brain@localhost:5432/company_brain")

# Show which ticket docs already exist
with Session(engine) as db:
    rows = db.execute(
        sa.text("SELECT source_id, ingestion_status FROM documents WHERE source_id LIKE 'ticket:%' ORDER BY source_id")
    ).fetchall()
    print(f"Existing ticket docs ({len(rows)}):")
    for r in rows:
        print(f"  {r[0]}  status={r[1]}")

# Try embedding each ticket one by one
tickets_path = Path("data/raw/tickets/support_tickets.json")
docs = TicketConnector().load(tickets_path)
print(f"\nTotal tickets in file: {len(docs)}")

existing_ids = {r[0] for r in rows}

for doc in docs:
    if doc.source_id in existing_ids:
        print(f"  SKIP {doc.source_id} (already in DB)")
        continue
    chunks = chunk_text(doc.raw_content)
    texts = [c["text"] for c in chunks]
    print(f"  EMBED {doc.source_id} ({len(texts)} chunks)...", end=" ", flush=True)
    try:
        vectors = embed_texts(texts)
        print(f"OK ({len(vectors[0])} dims)")
    except Exception as e:
        print(f"FAIL: {e}")
        break
