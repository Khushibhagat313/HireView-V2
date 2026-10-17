# in src/config.py
COLUMN_GAP_THRESHOLD = 0.15  # fraction of page width; smaller gaps aren't treated as a real column split
MAX_FILE_SIZE_MB = 10
MAX_PAGES = 15
MIN_EXTRACTED_CHARS = 200
LLM_MAX_TOKENS = 8192
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
RETRIEVE_TOP_K = 50
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
FACET_WEIGHTS = {
    "skills": 0.35,
    "projects": 0.20,
    "experience": 0.20,
    "achievements_publications": 0.15,
    "education_certifications": 0.10,
}
OPTIONAL_FACETS = {"achievements_publications", "education_certifications"}

FIELD_MATCH_THRESHOLD = 0.55
DISPLAY_THRESHOLD = 30
MAX_RESULTS = 25
MAX_CERT_BOOST = 1.2       # starting guess, tune with real data at Phase 8
CERT_RELEVANCE_FLOOR = 0.6 # below this, no boost — avoids noise

RERANK_KEEP_TOP_N = 20
RERANK_BLEND_WEIGHT = 0.5
EXACT_OVERLAP_WEIGHT = 0.6  # vs semantic similarity weight; starting guess, needs real-data tuning

HIDDEN_GEM_FACET_THRESHOLD = 0.6
HIDDEN_GEM_RANK_CUTOFF = 10


EVAL_TARGETS = {
    "recall_at_20": 0.70,
    "mrr": 0.85,
    "ndcg_at_10": 0.75,
    "skill_coverage_at_10": 0.65,
    "empty_rate": 0.0,
    "p95_latency_s": 3.5,
}

SEARCH_CACHE_SIZE = 64             # scored pools kept in memory (one per company + JD)
SEARCH_CACHE_TTL_SECONDS = 15 * 60 # safety net for pool changes made outside the API (e.g. scripts/ingest.py)

# Browser origins allowed to call the API. Vite dev server defaults to 5173; add the deployed frontend URL here.
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

