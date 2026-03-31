import re


def chunk_python_code(code):
    """
    Extract functions and classes from Python code
    """
    pattern = r"(def .*?:\n(?:\s+.*\n)*)|(class .*?:\n(?:\s+.*\n)*)"
    matches = re.findall(pattern, code)

    chunks = []
    for match in matches:
        chunk = match[0] if match[0] else match[1]
        if chunk.strip():
            chunks.append(chunk.strip())

    return chunks


def chunk_js_code(code):
    """
    Extract JS functions (basic)
    """
    pattern = r"(function .*?{[\s\S]*?})"
    matches = re.findall(pattern, code)

    return [m.strip() for m in matches if m.strip()]


def chunk_html(code):
    """
    Split HTML into blocks (very basic)
    """
    pattern = r"(<[^>]+>[\s\S]*?</[^>]+>)"
    matches = re.findall(pattern, code)

    return [m.strip() for m in matches if m.strip()]


def chunk_css(code):
    """
    Split CSS into selector blocks
    """
    pattern = r"([^{]+{[^}]+})"
    matches = re.findall(pattern, code)

    return [m.strip() for m in matches if m.strip()]


def chunk_file(file_path):
    """
    Route file to correct chunker
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    if file_path.endswith(".py"):
        return chunk_python_code(code)

    elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
        return chunk_js_code(code)

    elif file_path.endswith(".html"):
        return chunk_html(code)

    elif file_path.endswith(".css"):
        return chunk_css(code)

    else:
        return [code]  # fallback


if __name__ == "__main__":
    from file_loader import get_code_files

    repo_path = "D:/Institute/ML/stock_predictor_fastapi"

    files = get_code_files(repo_path)

    all_chunks = []

    for file in files:
        chunks = chunk_file(file)
        print(f"\n📄 {file} → {len(chunks)} chunks")

        all_chunks.extend(chunks)

    print(f"\n🔥 Total chunks created: {len(all_chunks)}")