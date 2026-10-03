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

**Addendum for whoever picks up Phase 3 (added 2026-09-20):**
- Real test data already exists: company `Test Co` (`a47c623b-569d-442b-8e0d-ff4c9d8dcf07`) has ingested resumes sitting in Supabase right now — no need to re-ingest to start testing retrieval. `tests/Priya_Sharma_Resume_sample.pdf` and `tests/Priya_Sharma_Resume_Two_Column_Realistic.pdf` are the source PDFs if more test data is needed.
- `query_builder.py` must use `embed_query()`, not `embed_documents()`, when converting the parsed JD into search vectors — that's the query side of the prefix asymmetry `embedder.py` was built and verified around. Using the wrong one won't error, it'll just quietly degrade retrieval quality.
- `sectioner.py` is the reference pattern for `jd_parser.py`: one LLM call, `call_llm(prompt, json_mode=True)`, parse into a Pydantic schema, retry once on `ValidationError`. Copy that shape rather than reinventing it.
- `applications` and `search_logs` tables exist in the schema but have no `store.py` functions built yet — don't assume they're ready to use.

**Blocked / needs discussion:** none

**Next session:** Phase 3 — retrieval & scoring (`retrieval/*`, `scoring/*`, `agents/jd_parser.py`, `embedding/reranker.py`).


---

## 2026-09-26 to 2026-09-27 — Khushi — ~12–14h
**Phase:** 3 (Retrieval & scoring) — COMPLETE

**New files built this phase:** `src/agents/jd_parser.py`, `src/retrieval/query_builder.py`, `src/retrieval/searcher.py`, `src/retrieval/pipeline.py`, `src/embedding/reranker.py`, `src/scoring/facets.py`, `src/scoring/skill_matcher.py`, `src/scoring/cert_relevance.py`, `src/scoring/eligibility.py`, `src/scoring/calibration.py`, `src/schemas/job.py`, `scripts/search_cli.py`, `tests/test_scoring.py`, `tests/sample_jd_junior.txt`.

**Phase 1/2 files retroactively changed:** `src/db/models.py`, `src/db/store.py`, `src/ingestion/sectioner.py`, `src/ingestion/pipeline.py`, `src/schemas/resume.py`, `src/config.py`.

**Done:**
- `jd_parser.py` — `parse_jd(text) → JDRequirements` + HyDE text in the same LLM call. Added in-memory cache keyed by SHA-256 hash of JD text — fixes a real non-determinism bug where identical JD searches produced different rankings because `hyde_text` regenerated every time. Hit and fixed a real token-truncation crash (`groq.BadRequestError`) — tightened `hyde_text` prompt to 150 words max, 1 job entry, 3 bullets.
- `query_builder.py` — parsed JD → 4 query vectors (skills, experience, projects, hyde). Each uses `embed_query()` with the query prefix.
- `searcher.py` — runs all 4 vectors against the database via `store.search_by_vector()`, unions the result IDs into a set. Supports optional `job_posting_id` for scoped search.
- `reranker.py` — cross-encoder (`ms-marco-MiniLM-L-6-v2`) scores (hyde_text, resume_text) pairs. Returns sorted list of (resume_id, score).
- `facets.py` — 5-facet scorer with the absence rule (missing sections get weight redistributed proportionally, not scored as zero). Refactored into 3 reusable pieces: `get_raw_facet_scores()` → `compute_composite()` → `score_facets()` (convenience wrapper), so the pipeline can inject hybrid skill score + cert boost before computing the composite.
- `skill_matcher.py` — hybrid exact-overlap + semantic skill matching. Both sides normalized through the same alias map (`normalize_skills`), so "K8s" matches "kubernetes." `EXACT_OVERLAP_WEIGHT = 0.6` (unvalidated guess). Returns matched/missing required and matched preferred skills — data Phase 5's feedback agent will use.
- `cert_relevance.py` — tier-gated certification boost. `tier == "assessed"` gates whether a boost fires; semantic relevance decides how much. `CERT_RELEVANCE_FLOOR` raised from 0.3 (blind guess) to 0.6 after testing with 3 real measurements (food safety vs frontend = 0.453, AWS vs frontend = 0.511, AWS vs cloud engineer = 0.727).
- `eligibility.py` — hard pass/fail gates, separate from fuzzy scoring (same separation as `guards.py` in Phase 2). Checks graduation-year eligibility + field-specific experience via embedding similarity between JD job title and each work-experience entry's title.
- `calibration.py` — **design reversal.** Original 3-anchor piecewise mapping had a hard ceiling that collapsed distinct candidates to the same score. Redesigned to `display = min(raw × 100, 99)` + separate `label_score()` (Exceptional/Strong/Good/Partial/Weak). Sort always by raw score.
- `pipeline.py` — the full orchestrator: `parse_jd` → `build_queries` → `search_candidates` → `rerank` → (per candidate) eligibility gate → facet scoring → hybrid skill override → cert boost → composite → calibrate + label → filter and rank. Verified end-to-end: Priya (backend) scored 83.4 "Exceptional," Riya (marketing) scored 38.7 "Partial."
- `search_cli.py` — Phase 3 checkpoint script. Takes company_id, --jd, optional --top, --job-posting-id, --threshold.
- `test_scoring.py` — 9/9 tests passing: determinism, no empty results, effective weights sum to 1.0, absence rule, limited-data flag, cert boost assessed gate, cert boost relevance gate, cert boost intended case, anti-keyword-stuffing.

