from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL, QUERY_PREFIX

model = SentenceTransformer(EMBEDDING_MODEL)

def embed_documents(texts: list[str]) -> list[list[float]]:
    return model.encode(texts, normalize_embeddings=True, batch_size=64).tolist()

def embed_query(text: str) -> list[float]:
    return model.encode(QUERY_PREFIX + text, normalize_embeddings=True).tolist()