# Local Setup

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), Docker, a Groq API key, and ~2 GB of free disk space (the embedding and reranker models are downloaded from Hugging Face on first use).

## 1. Database (Postgres + pgvector in Docker)

```bash
docker run -d --name hireview-db \
  -e POSTGRES_USER=hireview -e POSTGRES_PASSWORD=hireview -e POSTGRES_DB=hireview \
  -p 5433:5432 pgvector/pgvector:pg16
```

Port 5433 on your machine avoids clashing with any other Postgres already on 5432. After a reboot, run `docker start hireview-db`.

## 2. Environment variables

```bash
cp .env.example .env
```

Fill in `GROQ_API_KEY`. The other values already match the Docker command above.

## 3. Install dependencies and create the tables

```bash
uv sync
uv run alembic upgrade head
```

The first migration enables the `vector` extension itself, so no manual SQL is needed.

## 4. Seed a company and some resumes

There is no endpoint to create a company yet, so insert one directly. This ID is the one the tests and the frontend use during development:

```bash
docker exec hireview-db psql -U hireview -c \
  "insert into companies(id,name,created_at) values ('a47c623b-569d-442b-8e0d-ff4c9d8dcf07','Test Co',now());"
uv run python scripts/ingest.py a47c623b-569d-442b-8e0d-ff4c9d8dcf07 tests
```

## 5. Run the API

```bash
uv run uvicorn src.api.main:app --port 8010 --reload
```

- Swagger UI: http://localhost:8010/docs
- The frontend dev server must run on an origin listed in `CORS_ALLOWED_ORIGINS` in `src/config.py` (default `http://localhost:5173`, Vite's default).
- `.env` is read when the server starts. Restart after changing it.

## 6. Tests

```bash
uv run pytest
```

The database tests create throwaway companies and delete them when they finish (`make_company` in `tests/conftest.py`), so running them leaves Test Co untouched. The database must be running.