**Retroactive changes to Phase 1/2 files (not new — already existed, modified):**
- `models.py` — added `WorkExperience` model (new `work_experiences` table, not in original 9-table design), added `graduation_year` column to `Resume`, added `Integer` to SQLAlchemy imports.
- `store.py` — `search_by_vector` gained optional `job_posting_id` parameter. New functions: `add_job_posting`, `add_application`, `add_work_experience`, `get_work_experiences`, `get_certifications`, `get_candidate`, `delete_company`.
- `sectioner.py` — replaced standalone `years_experience` LLM instruction with structured `work_experience` list (one object per job). Added `graduation_year` extraction. Fixed retry-loop bug (see below).
- `resume.py` — added `WorkExperienceEntry` model, `graduation_year` field. `years_experience` changed from LLM-provided to `@model_validator`-computed: `sum(w.duration_years for w in work_experience)`, capped at 40.
- `pipeline.py` — added optional `job_posting_id` parameter, `add_work_experience` loop, `graduation_year` in resume_data.
- `config.py` — added: `RETRIEVE_TOP_K`, `RERANKER_MODEL`, `FACET_WEIGHTS`, `FIELD_MATCH_THRESHOLD`, `DISPLAY_THRESHOLD` (30), `MAX_RESULTS` (25), `MAX_CERT_BOOST` (1.2), `CERT_RELEVANCE_FLOOR` (0.6), `RERANK_KEEP_TOP_N` (20), `EXACT_OVERLAP_WEIGHT` (0.6). Removed: `SCORE_FLOOR`, `SCORE_MID`, `SCORE_CEILING`.
- `schemas/job.py` — added `job_title`, `eligible_graduation_years` to `JDRequirements`.
- `jd_parser.py` — added `job_title`, `eligible_graduation_years` to prompt. Fixed double assignment (`JD_PROMPT = JD_PROMPT = ...`).

**Real bugs fixed:**
- **Retry loop not catching API errors** — `call_llm(...)` was outside the `try` block in both `sectioner.py` and `jd_parser.py`, so `groq.BadRequestError` (token-limit rejections) was never caught or retried. Both now wrap the API call inside `try` and catch `BadRequestError` alongside `JSONDecodeError`/`ValidationError`.
- **`hyde_text` token overflow** — LLM wrote a two-job detailed synthetic resume that exceeded token budget. Tightened to: 1-sentence summary, skills list, exactly 1 job entry with up to 3 bullets, under 150 words.
- **Non-determinism** — identical JD searches produced different rankings because `hyde_text` regenerated every time. Fixed with in-memory hash cache in `jd_parser.py`.
- **Calibration ceiling** — raw scores ≥ 0.72 all mapped to display 100, losing sort information. Eliminated entirely.

**Explicitly rejected:**
- **Company-prestige scoring** — permanently rejected. Contradicts the project's anti-proxy principle. Company name is stored in `work_experiences`, surfaced to recruiters, never scored.

