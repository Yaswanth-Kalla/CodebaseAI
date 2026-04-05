"""
file_loader.py — walks a repo and produces chunks via multi_ast.chunk_file.

All AST / regex / fallback logic has been moved to multi_ast.py so this file
stays thin and focused on file discovery + orchestration.
"""

import os
import nbformat

from multi_ast import chunk_file          # ← single unified entry point


# ════════════════════════════════════════════════════════════════════════════
# FILE DISCOVERY
# ════════════════════════════════════════════════════════════════════════════

SUPPORTED_EXTENSIONS = (
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".c", ".cpp", ".cc",
    ".cs", ".go", ".rb", ".rs", ".php",
    ".html", ".ejs", ".xml",
    ".css", ".sql",
    ".ipynb",
)


def get_code_files(repo_path: str) -> list:
    code_files = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(SUPPORTED_EXTENSIONS):
                code_files.append(os.path.join(root, file))
    print(f"Loaded files count: {len(code_files)}")
    return code_files


# ════════════════════════════════════════════════════════════════════════════
# NOTEBOOK SUPPORT
# ════════════════════════════════════════════════════════════════════════════

def _chunk_ipynb(file_path: str) -> list:
    """Extract code cells from a Jupyter notebook as individual chunks."""
    try:
        nb = nbformat.read(file_path, as_version=4)
    except Exception as e:
        print(f"Notebook parse error ({file_path}): {e}")
        return []

    chunks = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        code = "".join(cell.source).strip()
        if not code:
            continue
        chunks.append({
            "type":       "notebook_cell",
            "name":       f"cell_{i}",
            "file":       file_path,
            "language":   "python",
            "code":       code,
            "start_line": i,
            "end_line":   i,
        })
    return chunks


# ════════════════════════════════════════════════════════════════════════════
# MAIN LOADER
# ════════════════════════════════════════════════════════════════════════════

def load_codebase(repo_path: str) -> list:
    files      = get_code_files(repo_path)
    all_chunks = []

    for file in files:
        if file.endswith(".ipynb"):
            chunks = _chunk_ipynb(file)
        else:
            chunks = chunk_file(file)          # multi_ast handles everything

        all_chunks.extend(chunks)

    print("Total chunks generated:", len(all_chunks))
    return all_chunks