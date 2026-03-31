from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

from chunker import chunk_file
from file_loader import get_code_files


# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')


def create_embeddings(chunks):
    embeddings = model.encode(chunks)
    return np.array(embeddings)


def build_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    return index


def main(repo_path):
    files = get_code_files(repo_path)

    all_chunks = []
    metadata = []

    for file in files:
        chunks = chunk_file(file)

        for chunk in chunks:
            all_chunks.append(chunk)
            metadata.append({
                "file": file
            })

    print(f"✅ Total chunks: {len(all_chunks)}")

    embeddings = create_embeddings(all_chunks)

    index = build_faiss_index(embeddings)

    print("🔥 FAISS index built successfully!")

    return index, all_chunks, metadata


if __name__ == "__main__":
    repo_path = "D:/Institute/ML/stock_predictor_fastapi"

    index, chunks, metadata = main(repo_path)