**Key finding — composite score range changed:**
Once the Skills facet is overridden with `hybrid_skill_score × cert_boost`, the composite can exceed the original ~0.25–0.75 range. Priya's composite was ~0.834. Phase 8's `scripts/calibrate.py` must measure the post-hybrid distribution, not assume the old range.

**Unvalidated constants (all need Phase 8 data-driven tuning):**
`FIELD_MATCH_THRESHOLD` (0.5), `MAX_CERT_BOOST` (1.2), `CERT_RELEVANCE_FLOOR` (0.6), `EXACT_OVERLAP_WEIGHT` (0.6), `RERANK_KEEP_TOP_N` (20), facet weights, calibration label boundaries (60/50/40/30), `hyde_text` 150-word cap.

**Open gap:** no test checks `hyde_text` against the embedding model's 512-token window. Must be added before Phase 8.

**What Phase 4 needs to know:**
- `search_and_score()` in `retrieval/pipeline.py` is the single entry point — takes `company_id`, `jd_text`, optional `job_posting_id`/`threshold`/`max_results`, returns a list of result dicts.
- Each result dict contains: `resume_id`, `candidate_id`, `raw_score`, `display_score`, `label`, `facet_scores` (dict — keys vary per candidate due to absence rule), `limited_data`.
- `ingest_resume()` in `ingestion/pipeline.py` takes `company_id`, `pdf_bytes`, optional `job_posting_id`/`expires_at`, returns `resume_id`.
- Eligibility gate (pass/fail) needs its own field in the API response — distinct from numeric score.
- Label (Exceptional/Strong/Good/Partial/Weak) should be visually prominent in Phase 6, number secondary.
- `skill_matcher.py` returns `matched_required`/`missing_required`/`matched_preferred` — Phase 5's feedback agent should use this data.

**Blocked / needs discussion:** none

---

## 2026-09-28 — Khushi — Xh
**Phase:** 4 (FastAPI layer) — COMPLETE for everything with real backing

**Files touched:** `src/api/main.py`, `src/api/dependencies.py`, `src/api/routes/resumes.py`, `src/api/routes/search.py`, `src/api/routes/candidates.py`, `src/retrieval/pipeline.py`, `src/db/store.py`, `docs/API_CONTRACT.md`, `pyproject.toml`/`uv.lock` (new deps)

