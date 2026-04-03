from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

from file_loader import load_codebase

# -------------------------------
# Load embedding model
# -------------------------------
model = SentenceTransformer('all-MiniLM-L6-v2')


# -------------------------------
# Create embeddings
# -------------------------------
def create_embeddings(chunks):
    embeddings = model.encode(chunks, show_progress_bar=False, batch_size=64)
    return np.array(embeddings)


# -------------------------------
# Build FAISS index
# -------------------------------
def build_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


# -------------------------------
# MAIN PIPELINE
# -------------------------------
def main(repo_path):
    chunks_data = load_codebase(repo_path)

    all_chunks = []
    metadata   = []

    for chunk in chunks_data:
        code_text = chunk.get("code", "").strip()
        if not code_text:
            continue

        name     = chunk.get("name", "")
        language = chunk.get("language", "")

        # Richer embedding text: language prefix helps the model
        # distinguish e.g. SQL SELECT from a Python comment about SELECT
        lang_prefix    = f"[{language.upper()}] " if language else ""
        enriched_text  = f"{lang_prefix}{name}\n{code_text}" if name else f"{lang_prefix}{code_text}"

        all_chunks.append(enriched_text)
        metadata.append({
            "file":       chunk.get("file"),
            "type":       chunk.get("type"),
            "name":       name,
            "language":   language,          # ← now forwarded
            "start_line": chunk.get("start_line"),
            "end_line":   chunk.get("end_line"),
        })

    print(f"✅ Total chunks: {len(all_chunks)}")

    if len(all_chunks) == 0:
        raise ValueError("❌ No chunks generated.")

    embeddings = create_embeddings(all_chunks)
    index      = build_faiss_index(embeddings)

    print("🔥 FAISS index built successfully!")
    return index, all_chunks, metadata