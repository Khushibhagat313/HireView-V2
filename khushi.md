# Hey Khushi, here's what I did

This is a quick rundown of everything I changed in HireView, how to run it, and what's still left. Your backend was in really good shape, so most of my work was building the frontend on top of it. Along the way I fixed a few things the browser needed, plus some small issues I ran into.

Nothing about how scoring or ranking works has changed.

---

## 1. Getting the code

It's all in one pull request on your repo. To try it on your machine:

```bash
gh pr checkout <PR number>
```

Or open the pull request on GitHub and check out its branch. The website isn't live yet (see section 6), so for now it only runs locally.

---

## 2. How to run it

You need: Docker, Python with `uv`, **Node.js 20.19 or newer** (for the frontend), and your Groq key in `.env`.

### Backend

```bash
# 1. Start the database (first time only: see docs/SETUP.md for the full docker run command)
docker start hireview-db

# 2. Install packages and update the tables
uv sync
uv run alembic upgrade head

# 3. Start the API
uv run uvicorn src.api.main:app --port 8010 --reload
```

I used port **8010** because 8000 was already taken on my laptop. Any free port works, but the frontend expects 8010 unless you change `frontend/vite.config.ts`.

If you're setting up from scratch, `docs/SETUP.md` has every step. I rewrote it, and it now also covers `.env.example`.

### Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173**. The top right corner should say **Connected**. If it doesn't, the backend isn't running.

It uses **Test Co** (`a47c623b-...`) by default. To use a different company, put `VITE_COMPANY_ID=<id>` in `frontend/.env.local`.

### Tests

```bash
uv run pytest          # backend: 46 tests, needs the database running
cd frontend && npm test   # frontend: 20 small tests
```

---

## 3. What the frontend does

The design idea is **"Red Pen"**: the screen looks like a resume a recruiter has already marked up with a pen.

- Skills the candidate **has** are **highlighted in yellow**.
- Required skills they're **missing** are **crossed out in red**.
- Their label (Strong, Good, Partial...) is **circled in the margin**, like a handwritten note.

It has light mode, dark mode, and follows your system setting by default. There's a toggle in the header.

**Rank tab**
- Paste a job description (or click "Use sample job") and press **Rank candidates** (Ctrl+Enter also works).
- You get a ranked list showing each person's name, latest role, skills, label and score, plus a small summary at the top.
- You can filter by label (only Strong, only Good, etc.).
- If someone uploads or deletes a resume after you ranked, a "Pool changed, re-rank" message pops up.
- The last ranking stays even if you refresh the page.

**Ask panel** (right side of the Rank tab)
- This is the chat, using your `/chat` endpoint. It suggests questions based on the actual results, like "Who knows Docker?" or "Compare Priya and Riya".
- When an answer is a list of candidates, you can click a name to open their details.
- Pressing `/` anywhere jumps to the question box.

**Candidate panel** (click any candidate)
- Slides in from the right.
- Shows their email (with a copy button), phone, label, score, a score bar for each resume section, which required skills they have or are missing, and their work history.
- Two buttons call your AI endpoints: **Explain this match** (the feedback endpoint) and **Interview questions** (the interview guide endpoint).
- The left and right arrow keys move to the previous or next candidate, and Esc closes the panel.

**Pool tab**
- Lists every resume uploaded for the company.
- Drag and drop PDFs anywhere on the page, or click Upload. Files upload one at a time, with a timer, because each takes about 10 to 20 seconds.
- If an upload fails, you see the exact reason from the backend (for example "this PDF is a scanned image").
- Delete asks for a confirmation on the same row before it actually deletes.
- Works on phones too.

**Other small stuff**
- A "waking the server" message if the backend is slow to start.
- Friendly error messages instead of raw errors.
- An error screen instead of a blank white page if something crashes.

The code is all in `frontend/`, and `frontend/README.md` explains which file does what.

---

## 4. Backend fixes

I tried to keep these small and in your style. Here's each one in plain words.

### Round 1 (Oct 10): things the browser needed

1. **The browser couldn't call the API at all.** Browsers block websites from talking to a different address unless the server says it's okay (this is called CORS). I added that permission in `src/api/main.py`. The allowed addresses are in `src/config.py` (`CORS_ALLOWED_ORIGINS`).

2. **Search results were losing the skill info.** The pipeline worked out `skills`, `matched_required`, `missing_required`, `matched_preferred` and `work_experience`, but the response schema in `src/schemas/candidate.py` didn't list those fields, so FastAPI silently dropped them before sending. I added them to the schema. The highlighting in the frontend depends on these.

