import functools

import src.retrieval.pipeline as pipeline
import src.retrieval.query_builder as query_builder
import src.scoring.cert_relevance as cert_relevance
import src.scoring.eligibility as eligibility
import src.scoring.facets as facets
from src.embedding import embedder


def _memoize(fn, key):
    cache = {}

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        k = key(*args, **kwargs)
        if k not in cache:
            cache[k] = fn(*args, **kwargs)
        return cache[k]

    return wrapper


def install() -> None:
    embed_query = _memoize(embedder.embed_query, lambda text: text)
    embed_documents = _memoize(embedder.embed_documents, lambda texts: tuple(texts))
    for module in (query_builder, facets, eligibility, cert_relevance):
        module.embed_query = embed_query
    for module in (eligibility, cert_relevance):
        module.embed_documents = embed_documents

    facets.get_resume_embeddings = _memoize(
        facets.get_resume_embeddings, lambda company_id, resume_id: (company_id, str(resume_id))
    )
    pipeline.search_candidates = _memoize(
        pipeline.search_candidates,
        lambda company_id, queries, job_posting_id=None: (
            company_id,
            job_posting_id,
            tuple(tuple(vector) for _, vector in sorted(queries.items())),
        ),
    )
    pipeline.rerank = _memoize(pipeline.rerank, lambda company_id, text, ids: (company_id, text, frozenset(ids)))
    for name in ("get_resumes", "get_work_experiences_many", "get_certifications_many", "get_candidates"):
        setattr(pipeline, name, _memoize(getattr(pipeline, name), lambda company_id, ids: (company_id, tuple(ids))))