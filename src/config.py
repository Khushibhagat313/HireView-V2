# in src/config.py
COLUMN_GAP_THRESHOLD = 0.15  # fraction of page width; smaller gaps aren't treated as a real column split
MAX_FILE_SIZE_MB = 10
MAX_PAGES = 15
MIN_EXTRACTED_CHARS = 200
LLM_MAX_TOKENS = 8192
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
