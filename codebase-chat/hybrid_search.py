print("🔥 Running hybrid search...")
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from model_loader import get_model

model = get_model()  # Ensure model is loaded before hybrid search runs


def build_bm25(texts):
    tokenized_chunks = [text.lower().split() for text in texts]
    return BM25Okapi(tokenized_chunks)


def hybrid_search(query, index, metadata, bm25, top_k=5):
    n = len(metadata)
    if n == 0:
        return []

    # Clamp top_k so FAISS never asks for more vectors than exist
    k = min(top_k, n)

    # ---------- Semantic Search ----------
    query_embedding = np.array(
        model.encode([query]),
        dtype="float32"
    )
    distances, indices = index.search(np.array(query_embedding), k)

    # Convert L2 distance → similarity score in [0, 1]
    semantic_scores = {}
    for i, idx in enumerate(indices[0]):
        if idx == -1:           # FAISS returns -1 when there are fewer results
            continue
        semantic_scores[idx] = 1 / (1 + distances[0][i])

    # ---------- Keyword Search ----------
    tokenized_query = query.lower().split()
    bm25_raw        = bm25.get_scores(tokenized_query)
    if len(bm25_raw) != n:
        bm25_raw = bm25_raw[:n]

    # Normalise BM25 into [0, 1] so it's on the same scale as semantic scores
    bm25_max = bm25_raw.max()
    if bm25_max > 0:
        bm25_norm = bm25_raw / bm25_max
    else:
        bm25_norm = bm25_raw

    # ---------- Combine ----------
    combined_scores = {}

    # Only evaluate top candidates (faster)
    candidate_indices = set(indices[0]) | set(np.argsort(bm25_norm)[-top_k*2:])

    for i in candidate_indices:
        if i == -1 or i >= n:
            continue
        sem = semantic_scores.get(i, 0)
        key = float(bm25_norm[i])
        combined_scores[i] = 0.7 * sem + 0.3 * key

    sorted_indices = sorted(
        combined_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    results = []
    for idx,score in sorted_indices[:top_k]:
        results.append({
            "meta": metadata[idx],
            "file":  metadata[idx]["file"],
            "score": score,
        })

    return results
