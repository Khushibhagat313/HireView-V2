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