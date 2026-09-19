# HireView Work Log

---

## 2026-09-08 — Khushi — ~2h
**Phase:** 0 (Foundation)
**Files touched:** entire scaffold, .gitignore, pyproject.toml, uv.lock

**Done:**
- Cloned repo into clean `Projects/HireView-V2` structure
- Created .gitignore (env, venv, db files, IDE clutter)
- Ran `uv init`, removed default main.py
- Created full scaffold (67 files across src/scripts/eval/tests/docs)
- Installed all dependencies via `uv add` — verified with import test, printed "ok"
- All changes committed and pushed in separate, logical commits

**In progress (NOT committed):** none

**Blocked / needs discussion:**
- Supabase project + Groq API key not yet created — needed before scripts/verify_setup.py

**Next session:** create Supabase project + Groq key, then write scripts/verify_setup.py
- Phase 0 done, DB/Groq/embedding all verified

**Phase 1:**
- Starting to work on setting database. 
- Working on Phase 1 schema after making changes to marking scheme,and updated build plan.
- Schema is completed in src/db/models.py ,next working on Alembic.
- field_type has no DB-level validation — store.py must check against VALID_FIELD_TYPES before insert.

## 2026-09-16 — Khushi — Xh
**Phase:** 1 (Database schema) — COMPLETE

**Files touched:** `src/db/models.py`, `src/db/session.py`, `src/db/store.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/51dec81dbef2_initial.py`, `tests/test_db.py`

