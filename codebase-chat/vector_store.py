# print("🔥 Loading vector store...")

# from sentence_transformers import SentenceTransformer
# import faiss
# import numpy as np
# from model_loader import get_model

# from file_loader import load_codebase

# # -------------------------------
# # Load embedding model
# # -------------------------------
# from sentence_transformers import SentenceTransformer

# model = get_model()  # Ensure model is loaded before any function runs


# # -------------------------------
# # Create embeddings
# # -------------------------------
# def create_embeddings(chunks):
#     embeddings = get_model().encode(chunks, show_progress_bar=False, batch_size=64)
#     return np.array(embeddings)


# # -------------------------------
# # Build FAISS index
# # -------------------------------
# def build_faiss_index(embeddings):
#     dim = embeddings.shape[1]
#     index = faiss.IndexFlatL2(dim)
#     index.add(embeddings)
#     return index


# # -------------------------------
# # MAIN PIPELINE
# # -------------------------------
# def main(repo_path):
#     chunks_data = load_codebase(repo_path)

#     all_chunks = []
#     metadata   = []

#     for chunk in chunks_data:
#         code_text = chunk.get("code", "").strip()
#         if not code_text:
#             continue

#         name     = chunk.get("name", "")
#         language = chunk.get("language", "")

#         # Richer embedding text: language prefix helps the model
#         # distinguish e.g. SQL SELECT from a Python comment about SELECT
#         lang_prefix    = f"[{language.upper()}] " if language else ""
#         enriched_text  = f"{lang_prefix}{name}\n{code_text}" if name else f"{lang_prefix}{code_text}"

#         all_chunks.append(enriched_text)
#         metadata.append({
#             "file":       chunk.get("file"),
#             "type":       chunk.get("type"),
#             "name":       name,
#             "language":   language,          # ← now forwarded
#             "start_line": chunk.get("start_line"),
#             "end_line":   chunk.get("end_line"),
#         })

#     print(f"✅ Total chunks: {len(all_chunks)}")

#     if len(all_chunks) == 0:
#         raise ValueError("❌ No chunks generated.")

#     embeddings = create_embeddings(all_chunks)
#     index      = build_faiss_index(embeddings)

#     print("🔥 FAISS index built successfully!")
#     return index, all_chunks, metadata


print("🔥 Loading vector store...")

import faiss
import numpy as np
import os
import json
import time   # 🔥 ADDED

from model_loader import embed_texts
from file_loader import load_codebase

# -------------------------------
# CONFIG (🔥 IMPORTANT)
# -------------------------------
BATCH_SIZE = 5          # Gemini-safe batching
NORMALIZE  = True        # improves FAISS search

# -------------------------------
# MAIN PIPELINE
# -------------------------------
def main(repo_path, save_path="faiss_index"):
    chunks_data = load_codebase(repo_path)

    if not chunks_data:
        raise ValueError("❌ No chunks generated.")

    print(f"📦 Total raw chunks: {len(chunks_data)}")

    index = None
    metadata = []

    for i in range(0, len(chunks_data), BATCH_SIZE):
        batch = chunks_data[i:i+BATCH_SIZE]

        texts = []
        batch_meta = []

        for chunk in batch:
            code_text = chunk.get("code", "").strip()
            if not code_text:
                continue

            name       = chunk.get("name", "")
            language   = chunk.get("language", "")
            chunk_type = chunk.get("type", "")

            # 🔥 BETTER EMBEDDING FORMAT
            enriched_text = (
                f"[LANG:{language}] "
                f"[TYPE:{chunk_type}] "
                f"{name}\n{code_text}"
            )

            texts.append(enriched_text)

            batch_meta.append({
                "file":       chunk.get("file"),
                "type":       chunk_type,
                "name":       name,
                "language":   language,
                "start_line": chunk.get("start_line"),
                "end_line":   chunk.get("end_line"),
                "text":       code_text
            })

        if not texts:
            continue

        # 🔥 GEMINI EMBEDDINGS (API CALL)
        embeddings = embed_texts(texts)
        embeddings = np.array(embeddings).astype("float32")

        # 🔥 RATE LIMIT FIX (VERY IMPORTANT)
        time.sleep(1)   # ✅ prevents 429 quota error

        # 🔥 NORMALIZATION
        if NORMALIZE:
            faiss.normalize_L2(embeddings)

        # 🔥 INIT INDEX
        if index is None:
            dim = embeddings.shape[1]
            index = faiss.IndexFlatL2(dim)

        index.add(embeddings)
        metadata.extend(batch_meta)

        print(f"✅ Processed batch {i // BATCH_SIZE + 1}")

    # 🔥 SAVE TO DISK
    os.makedirs(save_path, exist_ok=True)

    faiss.write_index(index, os.path.join(save_path, "index.faiss"))

    with open(os.path.join(save_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)

    print("💾 FAISS index saved to disk!")

    return save_path