3. **New endpoint: `GET /resumes?company_id=...`** lists every resume in a company, so the Pool page can show them without needing a job description.

4. **Search is cached now.** The same company plus the same job description gives back the saved result instead of re-running everything. A repeat search went from about 1 to 3.5 seconds down to about 0.2 seconds. Uploading or deleting a resume clears that company's cache, so results are never out of date. The cache code is in `src/retrieval/pipeline.py`.

5. **Better error codes.** Before, almost every problem came back as "500 Internal Server Error". Now:
   - **422** for bad input, like a broken ID, a file that isn't a PDF, a scanned PDF, or a PDF that's too big. It also tells you which one.
   - **404** when something doesn't exist.
   - **503** when Groq is down.

   The frontend uses these to show proper messages.

6. **The same person showed up more than once.** If someone uploaded two resumes, they appeared twice in search. Now each person appears once, using their best-scoring resume. This applies to chat too.

7. **Setup docs.** `.env.example` was empty, so I filled it in. I also wrote `docs/SETUP.md` and updated `docs/API_CONTRACT.md` and the handoff section in `WORKLOG.md`. The first migration now turns on the `vector` extension itself, so a fresh database works without running any manual SQL.

8. **Things for deploying:**
   - The backend now accepts URLs that start with `/api/` (for example `/api/search`) and treats them as normal ones. This lets the website and the API live on the same address.
   - There's an optional `ACCESS_CODE` setting. If it's set, people need a code to use the app. It's a simple lock until we build real login.

9. **New tests** in `tests/test_api.py`. They don't need the database or Groq, so they're fast.

### Round 2 (Oct 15): the things I'd left for later

10. **Saving a resume is all-or-nothing now.** Before, if something failed halfway through an upload (say, while saving the embeddings), the candidate and resume were already saved, but without their embeddings. That half-saved resume would then quietly mess with search. Now everything is saved in one go: either it all saves, or nothing does. The new function is `save_ingested_resume` in `src/db/store.py`, and `src/ingestion/pipeline.py` uses it. There's also a test for this (`test_failed_ingestion_saves_nothing`).

11. **Tests clean up after themselves.** Running `pytest` used to add a new copy of Priya's resume to Test Co every time, and leave test companies behind. Now the tests make throwaway companies and delete them at the end (`make_company` in `tests/conftest.py`). Test Co stays clean.

12. **The chat answers in words when nobody matches.** Before, "who knows Kubernetes" with no matches just returned an empty list. Now it says "No one in these results lists Kubernetes on their resume." The same goes for top N, experience, and hidden gems.

    Skill questions can also have more than one skill now:
    - "who knows Python **and** Docker" means they need both.
    - "who knows Python **or** Go" means either one is enough.

    These changes are in `src/agents/conversation/handlers.py`.

---

## 5. Things to know

- **One test fails sometimes:** `test_storage_round_trip` checks that Groq reads exactly 0.25 years of experience from Priya's sample resume. Groq sometimes reads 0.17 (2 months instead of 3), so the test is flaky rather than broken. It might be worth changing it to check a range instead.
- **Old test companies:** your local database probably still has old test companies from before the cleanup fix ("Pytest Co", "Company A" to "D"). They don't affect Test Co, so you can delete them whenever.
- **Not done on purpose:**
  - **Login.** It's better to build it together with a login screen, and my suggestion is Supabase Auth.
  - **Fixing scores running a bit high.** That needs the labelled test set from Phase 8 first.

---

## 6. Putting it online (not done yet)

Everything is set up to put the frontend and backend on **Vercel** together, on one address:

- `vercel.json` tells Vercel that the website is in `frontend/` and the API runs from a Docker container.
- `Dockerfile.vercel` builds the backend. It uses the smaller CPU-only version of torch and includes the AI models inside, so it starts faster.
- `.dockerignore` keeps the frontend, tests and `.env` out of the container.

The only missing piece is a **cloud database**. Vercel can't reach our local Docker database, so we need a Supabase Postgres connection string (`DATABASE_URL`). Once we have that, deploying is a few commands. Let's decide together which Supabase account to use.

---

## 7. If you want more detail

- `documentation/fixes.md` has the long explanation of every Round 1 fix: what was wrong, why, and why I picked that fix.
- `WORKLOG.md` has two new entries (Oct 10 and Oct 15) in your format.
- `docs/API_CONTRACT.md` is up to date with all the endpoint changes.

Let me know if anything looks off or if you'd have done something differently. Happy to change it.

Yuvraj
