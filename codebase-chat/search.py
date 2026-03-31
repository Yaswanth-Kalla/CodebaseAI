from sentence_transformers import SentenceTransformer
import numpy as np

# Import from previous step
from vector_store import main


# Load same model
model = SentenceTransformer('all-MiniLM-L6-v2')


def search(query, index, chunks, metadata, top_k=5):
    # Convert query to embedding
    query_embedding = model.encode([query])

    # Search FAISS index
    distances, indices = index.search(np.array(query_embedding), top_k)

    results = []

    for i in range(top_k):
        idx = indices[0][i]

        results.append({
            "chunk": chunks[idx],
            "file": metadata[idx]["file"],
            "score": distances[0][i]
        })

    return results


if __name__ == "__main__":
    repo_path = "D:/Institute/ML/stock_predictor_fastapi"

    # Build index
    index, chunks, metadata = main(repo_path)

    print("\n🔍 Codebase Search Ready! (type 'exit' to quit)\n")

    while True:
        query = input("💬 Enter your query: ")

        if query.lower() == "exit":
            break

        results = search(query, index, chunks, metadata)

        print("\n📌 Top Results:\n")

        for i, res in enumerate(results):
            print(f"Result {i+1}:")
            print(f"📂 File: {res['file']}")
            print(f"📊 Score: {res['score']}")
            print(f"💡 Code:\n{res['chunk'][:500]}")
            print("-" * 50)