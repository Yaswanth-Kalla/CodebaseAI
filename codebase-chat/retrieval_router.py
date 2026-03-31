def detect_query_type(query):
    q = query.lower()

    if ".py" in q or ".js" in q or ".html" in q:
        return "file"

    if "function" in q or "def " in q:
        return "function"

    return "general"


def find_target_file(query, files):
    q = query.lower()

    for f in files:
        filename = f.split("\\")[-1].lower()
        if filename in q:
            return f

    return None


def get_chunks_for_file(target_file, chunks, metadata):
    return [
        chunks[i]
        for i in range(len(metadata))
        if metadata[i]["file"] == target_file
    ]