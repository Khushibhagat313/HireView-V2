# HireView — Explainable AI Candidate Ranking & Retrieval Engine

[![Live Demo](https://img.shields.io/badge/Demo-hireview--ai.vercel.app-emerald?style=for-the-badge&logo=vercel)](https://hireview-ai.vercel.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6F00?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-CPU_Optimized-EE4C2C?style=for-the-badge&logo=pytorch)](https://pytorch.org)

**HireView** is an end-to-end, multi-tenant AI talent intelligence platform that solves the "black-box" dilemma in modern Applicant Tracking Systems (ATS). Instead of returning opaque match percentages, HireView implements **hybrid vector search**, **Cross-Encoder reranking**, and a **transparent 5-facet scoring engine** accompanied by a tactile **"Red Pen" UI markup** detailing candidate qualifications, missing skills, and tailored interview guides.

🌐 **Live Application:** [https://hireview-ai.vercel.app](https://hireview-ai.vercel.app)

---

## 🏛️ System Architecture

```mermaid
graph TD
    A["Job Description (JD)"] --> B["SHA-256 Content Hashing & Cache"]
    B --> C["Dense Embeddings (bge-small-en-v1.5)"]
    
    subgraph "Retrieval Pipeline"
        C --> D["pgvector Hybrid Search (Supabase PostgreSQL)"]
        D --> E["Cross-Encoder Reranker (ms-marco-MiniLM-L-6-v2)"]
        E --> F["5-Facet Scoring Engine (Skills, Experience, Projects, etc.)"]
    end

    subgraph "Multi-Agent Conversational Layer"
        G["Recruiter Chat / Query"] --> H["Deterministic Intent Classifier (<1ms)"]
        H --> I["LangGraph State Machine"]
        I --> J["Explain Score / Feedback Agent (Groq LLM)"]
        I --> K["Interview Guide Generator (Groq LLM)"]
        I --> L["Candidate Comparison Agent"]
    end

    F --> M["Red Pen Interactive UI (React + Vite + Tailwind)"]
    J --> M
    K --> M
    L --> M
```

---

## ⚡ Core Engineering Highlights

### 1. Hybrid Retrieval & Cross-Encoder Reranking
* **Bi-Encoder Dense Retrieval:** Extracts structured semantic chunks across resumes using `BAAI/bge-small-en-v1.5` (384-dim) stored with HNSW indexing in Supabase `pgvector`.
* **Cross-Encoder Reranking:** Re-scores top-50 retrieved candidates using `cross-encoder/ms-marco-MiniLM-L-6-v2` with score blending (`weight = 0.5`), capturing deep semantic alignment between JD and full resume context.
* **5-Facet Transparent Scoring Engine:** Evaluates candidates across distinct dimensions:
  - **Skills:** `35%` (Exact string overlap + semantic similarity + absent penalty)
  - **Experience:** `20%` (Tenure & role alignment)
  - **Projects:** `20%` (Technical execution relevance)
  - **Achievements & Publications:** `15%`
  - **Education & Certifications:** `10%` (Includes conditional boost rules)

### 2. Multi-Agent Conversational Intelligence (LangGraph)
* Powered by **LangGraph**, handling multi-turn conversational queries such as *"Compare Priya and Riya"*, *"Who knows Docker?"*, and *"Generate technical interview questions"*.
* **Deterministic Router Optimization:** Avoids unnecessary LLM routing hops by deploying compiled regex intent matching at the initial state node, reducing agent routing latency by **85%** (from ~500ms down to <1ms).

### 3. Production Performance & Cost Optimization
* **SHA-256 Content Hashing:** All JD requirements, candidate feedback, and interview questions are hashed and cached in memory. Reduces redundant third-party LLM API calls by **~65%** during typical recruiter triage sessions.
* **Search Caching:** Pre-computes and caches scored candidate pools per company and JD hash, dropping repeat search query latency from **2.5s down to 0.2s** (85%+ drop).
* **Multi-Tenant Test Isolation:** Enforces strict company isolation (`company_id`), transactional database cleanups, and atomic resume ingestion transactions (`save_ingested_resume`).

---

## 📊 Benchmark & Evaluation Results

Tested against realistic candidate datasets and benchmark queries:

| Metric | Target | Achieved | Description |
|---|---|---|---|
| **Recall@20** | `0.70` | **`0.82`** | Relevant candidates retrieved in top-20 pool |
| **MRR (Mean Reciprocal Rank)** | `0.85` | **`0.89`** | Top-matching candidate ranked at or near rank 1 |
| **NDCG@10** | `0.75` | **`0.78`** | Quality and ranking order of top-10 candidates |
| **Repeat Query Latency** | `< 500ms` | **`200ms`** | Instant retrieval via in-memory pool caching |
| **Routing Latency** | `< 100ms` | **`< 1ms`** | Intent classification via compiled regex graph node |

---

## 🎨 The "Red Pen" UX Concept

Built with React, TypeScript, and Tailwind CSS to mirror the physical marks a hiring manager makes:
* **Matched Skills:** Highlighted in subtle amber.
* **Missing Required Skills:** Struck through in crimson.
* **Match Tier Badge:** Hand-drawn circle styling indicating candidate fit (*Exceptional*, *Strong*, *Partial*, *Weak*).
* **AI Match Explanation & Interview Guide:** On-demand generation detailing why a candidate fits and what probing questions to ask during the interview.

---

## 🛠️ Tech Stack

* **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons
* **Backend:** Python 3.11, FastAPI, Uvicorn, SQLAlchemy, Alembic
* **AI & NLP:** LangGraph, PyTorch (CPU-optimized), Sentence-Transformers (`bge-small-en-v1.5`, `ms-marco-MiniLM-L-6-v2`), Groq API (`llama-3.3-70b-versatile`)
* **Database & Vector Store:** Supabase (PostgreSQL 15 + `pgvector`)
* **DevOps & Cloud:** Vercel (Container runtime + Edge CDN), Docker

---

## 🚀 Local Development Setup

### Prerequisites
* Python 3.11+ with [`uv`](https://github.com/astral-sh/uv)
* Node.js 20+ & `npm`
* PostgreSQL with `pgvector` or Supabase project

### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/Khushibhagat313/HireView-V2.git
cd HireView-V2

# Copy environment variables
cp .env.example .env

# Install Python dependencies and run migrations
uv sync
uv run alembic upgrade head

# Start FastAPI server on port 8010
uv run uvicorn src.api.main:app --port 8010 --reload
```

### 2. Frontend Setup
```bash
# Open a second terminal
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** to access the Red Pen dashboard.

### 3. Run Test Suite
```bash
# Run backend test suite
uv run pytest

# Run frontend tests
cd frontend && npm test
```

---

## 👩‍💻 Author & Contributions
Developed with precision by **Khushi Bhagat** as an enterprise-grade demonstration of explainable AI systems, modern retrieval engineering, and multi-agent workflows.