**Done:**
- `docs/API_CONTRACT.md` written first, documenting both built and deliberately-deferred endpoints
- `main.py` + `/health` — first successful FastAPI + uvicorn run
- Two missing dependencies caught and installed: `uvicorn`, `python-multipart` (Phase 0's original install list was incomplete for API work)
- `POST /resumes/upload`, `DELETE /resumes/{id}` — multipart form handling, wired to existing `ingest_resume`/`delete_resume`
- `POST /search` — full Phase 3 pipeline wired in via a Pydantic request body (`SearchRequest`)
- Fixed a real duplication bug: moved `candidate_name` lookup into `search_and_score` itself (in `retrieval/pipeline.py`) instead of leaving both `search_cli.py` and the new API route to independently re-implement the same lookup
- `GET /candidates/{id}` — needed a new `get_candidate` function in `store.py`, which had never existed
- Architectural check passed: `fastapi` only imported inside `src/api/`, confirmed via grep
- Full checkpoint proven end-to-end: upload → search (present) → delete → search again (gone)

**Phase 4 — addendum:**
- **Two dependencies missing from Phase 0's original install list:** `uvicorn` (needed to run a FastAPI app — FastAPI itself has no built-in server) and `python-multipart` (needed for any endpoint using `Form`/`File`, i.e. file uploads). Neither was caught until Phase 4 actually needed them. Worth adding to Phase 0's documented dependency list retroactively, since a fresh environment setup would hit both immediately.
- **`candidate_name` moved into `search_and_score` itself, not left as a route-level concern:** Originally patched by having the API route fetch each candidate's name separately after calling `search_and_score`. Caught as real duplication — `search_cli.py` was already doing the identical lookup independently. Fixed at the source: `retrieval/pipeline.py`'s `search_and_score` now returns `candidate_name` directly, and both callers were simplified to just use it.
- **New `store.py` function this phase:** `get_candidate(company_id, candidate_id)` — a basic getter that had never been built despite `add_candidate` existing since Phase 1. Needed the moment an actual API response had to include a candidate's name/email/phone.
- **Scope — only 4 of the originally-planned ~8 endpoints are built, deliberately:** `resumes/upload`, `resumes/delete`, `search`, `candidates/{id}` are built, tested, and proven via the full upload→search→delete→search checkpoint. `candidates/{id}/feedback`, `candidates/{id}/interview-guide`, `chat`, `emails` are explicitly deferred — they depend on Phase 5 (`agents/feedback.py`, `agents/interview_guide.py`, `agents/conversation/*`) and Phase 7 (`email/*`) respectively, none of which exist yet. This isn't scope creep avoidance — it's the only order that makes sense, since building stub endpoints for non-existent logic would just need rebuilding later. `API_CONTRACT.md` already documents all of them, built or not.
- **`schemas/candidate.py`, `schemas/chat.py` remain empty:** Routes currently return plain dicts rather than formal `CandidateResponse`-style Pydantic models (per the build plan's own naming convention table). Functionally correct, just not matching the stated convention yet — worth tightening whenever these routes get revisited (naturally, when Phase 5's feedback/interview-guide endpoints get added to the same file).

**Forward impact on later phases:**
- **Phase 5:** The feedback/interview-guide/chat routes, once their underlying agent logic exists, should follow the exact same thin-wrapper pattern already established here (`routes/candidates.py`, `routes/search.py`) — a route function that validates input via Pydantic, calls existing business logic, returns the result. No new architectural pattern needed, just more routes in the same shape.
- **Phase 6:** The frontend can build against `resumes/upload`, `search`, and `candidates/{id}` with real confidence — these aren't just documented in the contract, they're proven working end-to-end against real data. One thing confirmed and worth remembering: the JSON-escaping issue that came up during manual Swagger testing (multi-line text needing `\n` escapes) is *not* something Phase 6's frontend code needs to handle specially — `JSON.stringify` does this automatically for any normal fetch/axios call, so a real textarea with natural line breaks will work correctly without any extra handling.

**Blocked / needs discussion:** none

**Next session:** Phase 5 — LLM agents (`agents/feedback.py`, `agents/conversation/*`)

---

## 2026-10-02 to 2026-10-03 — Khushi — ~14–16h
**Phase:** 5 (LLM Agents, LangGraph Conversational Agent & Endpoints) — COMPLETE

**New files built this phase:**
- `src/agents/conversation/state.py` — `HiringState` TypedDict schema for LangGraph.
- `src/agents/conversation/router.py` — Rule-based intent classification for 8 intents (specific patterns ordered before general).
- `src/agents/conversation/handlers.py` — 8 intent handlers (`show_top_n`, `filter_by_skill`, `filter_by_experience`, `hidden_gems`, `explain_score`, `compare`, `interview_questions`, `general`) with bias guardrails and deterministic aggregation (`_pool_summary`).
- `src/agents/conversation/graph.py` — StateGraph compiling nodes and conditional routing edges.
- `src/agents/feedback.py` — Generates grounded score explanations with label-first framing and compound caching.
- `src/agents/interview_guide.py` — Generates targeted interview questions with prompt-injection defense and caching.
- `src/api/routes/chat.py` — `POST /chat` endpoint invoking the LangGraph workflow.
- `tests/test_agents.py` — 10 passing unit and integration tests.

**Phase 3/4 files modified:**
- `src/api/routes/candidates.py` — wired `POST /candidates/{id}/feedback` and `POST /candidates/{id}/interview-guide`.
- `src/api/routes/search.py` & `src/schemas/candidate.py` — added `SearchResult` / `SearchResponse` response model.
- `src/retrieval/pipeline.py` — carried forward `skills`, `matched_required`, `missing_required`, `matched_preferred`, and `work_experience` (as `SimpleNamespace` objects) in search results.
- `src/scoring/eligibility.py` — supported both dict and dot-notation objects in field-specific experience computation.
- `src/config.py` — added `HIDDEN_GEM_FACET_THRESHOLD = 0.6`, `HIDDEN_GEM_RANK_CUTOFF = 10`, `FIELD_MATCH_THRESHOLD = 0.55`.
- `docs/API_CONTRACT.md` — fully documented `/chat`, feedback, and interview-guide endpoints.

**Done:**
- Built full LangGraph workflow routing queries deterministically without LLM routing overhead.
- Implemented structural bias mitigation: candidate names and graduation years are never passed into LLM prompts; placeholders ("Candidate A/B/N") are used and real names restored post-generation.
- Prompt injection defense: rejected malicious resume commands, validated output format with regex, and raised `GuideUnavailable` so refusals or attacks are never saved into cache.
- Deterministic pool statistics: `_pool_summary` calculates exact counts using `Counter` and collapses duplicate resumes so general recruiter queries receive factual, hallucination-free summaries.
- Wired remaining candidate endpoints and verified 10/10 tests green in `tests/test_agents.py`.

---

### 🚀 Handoff Guide for Phase 6 (Frontend Partner)

The entire backend API for Phase 6 is **live, tested, and ready**. You do not need mock data — you can connect directly to the real API!

#### 1. How to run the backend locally:
```bash
uv run uvicorn src.api.main:app --reload
```
- API Base URL: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`

#### 2. Test Data Available:
- **`company_id`**: `a47c623b-569d-442b-8e0d-ff4c9d8dcf07` (Test Co — has ingested resumes in the database).
- **Sample JD text**: available in `tests/sample_jd_junior.txt` (Junior Backend Developer role).

#### 3. Key Endpoints & Frontend Expectations:

| Endpoint | Method | Request Body / Params | Expected Response & Frontend Behavior |
|---|---|---|---|
| `/resumes/upload` | `POST` | Multipart Form: `company_id`, `file` (PDF) | `{ "resume_id": "uuid", "filename": "...", "message": "..." }` |
| `/search` | `POST` | JSON: `{ "company_id": "...", "jd_text": "..." }` | Returns list of candidates with `candidate_id`, `candidate_name`, `label` (`Exceptional`/`Strong`/`Good`/`Partial`/`Weak`), `display_score`, `facet_scores`. **Rule:** Show the `label` prominently (badge/color), display score secondary. |
| `/chat` | `POST` | JSON: `{ "company_id": "...", "jd_text": "...", "query": "..." }` | Returns `{ "intent": "...", "response_text": "string or null", "response_candidates": [ ... ] or null }`. **Important:** The UI must render `response_candidates` as candidate cards (for filter intents) OR render `response_text` as markdown (for conversational answers). |
| `/candidates/{id}/feedback` | `POST` | JSON: `{ "company_id": "...", "jd_text": "..." }` | Returns `{ "candidate_id": "...", "feedback": "..." }`. Note: This is **POST** (not GET) because it needs the JD text. |
| `/candidates/{id}/interview-guide` | `POST` | JSON: `{ "company_id": "...", "jd_text": "..." }` | Returns `{ "candidate_id": "...", "interview_guide": "..." }`. Note: This is **POST** (not GET). |
| `/candidates/{id}` | `GET` | Query param: `?company_id=...` | Returns `{ "name": "...", "email": "...", "phone": "..." }`. |

#### 4. Important UI / UX Considerations:
- **Markdown Rendering:** `response_text`, feedback, and interview guides contain markdown (`**bold**`, numbered lists `1. 2. 3.`, `Why: ...`). Use a React markdown renderer (e.g. `react-markdown`).
- **Error Status Codes to handle:**
  - `404 Not Found`: Candidate was not in the ranked search results for this JD.
  - `422 Unprocessable Entity`: The model could not produce usable interview questions for the resume.
  - `503 Service Unavailable`: Temporary AI provider outage — show a friendly *"AI service temporarily unavailable, please try again"* message.
- **Stateless Chat:** Each `/chat` call is independent (no multi-turn history kept on backend). Every chat request must include `{ company_id, jd_text, query }`.
- **Duplicate Resumes:** Candidates with multiple resume uploads currently appear as distinct search items; candidate name matching in chat automatically resolves to their highest-scoring resume.

**Next session:** Phase 6 — Frontend development (`frontend/`) in React + Tailwind.

