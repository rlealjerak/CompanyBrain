# Company Brain + Personal Intelligence Layer
## Execution Plan

**Author:** Roberto Leal  
**Date:** 2026-06-05  
**Status:** Active

---

## Project Summary

A two-layer AI system. The first layer, **Company Brain**, is a shared organizational knowledge base that ingests documents, Slack threads, emails, and support tickets, processes them through a semantic pipeline, and exposes a RAG-powered chat API. The second layer, the **Personal Intelligence Layer (PIL)**, reads the same raw sources, extracts actionable tasks directed at a specific user, and automatically attaches relevant Company Brain context to each task — surfacing everything in a unified dashboard.

The system is built as a portfolio and interview artifact. The headline demo scenario is detecting and resolving a contradiction between two conflicting internal policy documents.

---

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| API | Python 3.11 + FastAPI | Async-first, typed, production-grade |
| Task Queue | Celery + Redis | Simple local setup; clean migration path to SQS in v2 |
| Vector Search | PostgreSQL + pgvector | Eliminates a dedicated vector service; HNSW indexing is fast enough for this scale |
| Relational DB | PostgreSQL 15 | Single database for both structured data and vectors |
| AI Provider (generation) | Anthropic Claude | claude-haiku for batch extraction; claude-sonnet for interactive chat |
| AI Provider (embeddings) | Voyage AI (voyage-3) | Anthropic's official embedding partner; 1024-dimension vectors; dedicated embeddings API separate from Claude |
| Frontend | React + TypeScript | Typed, component-based; standard for this kind of dashboard |
| Local Infra | Docker Compose | One command to start everything; containers translate directly to cloud |
| Cloud Target | AWS (ECS, RDS, ElastiCache, S3/CloudFront) | Managed services that map 1:1 to the local Docker services |

---

## Key Architectural Decisions

**Decision 1 — pgvector over Qdrant**  
Use pgvector (a PostgreSQL extension) instead of running a separate Qdrant container. This removes one service from Docker Compose, keeps all data in one place, and is sufficient for the scale of this project. The tradeoff is less flexibility for vector-specific operations. Document the upgrade path to Qdrant in the README.

**Decision 2 — PIL as a pure consumer of the Brain API**  
The Personal Intelligence Layer has no vector store of its own. When it needs context for a task, it calls the Company Brain search endpoint over HTTP. All knowledge lives in one place. This is the core architectural insight of the two-pipeline design and must be clearly explainable in interviews.

**Decision 3 — Celery/Redis for v1, SQS migration path documented**  
Celery and Redis run locally with no external dependencies and cover all requirements for v1. Design the queue layer cleanly so that swapping the broker to AWS SQS in v2 is a configuration change, not a structural rewrite. Document this explicitly in the README.

**Decision 4 — Haiku for batch processing, Sonnet for interactive chat**  
All background extraction (knowledge extraction, task extraction, context bundling) uses claude-haiku for cost efficiency. Only interactive chat calls use claude-sonnet for quality. This is a meaningful cost optimization during demos when the same questions are asked repeatedly.

**Decision 5 — Voyage AI for embeddings**  
Anthropic's Claude API handles text generation only — it does not provide a vector embeddings endpoint. Voyage AI is Anthropic's official embedding partner and the natural complement to the Claude stack. Use `voyage-3` (general-purpose, 1024-dimension vectors) for both ingestion and query embedding. This means two API keys and two SDKs (`anthropic` and `voyageai`), but keeps everything within one trusted provider relationship. The pgvector column dimension must be set to 1024 to match. `voyage-3-lite` is an available cost-reduction option for v2 if embedding costs become significant at scale.

**Decision 6 — Redis query cache with corpus versioning**  
All semantic search results are cached in Redis for 5 minutes. Cache keys include a corpus version counter that is incremented transactionally every time a document ingestion job completes successfully. This guarantees that stale cached answers can never survive a pipeline run — the moment new documents land, the entire cache namespace is invalidated atomically, not file-by-file. This is critical for the headline demo scenario: after any ingestion, the next refund policy query must always reflect the current corpus.

**Decision 7 — Two-tier authorization model**  
Authentication (JWT, who you are) is separate from authorization (what you can do). Query and personal endpoints are accessible to any authenticated user. Ingestion trigger and job management endpoints are restricted to users with the `admin` role. This prevents any authenticated account from driving unbounded Claude API calls or data churn through the ingestion pipeline.

---

## Phase Overview

| Phase | Name | Goal | Dependency |
|---|---|---|---|
| 1 | Infrastructure | All containers start; API is reachable | None |
| 2 | Synthetic Data | Realistic dataset with deliberate contradictions committed to git | Phase 1 |
| 3 | Ingestion Pipeline | All files processed; documents, chunks, embeddings in the database | Phase 2 |
| 4 | Query API + Chat UI | RAG chat detects and resolves the refund policy contradiction | Phase 3 |
| 5 | Personal Intelligence Layer | Tasks extracted; dashboard shows urgency scores and pre-bundled context | Phase 4 |
| 6 | Polish + Deployment | Tests pass; demo runs in under 3 minutes; system live at a public URL | Phase 5 |

Do not begin a phase until the previous phase's definition of done is fully satisfied.

---

## Phase 1 — Infrastructure

### Goal
A fully running local environment before any application logic is written. Every later phase depends on this being stable.

### Tasks

**1.1 — Repository Structure**  
Create the monorepo layout. Top-level folders: `backend/`, `frontend/`, `data/`, `infra/`, `docs/`, `scripts/`. Inside `backend/`, organize by concern: `app/api/` for route handlers, `app/connectors/` for data source adapters, `app/pipeline/` for chunking, embedding, and extraction, `app/personal/` for PIL logic, `app/models/` for database models, `app/core/` for shared configuration and utilities, `app/tasks/` for Celery task definitions. Commit the empty structure to git immediately.

**1.2 — Docker Compose**  
Define all services in a single `docker-compose.yml`: `postgres` (PostgreSQL 15 with pgvector), `redis`, `api` (FastAPI served via uvicorn), `worker` (Celery worker), `beat` (Celery Beat scheduler), `frontend` (React app). All services share a private Docker network. The `api` and `worker` services must wait for Postgres and Redis health checks before starting. Set `restart: unless-stopped` on all services.

**1.3 — Environment Variables**  
Create `.env.example` documenting every variable the system needs: Anthropic API key, Voyage AI API key, PostgreSQL connection string, Redis URL, JWT secret, and an environment flag (development/production). Add `.env` to `.gitignore`. Never commit real secrets. Both AI API keys are required — the system will fail at ingestion time without the Voyage AI key even if the Anthropic key is present.

