import numpy as np
from rank_bm25 import BM25Okapi

from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')


def build_bm25(chunks):
    tokenized_chunks = [chunk.split() for chunk in chunks]
    return BM25Okapi(tokenized_chunks)


def hybrid_search(query, index, chunks, metadata, bm25, top_k=5):
    # ---------- Semantic Search ----------
    query_embedding = model.encode([query])
    distances, indices = index.search(np.array(query_embedding), top_k)

    semantic_scores = {}
    for i, idx in enumerate(indices[0]):
        semantic_scores[idx] = 1 / (1 + distances[0][i])  # convert distance → similarity

    # ---------- Keyword Search ----------
    tokenized_query = query.split()
    bm25_scores = bm25.get_scores(tokenized_query)

    keyword_scores = {i: bm25_scores[i] for i in range(len(bm25_scores))}

    # ---------- Combine Scores ----------
    combined_scores = {}

    for i in range(len(chunks)):
        sem = semantic_scores.get(i, 0)
        key = keyword_scores.get(i, 0)

        combined_scores[i] = 0.7 * sem + 0.3 * key  # weight tuning

    # ---------- Sort ----------
    sorted_indices = sorted(combined_scores, key=combined_scores.get, reverse=True)

    results = []
    for idx in sorted_indices[:top_k]:
        results.append({
            "chunk": chunks[idx],
            "file": metadata[idx]["file"],
            "score": combined_scores[idx]
        })

    return results