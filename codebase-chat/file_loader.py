import os
import ast


# -------------------------------
# Python Chunking (AST Based)
# -------------------------------
def chunk_python_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    tree = ast.parse(code)
    lines = code.splitlines()

    chunks = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start = node.lineno - 1
            end = node.end_lineno

            func_code = "\n".join(lines[start:end])

            chunks.append({
                "type": "function",
                "name": node.name,
                "file": file_path,
                "code": func_code
            })

        elif isinstance(node, ast.ClassDef):
            start = node.lineno - 1
            end = node.end_lineno

            class_code = "\n".join(lines[start:end])

            chunks.append({
                "type": "class",
                "name": node.name,
                "file": file_path,
                "code": class_code
            })

    return chunks


# -------------------------------
# Fallback Chunking (Non-Python)
# -------------------------------
def chunk_text_file(file_path, chunk_size=300):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    chunks = []
    words = text.split()

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])

        chunks.append({
            "type": "text",
            "name": "text_chunk",
            "file": file_path,
            "code": chunk
        })

    return chunks


# -------------------------------
# Get All Files
# -------------------------------
def get_code_files(repo_path):
    code_files = []

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".py", ".js", ".html", ".css",".ipynb")):
                code_files.append(os.path.join(root, file))
    print(f"Loaded files count: {len(code_files)}")
    return code_files


# -------------------------------
# Main Loader
# -------------------------------
def load_codebase(repo_path):
    files = get_code_files(repo_path)

    all_chunks = []

    for file in files:
        if file.endswith(".py"):
            chunks = chunk_python_file(file)
        else:
            chunks = chunk_text_file(file)

        all_chunks.extend(chunks)

    return all_chunks