**1.4 — Python Project Bootstrap**  
Create `requirements.txt` with core dependencies: FastAPI, uvicorn, SQLAlchemy, Alembic, the Anthropic Python SDK, the Voyage AI Python SDK (`voyageai`), Celery with Redis support, Pydantic Settings, psycopg2-binary, pgvector, tiktoken, and pytest. Create the `backend/Dockerfile`. Verify that `pip install -r requirements.txt` runs without errors inside the container.

**1.5 — Health Check Endpoint**  
Implement a single `GET /health` endpoint that returns `{"status": "ok"}`. This is the smoke test for Phase 1.

**1.6 — Database Connection Wiring**  
Configure SQLAlchemy to connect to PostgreSQL using the environment variable. Verify the connection is live from inside the running API container before moving on.

### Definition of Done
- `docker compose up` starts all containers with no errors
- `curl localhost:8000/health` returns `{"status": "ok"}`
- The API container can connect to both PostgreSQL and Redis
- The empty folder structure is committed to git with a `.gitignore` that excludes `.env`

---

## Phase 2 — Synthetic Data Generation

### Goal
A complete, committed dataset that reads as realistic internal content for a fictional e-commerce company (Acme E-commerce). The dataset must contain at least two deliberate contradictions — these are the foundation of the headline demo scenario.

### Why Strategic Noise Matters
A knowledge base that retrieves clean data from a single authoritative source is unremarkable. A system that detects a conflict between a policy document and a Slack thread, identifies which source is more recent, and explicitly resolves the contradiction is what impresses interviewers. The synthetic data must be designed to make that scenario possible.

### Tasks

**2.1 — Policy and Process Documents (Markdown)**  
Generate 8–12 Markdown files covering: current refund policy (30-day window, authoritative, dated recently), old refund policy (14-day window, dated 6 months ago — this is Contradiction A), escalation paths by issue type, pricing rules and discount authority, shipping policy and SLAs, VIP customer handling, new customer onboarding checklist, and a product catalog guide. Every file must read as a realistic internal company document.

**2.2 — Slack Threads (JSON)**  
Generate 5–10 JSON files representing Slack conversations. Required threads: a support agent asking about refund policy where a senior agent explicitly confirms the 30-day rule (this resolves Contradiction A), a manager directly @mentioning a user to follow up on an overdue enterprise proposal (this generates the highest-priority PIL task), an engineering discussion about a checkout bug with implicit action items, a sales thread where a pricing exception was approved verbally but never written into any document (Contradiction B), and a customer success thread planning a quarterly business review with soft deadlines.

**2.3 — Support Tickets (JSON)**  
Generate 25–50 tickets. Each ticket needs: ID, customer ID, subject, body, status, priority, creation date, resolution date, and resolution notes. Include a mix of refund requests, shipping complaints, billing disputes, and technical issues. Some tickets should reference policy details inconsistent with the documents.

**2.4 — Email Threads (JSON)**  
Generate 3–5 email chains: one account manager chain with an enterprise client where a follow-up action is implied (PIL task), one internal billing dispute referencing the pricing document, one vendor negotiation with an action item buried deep in a long chain.

**2.5 — Structured Reference Data (JSON)**  
Three files: a pricing table with product tiers, discount thresholds, and coupon codes; an escalation matrix mapping issue type and severity to the right contacts; a team directory with names, roles, and departments (used later to resolve @mentions and identify managers).

**2.6 — Generation Approach**  
Use the Claude API via a Python script in `scripts/generate_data.py`. Use a two-pass approach: first generate clean, realistic content, then run a second prompt on that content asking Claude to introduce realistic noise — outdated sections, conflicting details, ambiguous references. Save all output to `data/raw/`. Commit all generated files so the dataset is fixed and reproducible.

**2.7 — Contradiction Documentation**  
Write `data/README.md` explicitly documenting both contradictions: what they are, which files are involved, the dates of each source, and the expected system behavior when both are retrieved together.

### Definition of Done
- All files in `data/raw/` exist, are valid JSON or Markdown, and read as realistic content
- Two contradictions are documented in `data/README.md`
- All files committed to git

---

## Phase 3 — Ingestion and Processing Pipeline

### Goal
All synthetic data files are processed through the full pipeline. Documents, chunks, and embeddings are in the database. The ingestion jobs table shows successful runs.

### Tasks

**3.1 — Database Schema and Migrations**  
Before writing any pipeline code, define all database tables using Alembic migrations. Create all tables now — even those not used until Phase 5 — to avoid disruptive schema changes later. Required tables:
- `documents` — raw content, source metadata, extracted knowledge JSON, source quality score, `source_id`, `content_hash` (SHA-256 of raw content), `source_mtime`, `ingestion_status` (values: `pending`, `complete`), and `ingestion_job_id UUID REFERENCES ingestion_jobs(id)` (the ID of the ingestion job that created this row). A document is inserted as `pending` and transitioned to `complete` only after all its chunks, embeddings, and extracted knowledge have been successfully written. Add a `UNIQUE (source_id, content_hash)` constraint — at most one row per file version can exist at any time. The `ingestion_status` column is the completeness gate: the hash-skip idempotency check must only skip documents with `ingestion_status = 'complete'`. A `pending` row with a matching hash indicates a prior crashed run left partial data; it must be deleted (cascading to chunks and embeddings) and re-processed from scratch. The `ingestion_job_id` column is required so pending-row repair is scoped to the specific stale job — not any `pending` row matching the hash.
- `chunks` — text segments linked to parent documents, with chunk index and token count
- `embeddings` — vectors linked to chunks, with source metadata and timestamp for reranking. The vector column must be declared as dimension **1024** to match the `voyage-3` output. Setting the wrong dimension here breaks all vector operations and requires a migration to fix.
- `ingestion_jobs` — tracks every sync run with status, timing, record count, and error messages. Required columns beyond the basics: `source_id`, `status` (values: `running`, `retrying`, `success`, `failed`), `locked_at` (timestamp updated to `now()` at job entry **and refreshed as a heartbeat after each major pipeline checkpoint** — file load, chunk, embed, store), and `attempt_number`. Add a **partial unique index on `(source_id) WHERE status IN ('running', 'retrying')`** — this covers both active states so no concurrent or retry-gap race can insert a second live job row for the same source. The heartbeat keeps `locked_at` fresh throughout the job lifetime; the stale threshold (15 minutes) must be set larger than the maximum expected time between any two checkpoints, not the total job duration.
- `users` — for authentication. Include a `role` column (values: `user`, `admin`). Seed at least one admin user during initial setup.
- `tasks` — for the PIL: description, user ID, urgency score, urgency band, status, deadline, context bundle (JSONB), and `source_reference TEXT NOT NULL` — a namespaced identifier for the source message that generated the task (format: `slack:{thread_ts}`, `email:{message_id}`, `ticket:{ticket_id}`). The namespace prefix prevents cross-source collisions. `source_reference` must be populated before every task INSERT; a missing value is a pipeline bug, not a nullable edge case. Add a `UNIQUE (user_id, source_reference)` constraint to prevent duplicate task extraction from the same source message across retries and repeated scans.
- `corpus_version` — a single-row table storing an incrementing integer counter. Incremented inside **Commit 2** — the same transaction that writes chunks, embeddings, and marks the document `complete`. One increment per successfully committed document, not once per job. This is the only place the counter advances; the job-level `success` transition does not touch it. Cache invalidation is implicit — any query that runs after a new document is committed will see the incremented version and miss the cache.

