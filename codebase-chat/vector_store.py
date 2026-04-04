print("🔥 Loading vector store...")

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from model_loader import get_model

from file_loader import load_codebase

# -------------------------------
# Load embedding model
# -------------------------------
from sentence_transformers import SentenceTransformer

model = get_model()  # Ensure model is loaded before any function runs


# -------------------------------
# Create embeddings
# -------------------------------
def create_embeddings(chunks):
    embeddings = get_model().encode(chunks, show_progress_bar=False, batch_size=64)
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
def main(repo_path, save_path="faiss_index"):
    chunks_data = load_codebase(repo_path)

    if not chunks_data:
        raise ValueError("❌ No chunks generated.")

    print(f"📦 Total raw chunks: {len(chunks_data)}")

    BATCH_SIZE = 32   # 🔥 VERY IMPORTANT
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

            name     = chunk.get("name", "")
            language = chunk.get("language", "")

            lang_prefix   = f"[{language.upper()}] " if language else ""
            enriched_text = f"{lang_prefix}{name}\n{code_text}" if name else f"{lang_prefix}{code_text}"

            texts.append(enriched_text)

            batch_meta.append({
                "file":       chunk.get("file"),
                "type":       chunk.get("type"),
                "name":       name,
                "language":   language,
                "start_line": chunk.get("start_line"),
                "end_line":   chunk.get("end_line"),
            })

        if not texts:
            continue

        # 🔥 Encode ONLY THIS BATCH
        embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
        embeddings = np.array(embeddings).astype("float32")

        # 🔥 Initialize FAISS once
        if index is None:
            dim = embeddings.shape[1]
            index = faiss.IndexFlatL2(dim)

        # 🔥 Add batch to FAISS
        index.add(embeddings)

        metadata.extend(batch_meta)

        print(f"✅ Processed batch {i//BATCH_SIZE + 1}")

    # 🔥 SAVE INDEX TO DISK
    os.makedirs(save_path, exist_ok=True)
    faiss.write_index(index, os.path.join(save_path, "index.faiss"))

    with open(os.path.join(save_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)

    print("💾 FAISS index saved to disk!")

    return save_path  # 🔥 RETURN PATH, NOT DATA
