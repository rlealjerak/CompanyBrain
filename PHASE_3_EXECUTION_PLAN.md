# Phase 3 — Ingestion and Processing Pipeline
## Execution Plan

**Project:** Company Brain  
**Phase:** 3 of 6  
**Prerequisite:** Phase 2 complete — all synthetic data files committed to `data/raw/`  
**Outcome:** Every file in `data/raw/` is fully ingested. Documents, chunks, embeddings, and extracted knowledge are in PostgreSQL. The ingestion job history shows `success` for every source. The system is safe under concurrent triggers, worker crashes, and retries.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Task 3.1 — Database Schema and Migrations](#2-task-31--database-schema-and-migrations)
3. [Task 3.2 — Connector Interface](#3-task-32--connector-interface)
4. [Task 3.3 — File Connectors](#4-task-33--file-connectors)
5. [Task 3.4 — Chunker](#5-task-34--chunker)
6. [Task 3.5 — Embedder](#6-task-35--embedder)
7. [Task 3.6 — Knowledge Extractor](#7-task-36--knowledge-extractor)
8. [Task 3.7 — Celery Configuration](#8-task-37--celery-configuration)
9. [Task 3.8 — Job State Machine](#9-task-38--job-state-machine)
10. [Task 3.9 — Idempotency and Concurrency Safety](#10-task-39--idempotency-and-concurrency-safety)
11. [Test Requirements](#11-test-requirements)
12. [Definition of Done](#12-definition-of-done)

---

## 1. Architecture Overview

Phase 3 introduces the `brain` Celery queue, which is responsible for reading raw files, processing them through the pipeline, and populating the vector database. The pipeline is a linear sequence:

```
Raw file → Connector → Chunker → Embedder (Voyage AI) → Extractor (Claude) → PostgreSQL
```

Each file is processed by a single Celery task. The task is governed by a job state machine stored in the `ingestion_jobs` table. The state machine is designed to be safe under three failure modes that occur in production: caught exceptions (handled via retry), unhandled worker crashes (recovered via heartbeat staleness detection), and concurrent triggers (serialized via a partial unique index and row-level locking).

**Key design constraints that apply throughout this phase:**

- No database transaction may span an external API call (Voyage AI or Claude). All API results are held in memory between the two explicit commit boundaries.
- Every write checkpoint is fenced: the worker verifies its job is still active before writing.
- The `corpus_version` counter is the cache invalidation mechanism. It is incremented exactly once per document, inside Commit 2. It is never incremented at job success.
- No JWT or credential may be committed to git. All secrets are injected via environment variables.

---

## 2. Task 3.1 — Database Schema and Migrations

**Implement before any pipeline code is written.** Create all tables in a single Alembic migration now — including tables not used until Phase 5 — to avoid disruptive schema changes later. A schema change after ingestion data exists requires a migration, re-indexing, and potentially re-ingestion.

### Tables

**`ingestion_jobs`**

Tracks every sync run. Required columns:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `source_id` | TEXT NOT NULL | The file's canonical identifier |
| `status` | TEXT NOT NULL | Values: `running`, `retrying`, `success`, `failed` |
| `locked_at` | TIMESTAMPTZ NOT NULL | Set at entry; refreshed as a heartbeat after each pipeline checkpoint |
| `attempt_number` | INT NOT NULL | Incremented on every retry |
| `error_message` | TEXT | Populated on final failure |
| `created_at` | TIMESTAMPTZ NOT NULL | |

Add a **partial unique index** on `(source_id) WHERE status IN ('running', 'retrying')`. This ensures at most one active job row can exist per source at any time, across both the `running` and `retrying` states. Covering both states closes the retry-gap race: Beat cannot start a duplicate run while a retry is pending.

**Why this index works for Algorithm C (stale takeover):** PostgreSQL evaluates non-deferrable unique constraint violations at the end of each SQL statement, not at end-of-transaction. When Algorithm C's UPDATE changes the old row to `status='failed'`, it is removed from the partial index predicate before the replacement INSERT fires. This means UPDATE-then-INSERT within one transaction is safe without a deferrable constraint. The order is load-bearing — INSERT before UPDATE would fail. Never reverse the order; never split the two statements across separate transactions.

---

**`documents`**

Stores one row per file version. Required columns:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `source_id` | TEXT NOT NULL | |
| `content_hash` | TEXT NOT NULL | SHA-256 of raw file content |
| `source_mtime` | TIMESTAMPTZ | File modification time at time of ingestion |
| `ingestion_status` | TEXT NOT NULL | Values: `pending`, `complete` |
| `ingestion_job_id` | UUID, FK → `ingestion_jobs.id` | The job that currently owns this row |
| `raw_content` | TEXT | Full raw text |
| `extracted_knowledge` | JSONB | Output from the Claude extractor |
| `source_quality_score` | INT | 1–5; set by the extractor |
| `created_at` | TIMESTAMPTZ NOT NULL | |

Add `UNIQUE (source_id, content_hash)`. At most one row per file version may exist at any time.

The `ingestion_job_id` column is critical for the repair protocol: it scopes every ownership check and claim operation to a specific job, not just a file version. Without it, concurrent repair attempts cannot distinguish which job owns a pending row.

The `ingestion_status` column is the completeness gate. The hash-skip check must only treat `complete` rows as fully ingested. A `pending` row with a matching hash means a prior job crashed mid-pipeline and left partial state.

---

**`chunks`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `document_id` | UUID, FK → `documents.id` ON DELETE CASCADE | |
| `chunk_index` | INT NOT NULL | Position within the parent document |
| `text` | TEXT NOT NULL | |
| `token_count` | INT NOT NULL | |

---

**`embeddings`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `chunk_id` | UUID, FK → `chunks.id` ON DELETE CASCADE | |
| `document_id` | UUID, FK → `documents.id` | Denormalized for query efficiency |
| `source_id` | TEXT NOT NULL | Denormalized for filtering |
| `source_type` | TEXT NOT NULL | |
| `chunk_index` | INT NOT NULL | |
| `vector` | VECTOR(1024) NOT NULL | Must be exactly 1024 — the `voyage-3` output dimension |
| `created_at` | TIMESTAMPTZ NOT NULL | Used for recency-based reranking |

The vector dimension must be declared as `VECTOR(1024)`. Declaring the wrong dimension silently corrupts similarity scores or raises a schema error at insert time. Setting it correctly now avoids a full re-migration and re-ingestion later.

Create the HNSW index on the vector column in the same migration. Do not leave it as a manual step — unindexed vector search is a full-table scan that will time out on any non-trivial dataset.

---

**`users`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `email` | TEXT NOT NULL UNIQUE | |
| `hashed_password` | TEXT NOT NULL | |
| `role` | TEXT NOT NULL | Values: `user`, `admin` |

Seed at least one admin user in the initial migration. Ingestion endpoints require the `admin` role.

---

**`tasks`** *(used by Phase 5, created now)*

| Column | Type | Notes |
|---|---|---|
| `id` | UUID, PK | |
| `user_id` | UUID, FK → `users.id` | |
| `description` | TEXT NOT NULL | |
| `urgency_score` | FLOAT | Range 1–10; matches Phase 5 scorer output |
| `urgency_band` | TEXT | Values: `high` (8–10), `medium` (5–7), `low` (1–4) |
| `status` | TEXT NOT NULL | Values: `open`, `complete`, `snoozed`, `dismissed` |
| `deadline` | TIMESTAMPTZ | |
| `context_bundle` | JSONB | Pre-fetched relevant chunks |
| `source_reference` | TEXT NOT NULL | Namespaced source ID (see below) |

`source_reference` format: `slack:{thread_ts}`, `email:{message_id}`, `ticket:{ticket_id}`. The namespace prefix prevents cross-source collisions. This field must be populated before every INSERT — a missing value is a pipeline bug, not a nullable edge case.

Add `UNIQUE (user_id, source_reference)` to prevent duplicate task extraction from the same source message across retries and repeated scans.

---

**`corpus_version`**

A single-row table with one INTEGER column. Incremented inside Commit 2 — the same transaction that marks a document `complete`. This is the only place the counter advances. The job-level `success` transition must not touch it. One increment per successfully committed document, not once per job.

---

### Migration checklist

- [ ] All tables created in a single initial migration
- [ ] HNSW index on `embeddings.vector` created in the same migration
- [ ] Partial unique index on `ingestion_jobs(source_id) WHERE status IN ('running', 'retrying')`
- [ ] `UNIQUE (source_id, content_hash)` on `documents`
- [ ] `UNIQUE (user_id, source_reference)` on `tasks`
- [ ] `corpus_version` seeded with value `0`
- [ ] At least one admin user seeded
- [ ] Migration verified to run cleanly against a fresh PostgreSQL container

---

## 3. Task 3.2 — Connector Interface

**File:** `app/connectors/base.py`

Define an abstract `BaseConnector` class and a `Document` dataclass. Every connector, regardless of source format, must output a list of `Document` objects. The pipeline code never handles raw files — it only receives `Document` objects. This contract is the extensibility boundary.

**`Document` fields:**

| Field | Type | Notes |
|---|---|---|
| `raw_content` | str | Full raw text of the document |
| `source_id` | str | Stable identifier for this file (e.g. relative file path) |
| `source_name` | str | Human-readable name |
| `author` | str | |
| `timestamp` | datetime | Creation or last-modified time of the source |
| `content_type` | str | Values: `policy`, `slack`, `email`, `ticket`, `reference` |
| `metadata` | dict | Any extra fields the connector wants to carry through |

**`BaseConnector` interface:** a single abstract method that accepts a file path and returns `list[Document]`.

---

## 4. Task 3.3 — File Connectors

**File:** `app/connectors/`

Implement two connector classes:

**`MarkdownConnector`** — reads `.md` files. Returns one `Document` per file. Sets `content_type = 'policy'`.

**`JsonConnector`** — reads `.json` files. Used for three source types with different schemas:

- **Slack threads** — array-of-messages schema; one `Document` per thread file
- **Email chains** — array-of-messages schema; one `Document` per chain file
- **Support tickets** — flat-object schema; one `Document` per ticket

Support tickets are generated as JSON in Phase 2. A `CsvConnector` must not be implemented — it would silently exclude the entire support-ticket corpus from ingestion. The `JsonConnector` must accept a configurable field mapping at construction time to handle both the array-of-messages and flat-object schemas without branching in the pipeline.

Each connector must validate that its output `Document` objects have non-empty `source_id`, `raw_content`, and `timestamp` before returning. A connector that silently produces empty documents is harder to debug than one that fails fast.

---

## 5. Task 3.4 — Chunker

**File:** `app/pipeline/chunker.py`

Chunk parameters:

| Parameter | Value | Rationale |
|---|---|---|
| Chunk size | 512 tokens | Balances retrieval granularity against context completeness |
| Overlap | 50 tokens | Prevents context loss at chunk boundaries |
| Measurement | tiktoken | Must use the same tokenizer consistently across pipeline |
| Split boundary | Sentence | Never cut mid-sentence |

Each chunk output must carry: its index within the parent document, its token count, and a reference to the parent `Document`. The token count is stored in the database and used later for prompt budget management.

---

## 6. Task 3.5 — Embedder

**File:** `app/pipeline/embedder.py`

Use the **Voyage AI SDK** (`voyageai` Python package). The Anthropic Claude API is generation-only and has no embeddings endpoint — any implementation that calls the Anthropic SDK for embeddings will fail at runtime.

| Parameter | Value |
|---|---|
| Model | `voyage-3` |
| Vector dimension | 1024 |
| Batch size | Up to 128 texts per request |
| Environment variable | `VOYAGE_API_KEY` |

Batch all embedding calls. Sending one request per chunk is dramatically slower and more expensive than batching. The SDK supports batches of up to 128 texts.

Add a startup check that fails fast with a clear error message if `VOYAGE_API_KEY` or `ANTHROPIC_API_KEY` is missing. A missing key that surfaces only during the first ingestion run wastes a full pipeline execution before failing.

Store the resulting vectors with full metadata: `source_id`, `source_type`, `document_id`, `chunk_index`, and `created_at`. The `created_at` timestamp is the recency signal used in Phase 4's reranking step to resolve contradictions between sources.

---

## 7. Task 3.6 — Knowledge Extractor

**File:** `app/pipeline/extractor.py`

Send the full document text (not individual chunks) to `claude-haiku` with a structured extraction prompt. Use `claude-haiku` for all batch extraction — it is substantially cheaper than Sonnet and sufficient for structured JSON output. The extraction prompt must specify the exact JSON schema to return:

- Key entities: people, teams, products, systems
- Key factual statements and policies
- Rules and procedures
- Relationships between entities
- Source quality score (1–5): how authoritative the document appears

Store the resulting JSON in `documents.extracted_knowledge` and the quality score in `documents.source_quality_score`. Both are written in Commit 2.

The extraction call must have an explicit timeout. If Claude does not respond within the timeout, treat it as a retryable failure and transition the job to `retrying`.

---

## 8. Task 3.7 — Celery Configuration

**File:** `app/celery_app.py`

Define two named queues:

| Queue | Purpose | Worker concurrency |
|---|---|---|
| `brain` | Company Brain ingestion tasks | Configurable; default 4 |
| `personal` | PIL task extraction (Phase 5) | Configurable; default 2 |

Both queues share the same Redis broker. Separate worker concurrency prevents ingestion from starving PIL tasks and vice versa.

Configure Celery Beat to scan `data/raw/` every 5 minutes. For each file found, check if a recent successful ingestion exists. If not, dispatch an ingestion task to the `brain` queue. This is the trigger for Entry Algorithm A (fresh start).

Set retry policy for ingestion tasks: maximum 3 attempts, exponential backoff starting at 30 seconds. Configure `task_acks_late = True` so that a worker crash does not silently drop a task — the task remains in the queue until the worker explicitly acknowledges it.

---

## 9. Task 3.8 — Job State Machine

**File:** `app/tasks/brain_tasks.py`

The ingestion job follows an explicit four-state machine. Every state transition is a deliberate, guarded operation — there is no implicit or ambient state change.

### State diagram

```
(trigger)
    │
    ▼
 running ──────────────────────────────────────────► success
    │                                                    ▲
    │ retryable exception                                │
    ▼                                              Commit 2 + success
 retrying                                          transition
    │
    │ retry invocation (Algorithm B)
    ▼
 running ──── max retries exceeded ──────────────► failed
                                              also: stale takeover
                                              marks old job failed
```

### Three entry algorithms

There are three distinct paths into a running ingestion job. They must never be conflated. An implementation that uses a single generic path for all three will either dead-end retries on the unique index or incorrectly evict live jobs.

---

#### Entry Algorithm A — Fresh start

*Triggered by: Celery Beat scan or manual API trigger. No `job_id` in task kwargs.*

1. Attempt `INSERT INTO ingestion_jobs (..., status='running', locked_at=now(), attempt_number=1)`.
   - If the INSERT succeeds: the source slot is acquired. Proceed to the pipeline.
   - If the INSERT is rejected by the partial unique index: an active row already exists for this source. Proceed to Algorithm C.
2. Forward the acquired `job_id` to all retry invocations via `self.retry(kwargs={'job_id': job.id, ...})`. This is what enables Algorithm B.

---

#### Entry Algorithm B — Retry start

*Triggered by: Celery retry mechanism. `job_id` is present in task kwargs.*

1. Do **not** INSERT. Do **not** run the stale-lock check.
2. `UPDATE ingestion_jobs SET status='running', locked_at=now(), attempt_number=attempt_number+1 WHERE id=:job_id AND status='retrying'`.
3. Check affected row count:
   - **1 row affected:** The transition succeeded. Proceed to the pipeline.
   - **0 rows affected:** The row was taken over by a stale-lock recovery between retry scheduling and this execution. Abort silently — do not proceed.

This is the only path by which a `retrying` row transitions back to `running`. It is keyed on `job_id`, not `source_id`, so it cannot collide with the partial unique index.

---

#### Entry Algorithm C — Stale Takeover Transaction

*Triggered by: Algorithm A when its INSERT is rejected by the unique index.*

All steps run inside a single database transaction. `SELECT FOR UPDATE` serializes concurrent takeover attempts — only one caller can proceed; all others block and re-evaluate after the lock is released.

1. `SELECT id, locked_at FROM ingestion_jobs WHERE source_id=:sid AND status IN ('running','retrying') FOR UPDATE`.
   - If no row is returned (the prior job completed between Algorithm A's failed INSERT and now): rollback and retry Algorithm A step 1.
2. Inspect `locked_at`. If less than 15 minutes old, the job is still live — rollback, abort silently.
3. If stale, execute in this exact order within the same open transaction:
   - `UPDATE ingestion_jobs SET status='failed', error_message='evicted: stale' WHERE id=:existing_id`
   - `INSERT INTO ingestion_jobs (..., status='running', locked_at=now(), attempt_number=1)`
   - COMMIT

   **PostgreSQL constraint note:** The UPDATE removes the old row from the partial index predicate (`WHERE status IN ('running','retrying')`) before the INSERT's constraint check fires. No deferrable constraint is needed. The order is load-bearing — INSERT before UPDATE fails. Never reverse the order and never split these two statements across separate transactions.

4. If the transaction fails for any reason: rollback. The old row reverts to its prior active state. Abort — do not retry the takeover.

---

### Heartbeat requirement

The worker must update `locked_at = now()` after each major checkpoint: file load, chunking complete, embedding API response received, Claude extraction response received, Commit 2 complete. The stale threshold (15 minutes) must exceed the maximum expected duration of any single checkpoint. Document the chosen threshold value and its basis alongside the configuration.

Never read `locked_at` in one transaction and act on it in a separate transaction — the heartbeat can advance between the two, making the staleness judgment incorrect. Algorithm C avoids this by reading `locked_at` with `SELECT FOR UPDATE` and writing the eviction in the same transaction.

---

### Bounded checkpoint timeouts

Every external call must have an explicit timeout:

| Checkpoint | Timeout |
|---|---|
| Voyage AI embedding API | 60 seconds |
| Claude extraction API | 120 seconds |
| Database write (Commit 1) | 10 seconds |
| Database write (Commit 2) | 30 seconds |

If any checkpoint exceeds its timeout, treat it as a retryable failure. This makes the stale threshold enforceable — a worker that is genuinely stuck stops heartbeating within a bounded time rather than hanging indefinitely.

---

### Fencing requirement

Before every write checkpoint — Commit 1, Commit 2, and every `locked_at` heartbeat update — the worker must verify its job row is still active. Include `SELECT status FROM ingestion_jobs WHERE id=:job_id` inside the same transaction as the write it guards. If `status != 'running'`, the worker has been evicted — rollback, abort all further writes without error.

The fencing check must be inside the same transaction as the write, not as a preceding standalone query. A standalone read-then-write has a race: another session can evict the job between the read and the write.

---

### State transitions on exception and completion

| Condition | Action |
|---|---|
| Caught retryable exception | Transition to `retrying`, call `self.retry(kwargs={'job_id': ...})` |
| Worker crash (no cleanup) | Row stays `running`/`retrying` with stale `locked_at`; Algorithm A recovers it |
| Max retries exceeded | Transition to `failed` with error message |
| Success | Transition to `success`; do **not** increment `corpus_version` here |

---

## 10. Task 3.9 — Idempotency and Concurrency Safety

The pipeline uses two explicit commit boundaries. No transaction ever spans an external API call.

---

### Commit 1 — Atomic document claim

The hash check and document row ownership are performed in a single transaction. They must never be split. `SELECT FOR UPDATE` only locks rows that already exist — a plain SELECT-then-INSERT leaves a window where two concurrent fresh jobs both find no row and race to INSERT. To close this gap, the INSERT is attempted first; the SELECT FOR UPDATE is only used when the INSERT conflicts and a row already exists.

**All steps run inside one transaction:**

**Step 1 — Fencing check**  
`SELECT status FROM ingestion_jobs WHERE id=:current_job_id`. If `status != 'running'`, rollback, abort.

**Step 2 — Attempt atomic first claim**  
`INSERT INTO documents (..., ingestion_status='pending', ingestion_job_id=:current_job_id) ON CONFLICT (source_id, content_hash) DO NOTHING RETURNING id`

- **INSERT returned a row:** This job atomically owns the new `pending` row. No concurrent job can claim the same `(source_id, content_hash)`. Proceed to Step 6 (COMMIT).
- **INSERT returned nothing:** A row already exists. Proceed to Step 3.

**Step 3 — Lock existing row**  
*(Reached only when INSERT conflicted.)*  
`SELECT id, ingestion_job_id, ingestion_status FROM documents WHERE source_id=:sid AND content_hash=:hash FOR UPDATE`  
`FOR UPDATE` now has a row to lock, serializing any other concurrent attempt that also reached this step.

**Step 4 — Re-fence and branch**  
Re-run fencing check inside the same transaction. Branch on the locked row:

- **`complete` row:** Fully ingested — rollback, skip. No work needed.

- **`pending` row, `ingestion_job_id` matches current job:** This is a retry — the job already owns this pending row from a prior attempt. Rollback the Commit 1 transaction and proceed directly to the pipeline steps. No claim action needed.

- **`pending` row, `ingestion_job_id` differs from current job:** A prior job created this row. Before claiming, verify that prior job is actually terminal:  
  `SELECT status, locked_at FROM ingestion_jobs WHERE id=:owner_job_id`
  - If `status IN ('running', 'retrying')` AND `locked_at > now() - 15 minutes`: the owner is still live. Rollback, abort cleanly — the live job will complete this document.
  - If `status IN ('failed', 'success')` OR `locked_at <= now() - 15 minutes`: the owner is terminal or stale. Claim in-place: `UPDATE documents SET ingestion_job_id=:current_job_id WHERE id=:doc_id AND ingestion_job_id=:owner_job_id`. Because Commit 2 is fully atomic, the stale pending row has no children. Proceed to Step 5.
  - Never DELETE and re-INSERT the same `(source_id, content_hash)` key.

**Step 5 — COMMIT**  
The pending row is now owned by the current job and visible to recovery code.

---

### Pipeline steps — no database writes

Run in memory after Commit 1 commits:

1. Load raw content from the `Document` object
2. Chunk the content using the chunker (in-memory, no DB writes)
3. Call the Voyage AI embedding API (batch all chunks in one or more requests)
4. Call the Claude extraction API (full document text, single request)
5. Hold all results in memory

No database transaction is open during steps 3 or 4. No lock is held. If either API call fails, treat it as a retryable failure.

---

### Commit 2 — Atomic document completion

All writes in a single transaction:

1. Fencing check: `SELECT status FROM ingestion_jobs WHERE id=:current_job_id`. If `status != 'running'`, rollback, abort.
2. Insert all chunks into `chunks`.
3. Insert all embedding vectors into `embeddings`.
4. Update the document: `UPDATE documents SET ingestion_status='complete', extracted_knowledge=:knowledge, source_quality_score=:score WHERE id=:doc_id AND ingestion_job_id=:current_job_id AND ingestion_status='pending'`.  
   Check affected row count:
   - **1 row affected:** Proceed.
   - **0 rows affected:** Another job has taken ownership of this document (or it was already completed). Rollback, abort. Do not surface this as a job failure — it is a clean abort.
5. Increment `corpus_version`: `UPDATE corpus_version SET version = version + 1`.
6. COMMIT.

The `WHERE ingestion_job_id=:current_job_id AND ingestion_status='pending'` predicate in step 4 is the ownership verification. It ensures that even if an evicted worker somehow reaches Commit 2 after its fencing check, it cannot overwrite a document claimed by a live job.

---

### Crash recovery paths

| Crash point | Row state after crash | Recovery on next run |
|---|---|---|
| Before Commit 1 commits | No document row | Commit 1's INSERT ON CONFLICT succeeds; proceeds normally |
| Between Commit 1 and Commit 2 | `pending` row, no children | Commit 1 INSERT conflicts; SELECT FOR UPDATE locks the row; owner job is terminal or stale; UPDATE-in-place claims the row; Commit 2 completes it |
| During Commit 2 (rolled back) | `pending` row, no children (Commit 2 is atomic) | Same as above |

---

## 11. Test Requirements

Tests must run against a real PostgreSQL instance using the actual Alembic migration — not an in-memory database or mocked schema. The concurrency model depends on PostgreSQL-specific constraint evaluation behavior.

### Functional correctness

- **Chunker:** Given a document of known token count, assert the correct number of chunks are produced with the correct overlap preserved.
- **Embedder batching:** Assert that a document with more than 128 chunks results in multiple batched Voyage AI requests, not one request per chunk.
- **Extraction output shape:** Assert that the Claude extractor returns valid JSON conforming to the expected schema for each content type.

### Idempotency

- **Hash skip fires only on `complete` documents:** Assert that a `pending` document row with a matching `(source_id, content_hash)` is never silently skipped — it must trigger the repair path, not skip.
- **Crash between Commit 1 and Commit 2:** Commit a `pending` document row; run a new ingestion attempt; assert Commit 1 claims the row in-place via UPDATE (not DELETE+INSERT), the primary key is unchanged, Commit 2 completes, and the document ends as `complete`.
- **Transaction rollback leaves recoverable `pending` row:** Force a rollback of Commit 2; assert the `pending` row from Commit 1 survives intact; assert the next run claims it in-place and completes it without a unique constraint violation or duplicate row.
- **Corpus version increments exactly once per document:** Assert `corpus_version` increments by 1 on a successful ingestion; assert it does not increment on a hash-skip (`complete` row found); assert it does not increment on job `success` transition.

### Job state machine

- **Algorithm B does not INSERT or check staleness:** Assert the retry invocation updates exactly 1 row via `WHERE id=:job_id AND status='retrying'` and does not touch the partial unique index.
- **Retry-gap race:** Assert that a Beat trigger firing while a job is `retrying` is rejected by the partial unique index, not silently admitted as a duplicate run.
- **Algorithm C UPDATE-then-INSERT order:** Against the real Alembic migration, run Algorithm C's exact UPDATE-then-INSERT sequence in one transaction; assert it commits without a unique constraint violation; assert the reversed order (INSERT-then-UPDATE) raises a unique constraint violation.
- **Stale takeover atomicity:** Simulate a transaction rollback after the stale row is marked `failed` but before the replacement INSERT commits; assert the old row reverts to `running`/`retrying` (no gap); assert the next fresh-start attempt completes the takeover successfully.
- **Concurrent stale takeover race:** Simulate two fresh-start triggers simultaneously detecting the same stale row; assert only one acquires the `SELECT FOR UPDATE` lock and inserts the replacement; assert the other aborts cleanly without inserting a duplicate `running` row.
- **Long-running legitimate job not falsely evicted:** Insert a `running` row with `locked_at` 14 minutes ago; assert Algorithm C finds it non-stale and aborts without evicting it.

### Fencing and ownership

- **Fencing aborts evicted worker at Commit 1:** Mark a job as `failed`; attempt Commit 1 using the evicted job's ID; assert the fencing check detects `status='failed'` and the transaction is rolled back without writing.
- **Fencing aborts evicted worker at Commit 2:** Proceed past Commit 1 normally; mark the job as `failed` before Commit 2; assert Commit 2's fencing check aborts and the document remains `pending` with no chunks or embeddings.
- **Commit 2 ownership predicate blocks wrong-owner write:** Insert a `pending` row owned by job_id=100; attempt Commit 2 with job_id=101; assert the `WHERE ingestion_job_id=100` predicate causes 0 rows affected; assert Commit 2 rolls back cleanly.
- **Stale takeover + pending-row repair while evicted worker resumes:** Commit a `pending` row owned by job_id=100; evict job 100 via Algorithm C (job_id=101 takes over); worker 101 claims the row via UPDATE-in-place; resume worker 100 and attempt Commit 2; assert worker 100's Commit 2 ownership predicate returns 0 rows affected (row is now owned by 101) and aborts cleanly; assert worker 101 completes with a `complete` row.

### Concurrency — document claim

- **Concurrent first-ingestion of same file version:** Simulate two concurrent fresh jobs for the same `(source_id, content_hash)` with no prior document row; assert the `INSERT ... ON CONFLICT DO NOTHING` serializes them — exactly one INSERT wins; the loser reads the winning row via `SELECT FOR UPDATE` and aborts cleanly; assert exactly one `pending` document row exists.
- **Retry recognizes its own pending row:** Commit a `pending` row owned by job_id=100; simulate a retry (Algorithm B) with the same job_id=100; assert Commit 1's INSERT conflicts, the SELECT FOR UPDATE finds `ingestion_job_id=100` matching the current job, and the retry skips the claim and proceeds directly to the pipeline without modifying the document row.
- **Live-owner abort:** Insert a `pending` row owned by a job whose status is `running` and `locked_at` is recent; simulate a second job reaching Commit 1 step 4; assert the second job reads the owner's job status, finds it live and non-stale, and aborts without modifying `ingestion_job_id`.
- **Pending-row repair claims in-place, never DELETE-then-INSERT:** Insert a `pending` row owned by a `failed` job; run a new ingestion job; assert the repair is an `UPDATE SET ingestion_job_id=:new_job_id` on the existing row, not a DELETE followed by INSERT of the same key; assert the row's primary key is unchanged.

---

## 12. Definition of Done

- [ ] All Alembic migrations run cleanly against a fresh PostgreSQL 15 container with the pgvector extension enabled
- [ ] HNSW index confirmed present via `\d embeddings` in psql
- [ ] Running ingestion against all files in `data/raw/` completes with `status = 'success'` for every source
- [ ] `documents`, `chunks`, and `embeddings` tables are fully populated
- [ ] Both refund policy documents (old 14-day and new 30-day) are in the database with distinct timestamps
- [ ] `corpus_version` has been incremented once per successfully ingested document
- [ ] All test categories listed in Section 11 pass against a real PostgreSQL instance
- [ ] No worker crashes or unhandled exceptions in Docker logs after a full ingestion run
- [ ] Ingestion is idempotent: running the pipeline a second time produces no changes to the database (all files already `complete`, hash-skip fires for all)
- [ ] No `.env` file or API key committed to git