**Done:**
- `models.py` — all 9 tables finalized (companies, job_postings, candidates, resumes, resume_links, certifications, resume_embeddings, applications, search_logs), verified against the build plan's Phase 1 rules line by line
- Alembic initialized (`migrations/`), `env.py` wired to import `Base.metadata` and read `DATABASE_URL` from `.env` (kept out of `alembic.ini` deliberately — that file is committed, `.env` isn't)
- First migration generated and reviewed before applying — caught and fixed a real bug: autogenerate wrote `pgvector.sqlalchemy.vector.VECTOR(dim=384)` into the `resume_embeddings` table but never imported `pgvector`, which would have crashed `upgrade()` mid-run
- `alembic upgrade head` applied — all 9 tables + Alembic's own `alembic_version` table confirmed live in Supabase
- `store.py` built incrementally: `create_company`, `add_candidate`, `add_resume`, `add_resume_embedding`, `delete_resume`, `get_resume`, `get_resume_embeddings` — every tenant-scoped function filters by `company_id` in the query itself, not just accepts it as an unused argument
- `tests/test_db.py` — all 4 checkpoint tests passing: insert/read-back, cascade delete (confirmed `resume_embeddings` disappears when its resume is deleted, proving `ondelete="CASCADE"` actually works), tenant isolation (wrong `company_id` returns `None` even when the row exists), same email under two companies (proves `UniqueConstraint(company_id, email)` is scoped correctly)

**Decisions/notes for later (not built now):**
- `delete_company` — drafted, deliberately deferred; not needed for Phase 1, useful later for company offboarding (full cascade delete by `company_id`) since every table already cascades from `companies`
- A data-export-by-`company_id` feature was discussed as a future need (GDPR-style "give us our data back") — no schema changes required when it's actually built, just a new `store.py` query
- Supabase project is single-environment (`PRODUCTION` label, free tier) — confirmed this is fine until a real company onboards; second free project for dev/staging planned for around Phase 9


**Blocked / needs discussion:** none

**Next session:** Phase 2 — ingestion pipeline (`src/ingestion/`, `embedder.py`)

---
## 2026-09-19 — Khushi — Xh
**Phase:** 2 (Ingestion pipeline) — COMPLETE

**Files touched:** `src/ingestion/extractor.py`, `src/ingestion/guards.py`, `src/ingestion/sectioner.py`, `src/ingestion/normalizer.py`, `src/ingestion/pipeline.py`, `src/embedding/embedder.py`, `src/schemas/resume.py`, `src/agents/llm_client.py`, `src/db/models.py`, `src/db/store.py`, `src/config.py`, `scripts/ingest.py`, `tests/test_embedding.py`, `migrations/versions/e6a4857912fd_add_skills_column_to_resumes.py`. Deleted: `src/ingestion/years_parser.py`.

**Done:**
- `extractor.py` — PDF → text via PyMuPDF, block-based. Column detection is *adaptive*, not a fixed 50/50 split: finds the largest horizontal gap between block starting-positions on the page, only treats it as a real column boundary if that gap exceeds `COLUMN_GAP_THRESHOLD` (0.15 × page width, a guessed starting value, not empirically tuned). Verified against both single-column and two-column real resumes.
- `guards.py` — `check_size` (10MB), `check_pages` (15), `is_scanned` (<200 extracted chars) — all raise `ValueError` rather than returning bool, so `pipeline.py` fails fast with a clear reason.
- `llm_client.py` — one wrapper for every LLM call, per the architecture rule. Supports `json_mode` (forces valid JSON, avoids markdown-fence wrapping) and an overridable `max_tokens` (default `LLM_MAX_TOKENS = 8192` in config — another guessed value; we hit a real truncation failure at a smaller default once the sectioning prompt grew, so this is generous but unverified against the model's actual hard limit).
- `sectioner.py` — one LLM call does all of: candidate identity (name/email/phone), the 8 resume sections verbatim, certification extraction + tiering (assessed/completion, using proctored-exam + issuing-body criteria), link extraction with project labels, cross-section skill extraction (proven working — picked up `pgvector`/`React`/`SQLite` from project descriptions, not just the Skills line), and `years_experience` (LLM-computed, clamped to [0, 40] via a Pydantic validator regardless of what the model returns).
- `normalizer.py` — lowercases, dedupes, and aliases skills (`k8s`→`kubernetes` etc.) — a starting alias list, not exhaustive.
- `embedder.py` — `embed_documents`/`embed_query`, with the deliberate prefix asymmetry (query gets `QUERY_PREFIX`, documents don't) — verified the two produce different vectors for identical text, proving the asymmetry is real, not accidental.
- `store.py` additions: `add_certification`, `add_resume_link`. **`add_candidate` was rewritten** — originally always inserted, which crashed on any repeat email under the same company. Now it's find-or-create: same `(company_id, email)` reuses the existing candidate and refreshes their `name`/`phone`, rather than failing or leaving stale data. Multiple resumes per candidate already worked correctly the whole time (each `add_resume` call always creates a new row) — this fix was purely about the candidate identity layer.
- `pipeline.py` — `ingest_resume(company_id, pdf_bytes, expires_at)` orchestrates all of the above. Known, unfixed limitation: no single transaction across the whole function — a failure partway through (e.g. after the resume row exists but before embeddings finish) leaves partial data. Not fixed yet, flagged for later if it becomes a real problem.
- `scripts/ingest.py` — CLI to batch-ingest a folder. Needed an explicit `sys.path.insert(0, ...repo root...)` fix at the top — running a script directly from `scripts/` doesn't put the repo root on the import path the way `uv run python -c` from the repo root does. **`search_cli.py` and `calibrate.py` in Phase 3 will need this same fix.**
- `tests/test_embedding.py` — 6 passed: storage round-trip, normalization, cross-section skills, cert tiering, link extraction, no-truncation. 2 explicitly skipped with reasons (see below), not silently dropped.

**Real schema change, mid-phase — new migration:** added `resumes.skills` (JSON array) via Alembic. Wasn't in the original 9-table design. Reason: Phase 3's `skill_matcher.py` needs "exact overlap" matching against a *stored* skill list — without persisting it at ingestion time, scoring would need another LLM call per search, breaking the determinism rule ("after JD parse, nothing calls an LLM").

**Deviations from `Build_plan.md` (already updated there too):**
- `years_parser.py` was never built as a separate file — folded into `sectioner.py`'s single LLM call instead. Reasoning: real resume date formats are too inconsistent for reliable regex parsing, and the LLM call already exists for sectioning, so no extra cost to add one more field.
- Candidate identity (name/email/phone) also comes from the sectioner's LLM call — wasn't in the original schema design for `SectionedResume` at all; added once we actually tried to wire `pipeline.py` together and realized nothing else could supply it.

**Deferred — 2 of the 8 Phase 2 checkpoint items, tracked as `@pytest.mark.skip` in `test_embedding.py`, not forgotten:**
1. **Identity retrieval** ("search with its own text → returns itself first") — needs `retrieval/searcher.py`'s `search_by_vector`, which doesn't exist yet. **Whoever picks up Phase 3 should un-skip this test once vector search is built** — it's specifically designed to catch a similarity/distance sign flip that would silently invert the entire ranking.
2. **Speed at 50 resumes** — only 2 sample PDFs exist right now. Revisit once there's real volume, or fold into Phase 8's evaluation harness, which already targets `p95 < 3.5s`.

**What Phase 3 needs to know about how Phase 2 actually works (not just what the plan says):**
- `resume_embeddings` rows are only created for sections that are actually present — a resume with only 6 filled sections has exactly 6 embedding rows, not 8 padded with empty ones. Scoring's absence-rule redistribution needs to handle this per-resume, not assume a fixed count.
- The candidate's normalized skill list lives in `resumes.skills` (the new column) — read from there for exact-overlap matching, don't re-derive it from `skills_text` alone, since that would miss everything the cross-section extraction caught.
- Certification tier (`assessed`/`completion`) lives in the `certifications` table, one row per cert, linked by `resume_id` — this is what the cert-relevance boost (Phase 3) should query.
- A naming collision I flagged as a risk (`Certification`/`ResumeLink` exist as both Pydantic classes in `schemas/resume.py` and SQLAlchemy classes in `db/models.py`) turned out to be a non-issue in `pipeline.py`, since it never imports both at once. **If Phase 3's scoring code ever needs both together, it'll need an import alias** — just didn't come up yet.
- `add_candidate` is idempotent now (see above) — Phase 3/4 code calling it repeatedly for the same person is safe, not a bug.

**Project-level reminders, not code, worth keeping visible for a collaborator:**
- Supabase is a single free-tier project, labeled `PRODUCTION` by default — there's no separate dev/staging database. This is fine and deliberate until the first real company onboards; a second free project should be created before then (see decision log around Phase 9).
- `delete_company` (full cascade delete by `company_id`) and a data-export-by-`company_id` feature were both discussed and deliberately deferred — not built, but the schema already supports both without changes when they're needed (offboarding/GDPR-style requests).

**Blocked / needs discussion:** none

**Next session:** Phase 3 — retrieval & scoring (`retrieval/*`, `scoring/*`, `agents/jd_parser.py`, `embedding/reranker.py`).

---