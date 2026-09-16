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