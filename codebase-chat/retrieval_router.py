import re


def detect_query_type(query):
    q = query.lower()

    if re.search(r'\.\w{1,5}\b', q):   # any file extension mention
        return "file"

    if "function" in q or "def " in q or "method" in q:
        return "function"

    return "general"


def find_target_file(query, files):
    q = query.lower()

    for f in files:
        # cross-platform: handle both / and \
        basename = re.split(r'[\\/]', f)[-1].lower()
        if basename in q:
            return f

    return None


def get_chunks_for_file(target_file, chunks, metadata):
    return [
        chunks[i]
        for i in range(len(metadata))
        if metadata[i]["file"] == target_file
    ]