Create the HNSW index on the embeddings vector column immediately after the initial migration. Do not leave this as a manual step.

**3.2 — Connector Interface**  
Define an abstract `BaseConnector` class and a `Document` dataclass in `app/connectors/base.py`. Every connector, regardless of source format, must output a list of `Document` objects. The `Document` contains: raw text content, source name, source-specific ID, author, timestamp, content type, and a metadata dictionary. This contract is the extensibility guarantee — the pipeline never knows or cares what format the data came from.

**3.3 — File Connectors**  
Implement three connectors: `MarkdownConnector` for policy documents, `JsonConnector` for Slack threads and email chains, and `JsonConnector` (same class, different schema mapping) for support tickets. Support tickets are generated as JSON in Phase 2 — the `CsvConnector` originally planned here was a format mismatch. Each connector reads its file, parses the format, and returns a list of `Document` objects conforming to the base interface. The `JsonConnector` must handle both the Slack/email array-of-messages schema and the support-ticket flat-object schema via a configurable field mapping at construction time.

**3.4 — Chunker**  
Implement the chunker in `app/pipeline/chunker.py`. Target chunk size: 512 tokens (measured with tiktoken). Overlap: 50 tokens between adjacent chunks to prevent context loss at boundaries. Split on sentence boundaries where possible — never cut mid-sentence. Each chunk must store its index within the parent document and its token count.

**3.5 — Embedder**  
Implement the embedder in `app/pipeline/embedder.py` using the **Voyage AI SDK** (`voyageai` Python package), not the Anthropic SDK. Anthropic's Claude API is generation-only and has no embeddings endpoint. The embedding model is `voyage-3`, which produces 1024-dimension vectors. Batch API calls — the Voyage AI SDK supports batching up to 128 texts per request, which is dramatically faster than one request per chunk. Store the resulting vectors alongside the chunk's metadata: source, source type, document ID, chunk index, and timestamp. The timestamp is critical for conflict resolution — it is how the system determines which of two contradicting sources is more recent.

The `VOYAGE_API_KEY` environment variable must be present. Add a startup check that fails fast with a clear error message if either `ANTHROPIC_API_KEY` or `VOYAGE_API_KEY` is missing, rather than surfacing a cryptic SDK error during the first ingestion run.

**3.6 — Knowledge Extractor**  
Implement the extractor in `app/pipeline/extractor.py`. Send the full document (not individual chunks) to Claude with a structured extraction prompt. Claude returns a JSON object containing: key entities (people, teams, products, systems), key factual statements and policies, rules and procedures, relationships between entities, and a source quality score from 1–5 indicating how authoritative the document appears. Store this JSON in the `extracted_knowledge` column on the `documents` table.

**3.7 — Celery Configuration**  
Define two named queues: `brain` for all Company Brain ingestion tasks, and `personal` for PIL task extraction. Both share the same Redis broker but use separate worker concurrency so they do not compete. Configure Celery Beat to scan the data folder every 5 minutes and trigger ingestion for new or modified files.

**3.8 — Ingestion Celery Task and Job State Machine**  
Implement the full pipeline as a Celery task in `app/tasks/brain_tasks.py`. The ingestion job must follow an explicit four-state machine that is safe under both caught exceptions and unhandled worker crashes:

**States:** `running` → `retrying` → `running` (on each subsequent attempt) → `success` or `failed`

The partial unique index covers `WHERE status IN ('running', 'retrying')`. There are **three distinct entry algorithms** — implementations must not conflate them:

**Entry Algorithm A — Fresh start** (Celery Beat cycle or manual trigger, no `job_id` in task kwargs):
1. Try `INSERT a new row with status = 'running', locked_at = now(), attempt_number = 1`. If successful, the source slot is acquired — continue to processing.
2. If the INSERT is rejected by the partial unique index, an active row exists. Enter the **Stale Takeover Transaction** (Algorithm C). If Algorithm C succeeds, continue to processing with the new `job_id`. If it aborts (job is still live), exit silently.
3. Pass the acquired `job_id` forward via `self.retry(kwargs={'job_id': job.id, ...})` so retries use Entry Algorithm B.

**Entry Algorithm B — Retry start** (Celery retry invocation, `job_id` present in task kwargs):
1. Do **not** INSERT. Do **not** run the stale-lock check.
2. `UPDATE ingestion_jobs SET status='running', locked_at=now(), attempt_number=attempt_number+1 WHERE id=:job_id AND status='retrying'`. Check affected row count: 1 = success, proceed; 0 = the row was taken over by a stale-lock recovery between retry scheduling and execution — abort, do not proceed.
3. This path is the only way a `retrying` row transitions back to `running`. It is keyed on `job_id`, not `source_id`, so it cannot collide with the unique index.

**Entry Algorithm C — Stale Takeover Transaction** (called from Algorithm A when step 1's INSERT is rejected):
All steps below run inside a single database transaction. The `SELECT FOR UPDATE` serializes concurrent takeover attempts — only one caller can proceed; all others wait and re-evaluate after the lock is released.
1. `SELECT id, locked_at FROM ingestion_jobs WHERE source_id=:sid AND status IN ('running','retrying') FOR UPDATE` — lock the active row. If no row is returned (the prior job completed between Algorithm A's failed INSERT and now), rollback and retry Algorithm A step 1.
2. Inspect `locked_at`. If less than 15 minutes old, the job is still live — rollback, abort silently.
3. If stale: `UPDATE ingestion_jobs SET status='failed' WHERE id=:existing_id`, then `INSERT INTO ingestion_jobs (..., status='running', locked_at=now(), attempt_number=1)`, then COMMIT. Both the retirement and the replacement are committed atomically — the source slot is never unguarded between the two statements.
4. If the transaction fails for any reason (including a concurrent takeover that already inserted after our lock): rollback. The old row reverts to its previous `running`/`retrying` state. Abort — do not retry the takeover.

**Heartbeat requirement:** During processing, the worker must update `locked_at = now()` after each major pipeline checkpoint (file load, chunking, embedding API call, store). The stale threshold (15 minutes) must be larger than the maximum expected duration of any single checkpoint — document the chosen value and its basis in the code.

**Bounded checkpoint timeouts:** Every external call (Voyage AI embedding, Claude extraction, database writes) must have an explicit timeout set. No checkpoint may block indefinitely. If a checkpoint exceeds its timeout, treat it as a retryable failure. This makes the stale threshold enforceable — a worker that is genuinely stuck will stop heartbeating within a bounded time, not after an unbounded hang.

**Fencing requirement:** Before executing each write checkpoint — Commit 1 (the atomic document-claim transaction that may include a repair delete and always includes the pending row INSERT), Commit 2 (chunks + embeddings + complete), and every `locked_at` heartbeat update — the worker must verify its job row is still active: re-read `SELECT status FROM ingestion_jobs WHERE id=:job_id`. If `status != 'running'`, the worker has been evicted by a stale takeover — abort all further writes immediately without error. This prevents a slow-but-live worker that was evicted from writing after a new worker has taken over the same source. The fencing check must happen inside the same transaction as the write it guards, not as a separate preceding query, to eliminate the read-then-write race.

**On caught retryable exception:** Transition the row to `retrying` before calling `self.retry(kwargs={'job_id': job.id, ...})`. The `retrying` state remains under the partial unique index — no other process can claim the source slot during the retry delay.

**On worker crash:** No cleanup runs. The row stays `running` or `retrying` with a stale `locked_at`. Algorithm A's stale-lock check recovers it on the next attempt.

**On final failure (max retries exceeded):** Transition to `failed` with the error message. Surface prominently in the ingestion dashboard.

**On success:** Transition to `success`. Do not increment `corpus_version` here — it was already incremented inside Commit 2 when the document was committed. Bumping it again at job success would double-invalidate the cache and make the version counter's semantics ambiguous for any job that processes more than one document.

**3.9 — Idempotency and Concurrency Safety**  
Before ingesting a file, compute a SHA-256 hash of its raw content. The hash check and the resulting document row insertion are performed together in a single **atomic document-claim transaction** (this is Commit 1). They must never be split into separate transactions — doing so leaves a window where two concurrent jobs can both observe the same state, both act on it, and one fails on the UNIQUE constraint or deletes a live job's row.

**Commit 1 — Atomic document claim (fenced, serialized):**
All steps below run inside one transaction:
1. `SELECT id, ingestion_job_id, ingestion_status FROM documents WHERE source_id=:sid AND content_hash=:hash FOR UPDATE` — lock any existing row for this file version. `FOR UPDATE` serializes concurrent attempts: a second job trying this SELECT on the same row blocks until the first transaction commits or rolls back.
2. Fencing check: `SELECT status FROM ingestion_jobs WHERE id=:current_job_id`. If `status != 'running'`, the current job has been evicted — rollback, abort.
3. Branch on what the SELECT returned:
   - **`complete` row found:** This file version is fully ingested — rollback, skip. No work needed.
   - **`pending` row found:** Verify its `ingestion_job_id` is **not** the current job's `job_id` (if it matches, something is structurally wrong — rollback, surface an error). Then `DELETE FROM documents WHERE id=:stale_doc_id AND ingestion_job_id=:stale_job_id`. Foreign-key cascades remove partial chunks and embeddings. Proceed to step 4.
   - **No row found:** Proceed directly to step 4.
4. `INSERT INTO documents (..., ingestion_status='pending', ingestion_job_id=:current_job_id)`. If the INSERT fails with a unique constraint violation — meaning a concurrent job committed its own pending row between step 1's `FOR UPDATE` returning nothing and this INSERT — treat it as "another job claimed this file version, abort cleanly." This is not a retryable error; it means the other job will process the file.
5. COMMIT. The pending row is now visible to recovery code.

**Pipeline steps (no DB writes):** Run chunking (in-memory), call the Voyage AI embedding API, call the Claude extraction API. All results are held in memory. No database writes happen during API calls — this keeps transactions short and avoids holding locks across external network calls.

**Commit 2 (atomic):** Write all chunks, all embeddings, extracted knowledge, update `ingestion_status = 'complete'`, and increment `corpus_version` in a single transaction. Either all of these land together or none do.

If the worker crashes between Commit 1 and Commit 2, the `pending` row persists with no children. The next run's Commit 1 transaction acquires the `FOR UPDATE` lock on the pending row, detects it's stale, deletes it, and inserts a fresh pending row — all atomically. If the worker crashes during Commit 2, the transaction rolls back — the `pending` row from Commit 1 remains, and the same repair path applies on the next run.

Three distinct entry algorithms govern every ingestion task invocation — never use a single generic path for all three:

- **Fresh starts** (Beat/manual, no `job_id`): try INSERT new `running` row; on unique violation, enter the Stale Takeover Transaction (Algorithm C). Forward the acquired `job_id` to retries via task kwargs.
- **Retry starts** (`job_id` present in task kwargs): UPDATE the specific `retrying` row back to `running` via `WHERE id=:job_id AND status='retrying'`; proceed only if 1 row affected. Never INSERT. Never run the stale-lock check.
- **Stale takeovers** (Algorithm C): a single transaction that does `SELECT FOR UPDATE` on the active row, checks staleness, then retires it and inserts the replacement atomically. The source slot is never dropped without an immediate replacement in the same transaction. If the transaction rolls back for any reason, the old row reverts to its active state — no gap is left.

The worker refreshes `locked_at` at each pipeline checkpoint so legitimately running jobs never appear stale. The stale threshold must be calibrated against the maximum single-checkpoint duration, not total job time.

### Definition of Done
- Running ingestion against all files in `data/raw/` completes without errors
- The `documents`, `chunks`, and `embeddings` tables are populated in PostgreSQL
- The `ingestion_jobs` table has records showing `status = 'success'`
- Both refund policy documents (old and new) are in the database with different timestamps

---

## Phase 4 — Query API and Chat Interface

### Goal
A working chat interface where a user can ask questions and receive grounded answers with source citations. The contradiction between the two refund policy documents is correctly detected and resolved by the system.

### Tasks

**4.1 — Query Pipeline**  
Implement the four-step query pipeline in `app/pipeline/query.py`:
1. **Embed** the question using the Voyage AI `voyage-3` model — the same model and provider used during ingestion. Query vectors and document vectors must come from the same model; mixing providers or models produces meaningless similarity scores.
2. **Retrieve** the top-5 most similar chunks from pgvector using cosine distance
3. **Rerank** the results by a combination of relevance score and recency (timestamp) — this ensures the newer refund policy ranks above the older one
4. **Generate** a Claude response with the retrieved chunks as context, instructing it to cite sources by name and to explicitly flag when two sources contradict each other

**4.2 — Redis Query Cache with Corpus Versioning**  
Before hitting the vector database, read the current corpus version from the `corpus_version` table. Build the cache key as `search:{corpus_version}:{sha256(query + filters)}`. Cache results under this key for 5 minutes.

When an ingestion job completes successfully, increment the `corpus_version` counter inside the same database transaction that commits the new documents. Because the version is part of every cache key, all prior cached results become unreachable immediately — no explicit key enumeration or invalidation loop required. The next query after any ingestion will always miss the cache and hit the updated vector database. This is the only safe invalidation strategy for a corpus that changes at ingestion boundaries.

**4.3 — API Endpoints — Query Router (`/v1/query/`)**  
- `POST /v1/query/search` — semantic search, returns the top matching chunks with relevance scores and source metadata
- `POST /v1/query/chat` — full RAG pipeline, returns a Claude-generated answer with citations
- `WebSocket /v1/query/chat/stream` — streaming version of chat, sends answer tokens as Claude generates them

**4.4 — API Endpoints — Ingestion Router (`/v1/ingest/`)**  
All three ingestion endpoints require the `admin` role. A user with role `user` receives 403 Forbidden. This is enforced by a `require_admin` FastAPI dependency applied to the entire ingestion router, not on individual routes.
- `POST /v1/ingest/trigger` — manually trigger a sync for a specific source or all sources (admin only)
- `GET /v1/ingest/jobs` — list recent ingestion jobs with status, duration, and record counts (admin only)
- `GET /v1/ingest/jobs/{id}` — details for a specific job including any error message (admin only)

**4.5 — API Endpoints — Auth Router (`/v1/auth/`)**  
- `POST /v1/auth/login` — validates credentials, returns a JWT token
- `GET /v1/auth/me` — returns the current user's profile

**4.6 — JWT Authentication and Role-Based Authorization**  
Implement JWT signing and verification in `app/core/auth.py`. The JWT payload must include the user's `role` field alongside the user ID. Create two FastAPI dependencies: `get_current_user` (validates the token, returns the user) and `require_admin` (calls `get_current_user` and raises 403 if the role is not `admin`). Apply `get_current_user` to all query and personal endpoints. Apply `require_admin` to all ingestion endpoints.

For the streaming WebSocket endpoint, do not pass the JWT as a URL query parameter — query strings are captured in access logs, browser history, and reverse proxy traces, which exposes bearer tokens even over TLS. Instead, use the `Sec-WebSocket-Protocol` header to carry the token as a subprotocol value (a standard pattern for WebSocket bearer auth), or accept it in the first message payload after the connection is established and close the socket immediately if the token is missing or invalid.

**4.7 — Standardized Error Responses**  
Every API error must return a consistent JSON shape with an error code and a human-readable message. Register a global exception handler in `app/main.py`. Never return unstructured error strings or Python tracebacks to the client.

**4.8 — React Chat Interface**  
Build in `frontend/src/pages/ChatPage.tsx`. Components needed: a message thread displaying the conversation history, a text input at the bottom, and a source citations panel below each answer. Connect to the streaming WebSocket so responses appear token by token. The citations panel must show the document name, content type, and a short excerpt for each source so the user can trace every claim back to its origin.

**4.9 — Ingestion Dashboard**  
Build in `frontend/src/pages/IngestionPage.tsx`. Show a table with each data source, its last sync time, document count, and status. Add a manual sync trigger button per source. Show a job history list at the bottom with recent runs, their duration, and record counts. If a job failed, show the error message inline.

### Definition of Done
- `POST /v1/query/chat` with "What is our refund policy?" returns an answer that cites both the current policy document and the Slack thread, explicitly notes the contradiction, and identifies the current policy as more authoritative
- WebSocket streaming delivers tokens progressively in the chat UI
- Source citations panel shows document name, type, and excerpt
- Ingestion dashboard displays all sources with last sync time
- Manual sync trigger works and shows the new job in the job history

---

## Phase 5 — Personal Intelligence Layer

### Goal
Tasks extracted from synthetic Slack and email threads appear in the dashboard with urgency scores. Clicking a task opens a context panel showing relevant knowledge chunks already attached — the user does not have to search for anything manually.

### Tasks

**5.1 — Task Extractor**  
Implement in `app/personal/task_extractor.py`. For each Slack thread and email chain, send the full content to Claude along with the current user's name and role. Ask Claude to return a structured JSON array of tasks. Each task must include: a description of what needs to be done, the action type (follow-up, respond, review, complete, or escalate), a raw urgency score from 1–10, a deadline if mentioned, whether the user was explicitly named or only implied by context, and the source message ID.

**5.2 — Urgency Scoring Function**  
Implement in `app/personal/urgency_scorer.py`. Start with Claude's raw urgency score. Apply bonuses: +2 if the deadline is within 24 hours, +1.5 if within 3 days, +1 if within a week, +1 if the user was explicitly named (not just implied), +1 if the sender is a manager in the team directory. Apply a daily decay for tasks that have been sitting unactioned for more than 3 days. Clamp the final score between 1 and 10. Assign urgency bands: high (8–10), medium (5–7), low (1–4).

**5.3 — Context Bundler**  
Implement in `app/personal/context_bundler.py`. After a task is scored and stored, the bundler runs automatically as a follow-up Celery task. It takes the task description, calls the Company Brain `POST /v1/query/search` endpoint with that description as the query, retrieves the top 3–5 most relevant chunks, and writes them to the `context_bundle` column on the task record. **This must be implemented as an HTTP call to the Brain API, not a direct database query.** This keeps the PIL as a pure consumer and ensures future query pipeline improvements (reranking, caching, filtering) automatically benefit the PIL.

**5.4 — PIL Celery Task**  
Implement in `app/tasks/personal_tasks.py`. For each Slack or email file, run the task extractor, score each extracted task, store it in the `tasks` table, and dispatch a follow-up context bundling task. Handle retries identically to the brain ingestion tasks (3 retries, short delay, failure stored with error message).

**5.5 — Personal API Endpoints (`/v1/personal/`)**  
- `GET /v1/personal/tasks` — list all tasks for the current user, sorted by urgency score descending
- `GET /v1/personal/tasks/{id}` — single task with its full context bundle
- `PATCH /v1/personal/tasks/{id}` — update status (complete, snoozed, dismissed)
- `GET /v1/personal/summary` — task counts grouped by urgency band for the dashboard header

**Tenant isolation invariant:** Every query and mutation on the `tasks` table must filter by both `tasks.id` and `tasks.user_id == current_user.id`. This applies to every single-record endpoint — `GET /{id}` and `PATCH /{id}`. An implementation that fetches by `id` alone allows any authenticated user to read or mutate another user's tasks by guessing or enumerating UUIDs. On a mismatch between the task's `user_id` and the authenticated user's ID, return 404 (not 403) — leaking the existence of a task to an unauthorized user is itself a disclosure. This invariant must be applied at the database query layer, not as a post-fetch check in application code.

**5.6 — Unified Dashboard**  
Build in `frontend/src/pages/DashboardPage.tsx`. Three panels:
- **Left — Task Feed:** Tasks grouped into high, medium, and low urgency bands. Each card shows description, source, sender, deadline (if any), and urgency score. Action buttons: mark complete, snooze, dismiss. The feed polls for new tasks every 60 seconds.
- **Center — Context Panel:** Opens when the user clicks a task. Shows the knowledge chunks bundled onto that task, each with source label and relevance score. If the bundle is not yet populated (async lag), show a loading indicator.
- **Right — Brain Search Bar:** A search input that calls the Company Brain search endpoint directly. Results show the top 5 chunks with source labels. The user can query any organizational knowledge without leaving the dashboard.

### Definition of Done
- At least one task appears in the dashboard extracted from the enterprise proposal Slack thread
- That task is in the high urgency band (manager sender + explicit mention)
- Clicking the task opens the context panel with 3–5 relevant knowledge chunks already attached
- The context bundle is populated before the user clicks (async background bundling completes within ~30 seconds of task creation)
- The task feed refreshes every 60 seconds without a page reload

---

## Phase 6 — Polish, Testing, and Deployment

### Goal
The system runs end to end without errors. The README is professional. The demo scenario runs cleanly in under 3 minutes. The project is deployed and accessible at a public URL.

### Tasks

**6.1 — Error Handling Audit**  
Review every API endpoint and every Celery task. Every endpoint must return the standardized error JSON shape on failure. Every task must retry up to 3 times with exponential backoff before marking the job failed. Claude API rate limit errors and timeouts must be caught and handled gracefully — they must never crash a worker or return a 500 to the client. No part of the system should fail silently.

**6.2 — Test Suite**  
Write focused tests for the 6 paths that break most painfully if wrong:
- **Chunker:** Given a document of a known token count, assert the correct number of chunks with the correct overlap preserved
- **Search pipeline:** Given a seeded database with both refund policy documents, assert that a search for "refund policy" retrieves chunks from both documents
- **Contradiction detection:** Assert that the RAG answer to "refund policy" contains language indicating a conflict between sources
- **Task extraction:** Given the enterprise proposal Slack thread, assert that a task is created with a description containing follow-up intent
- **Context bundler:** Assert that after task creation, the `context_bundle` column is non-null and contains at least one chunk
- **Auth guard:** Assert that all protected endpoints return 401 without a valid JWT token
- **Tenant isolation:** Create two users (user A and user B), create a task owned by user A, assert that `GET /v1/personal/tasks/{id}` returns 404 when called with user B's token, and that `PATCH /v1/personal/tasks/{id}` similarly returns 404 — not 403, not 200
- **Ingestion retry recovery — caught exception:** Simulate a retryable API error mid-pipeline; assert the job row transitions to `retrying` (not `failed`); assert the retry invocation uses Entry Algorithm B (UPDATE by `job_id`, not INSERT), transitions the row back to `running`, and completes successfully; assert no duplicate documents are created
- **Retry does not abort on its own unique-index guard:** Assert that the retry invocation does not attempt an INSERT or stale-lock check — it must match exactly 1 row via `WHERE id=:job_id AND status='retrying'` and proceed without touching the partial unique index
- **Crash after document insert, before chunks complete:** Insert a `pending` document row for a source, then run a fresh ingestion attempt; assert the `pending` row and any partial chunks/embeddings are deleted, full ingestion runs from scratch, and the document ends as `complete` with all expected chunks and embeddings present
- **Hash skip only fires on `complete` documents:** Assert that a `pending` document row with a matching `(source_id, content_hash)` is never silently skipped — it must trigger repair, not skip
- **Transaction rollback leaves detectable `pending` row:** Commit the `pending` document row (Commit 1), then force a rollback of Commit 2 (simulate a DB error during chunk write); assert the `pending` row survives (it was committed in Commit 1), assert the next run detects it, deletes it, and completes successfully with a `complete` row
- **Fencing aborts evicted worker writes:** Mark a job row as `failed` (simulating stale takeover), then attempt a write checkpoint using the old `job_id`; assert the fencing read detects `status != 'running'` and the write is aborted without persisting any data
- **Ingestion retry recovery — worker crash:** Simulate a hard crash by leaving a `running` row with a `locked_at` timestamp 20 minutes in the past (no heartbeat updates); assert the atomic takeover `UPDATE` matches exactly 1 row, the old row is marked `failed`, and the new attempt completes successfully
- **Long-running ingestion not falsely evicted:** Simulate a legitimately long ingestion by inserting a `running` row with `locked_at` updated 14 minutes ago (just under the threshold); assert that a concurrent Beat trigger does not evict it — the atomic takeover `UPDATE` matches 0 rows and the trigger aborts silently
- **Retry-gap race:** Simulate Celery Beat firing between the moment a job is marked `retrying` and the retry execution; assert Beat aborts rather than starting a duplicate run — confirming `retrying` is covered by the partial unique index
- **Stale takeover atomicity — crash between UPDATE and INSERT:** Simulate a transaction rollback after the stale row is marked `failed` but before the replacement INSERT commits; assert the old row reverts to `running`/`retrying` (no gap left), and the next fresh-start attempt successfully completes the takeover
- **Concurrent stale takeover race:** Simulate two fresh-start triggers simultaneously detecting the same stale row; assert only one acquires the lock via `SELECT FOR UPDATE` and inserts the replacement, and the other aborts cleanly without inserting a duplicate `running` row
- **Stale takeover + pending-row repair while evicted worker resumes:** Simulate worker A (job_id=100) that commits a `pending` document row then is evicted by a stale takeover marking job 100 as `failed`; let worker B (job_id=101) run the pending-row repair fenced delete scoped to `ingestion_job_id=100`; then resume worker A and attempt its next write checkpoint; assert worker A's fencing read detects `status='failed'` and aborts all writes without persisting any data, and that worker B completes with a `complete` document row linked to job 101
- **Corpus version increments exactly once per document, not per job:** Run a full ingestion of one file; read `corpus_version` before and after; assert it incremented by exactly 1. Then run the same ingestion again (hash skip fires — `complete` match); assert `corpus_version` did not increment. This pins the invariant that `corpus_version` advances in Commit 2 and nowhere else.
- **Pending-row repair deletes by primary key + stale job ID, not by hash:** Insert a `pending` document row owned by job_id=100; start a new job (job_id=101); assert the Commit 1 transaction acquires `FOR UPDATE` on the pending row; assert the DELETE predicate targets `documents.id` and `ingestion_job_id=100`, not `(source_id, content_hash)` alone; assert the new INSERT and DELETE are committed in the same transaction
- **Concurrent pending-row repair race — only one job claims the document version:** Insert a stale `pending` row owned by job_id=100; simulate two concurrent jobs (job_id=101 and job_id=102) both entering Commit 1 for the same `(source_id, content_hash)`; assert that `SELECT FOR UPDATE` serializes them — only one acquires the lock and proceeds, the other either blocks until the first commits then finds a `complete` or new `pending` row and aborts cleanly, or receives a unique constraint violation on INSERT and aborts without surfacing a failure; assert no duplicate document rows exist and no unique constraint error propagates as a job failure

**6.3 — Demo Scenario Rehearsal**  
Define and rehearse the exact 5-step demo that will be run in every interview. Practice until it runs in under 3 minutes without notes:
1. Ask "What is our refund policy?" in the chat UI — answer cites both docs, flags the contradiction, names the current policy as authoritative
2. Ask "Who handles VIP customer escalations?" — answer draws from the escalation matrix and VIP handling document
3. Switch to the dashboard — show the task extracted from the enterprise proposal thread
4. Click the task — show the context panel opening with relevant chunks already attached
5. Open the ingestion dashboard — trigger a manual sync, show the new job appearing in the job history in real time

**6.4 — README**  
Write a professional README. Required sections: 2–3 sentence project description explaining what makes it technically interesting, architecture diagram embedded as an image, tech stack table with every technology and one sentence explaining why it was chosen, step-by-step quick start from `git clone` to a running demo, demo login credentials for the pre-seeded user, and a key design decisions section covering the two-pipeline architecture, the Celery/Redis v1 choice, and the migration path to AWS SQS in v2. That last point — documenting the migration path without having done it — demonstrates architectural maturity and will come up in interviews.

**6.5 — Architecture Diagram**  
Create and commit `docs/architecture.png`. Show both pipelines (brain queue and personal queue), all services, the data flow from raw files to the chat UI and dashboard, and the PIL's dependency on the Brain Query API. This diagram is the fastest way to communicate the design to an interviewer.

**6.6 — Cloud Deployment**  
Deploy using the following AWS service mapping:

| Local (Docker Compose) | AWS |
|---|---|
| `api` container | ECS Fargate task |
| `worker` container | ECS Fargate task (separate task definition) |
| `beat` container | ECS Fargate task (separate task definition) |
| PostgreSQL container | RDS PostgreSQL 15 with pgvector extension |
| Redis container | ElastiCache Redis 7 |
| React frontend | S3 bucket + CloudFront distribution |
| `.env` file | AWS Secrets Manager |

The container images do not change between local and cloud. Push them to ECR. Wire ECS task definitions to pull from ECR and inject secrets from Secrets Manager as environment variables.

**6.7 — Pre-Demo Validation Checklist**  
Before every demo session: start all services, trigger a full ingestion sync, verify all jobs completed successfully, run the 5-step demo scenario once end to end, confirm all PIL tasks are loaded and context bundles populated.

### Definition of Done
- `pytest` passes all 6 test categories
- The 5-step demo scenario runs without errors in under 3 minutes
- README is complete with architecture diagram and tech stack table
- System is accessible at a live public URL
- All API errors return the standardized JSON error shape
- No unhandled exceptions appear in Docker logs after a full demo run
- You can explain every technical decision without notes

---

## Cross-Cutting Concerns

### Security
- Never commit `.env` or any file containing real credentials. Enforce this in `.gitignore` from Phase 1.
- Authentication (JWT validity) and authorization (role check) are separate concerns implemented as separate FastAPI dependencies. Never conflate them.
- All non-auth endpoints require a valid JWT. Ingestion endpoints additionally require the `admin` role. No exceptions.
- Never pass JWT tokens in WebSocket URL query parameters. Use the `Sec-WebSocket-Protocol` header or in-message token exchange.
- Every personal task query and mutation must filter by both `tasks.id` and `tasks.user_id == current_user.id` at the database layer. Return 404 on mismatch — not 403. Never fetch by ID alone and check ownership afterward in application code.
- Validate all user inputs at API boundaries. Do not pass raw user input directly to database queries or Claude prompts without sanitization.

### Cost Management
- Use `claude-haiku` for all batch background processing (knowledge extraction, task extraction, context bundling).
- Use `claude-sonnet` only for interactive chat.
- The Redis query cache (5-minute TTL) is the primary cost control during demos. The same questions asked repeatedly during an interview will hit cache after the first call.
- Batch all Voyage AI embedding calls. The SDK supports up to 128 texts per request — never send one request per chunk.
- Voyage AI and Anthropic are billed separately. Track both API keys and monitor both usage dashboards. Voyage AI embedding costs are typically much lower than Claude generation costs but can accumulate during large ingestion runs.

### Idempotency
- Every ingestion task performs an atomic document-claim transaction (Commit 1) that combines the hash check, optional stale pending-row repair, and new pending row insertion into one `FOR UPDATE`-serialized transaction. A `complete` match means skip. A `pending` match owned by a stale job triggers a DELETE + INSERT in the same transaction. A unique constraint violation on INSERT means a concurrent job claimed the slot — abort cleanly. This eliminates the window that would exist if the repair delete and the new INSERT were in separate transactions.
- Two explicit commit boundaries keep transactions short: Commit 1 is the atomic document claim (fast, no API calls, uses `SELECT FOR UPDATE` for serialization); Commit 2 writes all chunks, embeddings, extracted knowledge, `ingestion_status = 'complete'`, and `corpus_version` atomically. No DB transaction spans an external API call.
- Before each write checkpoint, the worker verifies its job row status with a fencing read inside the same transaction. If `status != 'running'`, abort — the job was evicted by a stale takeover. Every external call (Voyage AI, Claude, DB write) must have an explicit timeout so the stale threshold is enforceable.
- The partial unique index covers `ingestion_jobs (source_id) WHERE status IN ('running', 'retrying')` — both active states. This closes the retry-gap race.
- Three entry algorithms must be kept strictly separate: fresh starts INSERT a new row and enter Algorithm C on a unique-index collision; retry starts UPDATE the specific `retrying` row by `job_id` only, never INSERT, never check for staleness; stale takeovers (Algorithm C) use `SELECT ... FOR UPDATE` on the active job row inside a single transaction, inspect `locked_at` to confirm staleness, then UPDATE the old row to `failed` and INSERT the replacement in the same transaction before committing. An implementation that uses one generic path for all three will either dead-end retries on the unique index or incorrectly evict live jobs. An implementation that does Algorithm C with a conditional UPDATE alone (without `SELECT FOR UPDATE`) cannot safely inspect `locked_at` before deciding to evict.
- The `job_id` must be forwarded through `self.retry(kwargs={'job_id': ...})` so every retry invocation knows it is a retry and uses the correct entry algorithm.
- The worker refreshes `locked_at` at each pipeline checkpoint. The stale threshold must be calibrated against the maximum single-checkpoint duration, not total job time. Never read `locked_at` in one transaction and then act on it in a separate transaction — the heartbeat can advance between the two, making the staleness judgment incorrect. Algorithm C avoids this by reading `locked_at` with `SELECT FOR UPDATE` and writing the eviction in the same transaction; the lock prevents any heartbeat update from slipping in between the read and the write.
- Database `UNIQUE` constraints on `documents (source_id, content_hash)` and `tasks (user_id, source_reference)` are the last line of defense against duplicates. Application-level checks reduce load; database constraints prevent corruption.
- The `corpus_version` counter is incremented exactly once per successfully committed document, inside Commit 2. It is not incremented at job success. Cache invalidation is implicit — no explicit key tracking or deletion loops. One increment point prevents the double-invalidation that would arise if the counter also advanced at job success.

### Logging
- Log at INFO level: task start/end, ingestion job status changes, cache hits.
- Log at ERROR level: Claude API failures, database errors, unhandled exceptions.
- All Celery task failures must log the full error message before retrying.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Anthropic (Claude) rate limits during bulk extraction | Medium | High | Use claude-haiku for all batch extraction; add exponential backoff on rate limit errors; run initial ingestion off-peak |
| Voyage AI rate limits during bulk embedding | Low | High | Batch up to 128 texts per call; add exponential backoff on 429 responses; Voyage AI limits are generous for this dataset size |
| Wrong vector dimension in pgvector schema | Low | High | voyage-3 produces 1024-dimension vectors — declare `Vector(1024)` in the migration; a mismatch silently corrupts similarity scores or raises a schema error at insert time |
| pgvector HNSW index missing, causing slow queries | Medium | High | Create index as part of the Phase 3 Alembic migration, not as a manual post-migration step |
| Contradiction detection fails to appear in RAG answer | Medium | High | Validate the RAG prompt produces contradiction language on seeded data in Phase 4 before advancing to Phase 5 |
| Celery Beat or manual trigger fires during retry window, causing duplicate run | Low | Medium | Partial unique index covers both `running` and `retrying` states — any concurrent attempt is rejected while a retry is pending |
| Worker crash orphans `running`/`retrying` row, blocking source | Low | High | Worker heartbeats `locked_at` at each checkpoint; stale takeover (Algorithm C) uses `SELECT FOR UPDATE` + transactional retire-and-replace; rollback on failure reverts old row to active state — no permanent block |
| Stale takeover leaves source slot unguarded between retiring old row and inserting new one | Low | High | Algorithm C wraps `UPDATE SET failed` and replacement `INSERT` in one transaction; `SELECT FOR UPDATE` serializes concurrent takeovers; slot is never dropped without an atomic replacement |
| Long-running legitimate job falsely evicted as stale | Low | High | Heartbeat at each checkpoint keeps `locked_at` fresh; stale threshold set larger than max single-checkpoint duration; test asserts 14-minute-old row is not evicted |
| Evicted worker resumes and writes concurrently with new worker | Low | High | Fencing check inside each write transaction reads job status; if `status != 'running'` for this `job_id`, abort all writes — evicted worker cannot corrupt the corpus |
| DB transaction spans an external API call, holding locks during network latency | Low | Medium | No transaction may open across a Voyage AI or Claude API call; all API results held in memory between Commit 1 and Commit 2 |
| Authenticated user reads or mutates another user's task via ID enumeration | Low | High | All personal task queries filter by both `id` and `user_id == current_user.id` at the database layer; mismatch returns 404 |
| Duplicate documents/chunks from concurrent ingestion paths | Low | High | `UNIQUE (source_id, content_hash)` constraint on `documents`; content hash check before processing |
| Crashed run leaves `pending` document that hash-skip treats as complete, silently dropping chunks/embeddings | Low | High | Hash skip checks `ingestion_status = 'complete'`; `pending` match triggers delete-and-reprocess, not skip |
| Pending-row repair delete removes a row owned by a concurrent or resumed job, not the stale job | Low | High | Repair delete targets `documents.id` (primary key) plus `ingestion_job_id=:stale_job_id`; deletion runs inside the same Commit 1 transaction as the new INSERT; `SELECT FOR UPDATE` serializes concurrent repair attempts |
| Two concurrent jobs race through separate repair-delete and Commit-1 transactions, one failing on UNIQUE constraint | Low | High | Repair delete and new pending INSERT are merged into one atomic transaction; `SELECT FOR UPDATE` on existing row serializes concurrent access; unique constraint violation on INSERT (no-row race) is caught and treated as clean abort, not a job failure |
| `corpus_version` incremented at both Commit 2 (per document) and job success, causing double cache invalidation | Low | High | Counter is incremented exactly once per document inside Commit 2; the job-level `success` transition does not touch the counter |
| Stale cached answers served after ingestion (especially refund policy scenario) | Medium | High | Corpus version counter incremented in the same transaction as document commit; version is part of every cache key |
| Any authenticated user triggers unbounded ingestion and Claude API calls | Medium | High | `require_admin` dependency on all ingestion endpoints; role column in `users` table |
| JWT token leaked via WebSocket URL query parameter | Low | High | Use `Sec-WebSocket-Protocol` header or first-message token exchange; never put token in query string |
| JWT secret committed to git | Low | High | `.gitignore` enforced from Phase 1; secret rotation if ever accidentally exposed |
| WebSocket disconnects during long Claude streaming responses | Medium | Medium | Implement reconnect logic in the frontend WebSocket hook |
| Context bundle not populated when user clicks task | Low | Medium | Bundler runs as an immediate follow-up task; dashboard shows loading indicator while bundle is pending |
| Cloud deployment costs exceed expectations | Low | Medium | Use Fargate Spot for worker and beat tasks; set RDS and ElastiCache to smallest viable instance sizes |

---

## Definition of "Done" — Principles

A phase is complete when:

1. The demo scenario specific to that phase executes without errors
2. All changes are committed to git with clear commit messages
3. You can explain every decision made in that phase without reading notes

Do not carry broken behavior forward between phases. A broken chunker in Phase 3 breaks every downstream test in Phases 4, 5, and 6. Fix it before advancing.
