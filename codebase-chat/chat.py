from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import StreamingResponse
import requests
import re
import json
import os
import zipfile
import shutil
import subprocess
import nbformat

from vector_store import main
from hybrid_search import hybrid_search, build_bm25
from code_graph import build_code_graph
from file_loader import get_code_files
from context_expander import expand_context

from features import (
    explain_file,
    list_all_functions,
    find_definition,
    get_call_chain,
    extract_api_endpoints
)
import nbformat
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"

router = APIRouter()
UPLOAD_DIR = "uploaded_repos"

# -------------------------------
# GLOBAL STATE
# -------------------------------
current_repo = {
    "path": None,
    "index": None,
    "chunks": None,
    "metadata": None,
    "bm25": None,
    "files": None,
    "graph": None,
    "symbol_table": None,
    "call_graph": None,
}

# -------------------------------
# NOTEBOOK PARSER
# -------------------------------
def parse_ipynb(file_path):
    try:
        nb = nbformat.read(file_path, as_version=4)

        code_cells = []

        for cell in nb.cells:
            if cell.cell_type == "code":
                code = "".join(cell.source)
                if code.strip():
                    code_cells.append(code)

        return "\n\n".join(code_cells)

    except Exception as e:
        print("Notebook parse error:", e)
        return ""

# -------------------------------
# LOAD REPO (DYNAMIC)
# -------------------------------
def load_repository(repo_path):
    global current_repo

    print(f"Loading repo: {repo_path}")

    index, chunks, metadata = main(repo_path)
    bm25 = build_bm25(chunks)

    raw_files = get_code_files(repo_path)
    files = []
    file_contents_override = {}   # 🔥 important

    for f in raw_files:
        if f.endswith(".ipynb"):
            content = parse_ipynb(f)

            if content.strip():
                files.append(f)
                file_contents_override[f] = content  # 🔥 store parsed code
        else:
            files.append(f)
            
    for f in raw_files:
        if os.path.isfile(f):   # 🔥 IMPORTANT FILTER
            files.append(f)

    print("Loaded files count:", len(files))  # debug
    import json

    FILES_CACHE = "repo_files.json"

    # after building files
    with open(FILES_CACHE, "w") as f:
        json.dump(files, f)

    graph, symbol_table, call_graph = build_code_graph(files)

    # 🔥 CRITICAL: assign ONCE here
    current_repo = {
        "path": repo_path,
        "index": index,
        "chunks": chunks,
        "metadata": metadata,
        "bm25": bm25,
        "files": files,
        "graph": graph,
        "symbol_table": symbol_table,
        "call_graph": call_graph,
    }

    print("Repo stored in memory:", len(current_repo["files"]))  # 🔥 DEBUG

# -------------------------------
# INIT
# -------------------------------
# DEFAULT_REPO = r"D:\Institute\ML\stock_predictor_fastapi"
# load_repository(DEFAULT_REPO)

# -------------------------------
# GRAPH INFO
# -------------------------------
def get_relevant_graph_info(graph, retrieved_files):
    graph_info = ""
    for file in retrieved_files:
        if file in graph:
            info = graph[file]
            graph_info += f"\nFile: {file}\n"
            graph_info += f"Functions: {info['functions']}\n"
            graph_info += f"Imports: {info['imports']}\n"
    return graph_info

# -------------------------------
# RANK CHUNKS
# -------------------------------
def rank_chunks(query, chunks):
    scored = []
    query_words = set(query.lower().split())

    for chunk in chunks:
        score = 0
        text = chunk.lower()

        for word in query_words:
            if word in text:
                score += 2

        if "def " in text:
            score += 1

        scored.append((score, chunk))

    scored.sort(reverse=True)
    return [c for _, c in scored]

# -------------------------------
# FILE EXTRACTION
# -------------------------------
def extract_file_function_pairs(answer, graph, files):
    results = []
    answer_lower = answer.lower()

    function_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', answer)
    function_matches = list(set(func.lower() for func in function_matches))

    for file in files:
        filename = file  # 🔥 FULL PATH

        if file.split("\\")[-1].lower() not in answer_lower:
            continue

        graph_functions = graph.get(file, {}).get("functions", [])
        matched_functions = set()

        for func in graph_functions:
            if func.lower() in answer_lower:
                matched_functions.add(func)

        if not matched_functions:
            for func in function_matches:
                matched_functions.add(func)

        for func in matched_functions:
            results.append({"file": filename, "function": func})

        if not matched_functions:
            results.append({"file": filename, "function": None})

    # remove duplicates
    unique = []
    seen = set()

    for item in results:
        key = (item["file"], item["function"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique

# -------------------------------
# MEMORY
# -------------------------------
try:
    with open("memory.json", "r") as f:
        chat_history = json.load(f)
except:
    chat_history = []

last_user_query = None

# -------------------------------
# STREAM ANSWER
# -------------------------------
def stream_answer(query):
    global chat_history, last_user_query

    repo = current_repo

    if repo["index"] is None:
        yield "data:No repository loaded.\n\n"
        return

    index = repo["index"]
    chunks = repo["chunks"]
    metadata = repo["metadata"]
    bm25 = repo["bm25"]
    files = repo["files"]
    graph = repo["graph"]
    symbol_table = repo["symbol_table"]
    call_graph = repo["call_graph"]

    file_index = "\n".join([f.split("\\")[-1] for f in files])

    q = query.lower()

    if "that" in q or "again" in q:
        if last_user_query:
            query = last_user_query

    # -------- SPECIAL COMMANDS --------
    if q.startswith("explain file"):
        file = query.split("explain file")[-1].strip()
        yield f"data:{explain_file(graph, file, files)}\n\n"
        return

    elif "list functions" in q:
        yield f"data:{list_all_functions(graph)}\n\n"
        return

    elif "where is" in q:
        name = re.sub(r'[^a-zA-Z0-9_ ]', '', q)
        name = name.replace("where is", "").replace("defined", "").strip()
        name = name.replace(" ", "_")
        yield f"data:{find_definition(symbol_table, name)}\n\n"
        return

    elif "call chain" in q:
        func = query.split("call chain")[-1].strip()
        yield f"data:{get_call_chain(func, call_graph)}\n\n"
        return

    elif "api" in q:
        yield f"data:{extract_api_endpoints(files)}\n\n"
        return

    # -------- RAG SEARCH --------
    results = hybrid_search(query, index, chunks, metadata, bm25)

    if not results or results[0]["score"] < 0.25:
        yield "data:Not enough relevant information.\n\n"
        return

    context_chunks, retrieved_files = expand_context(
        results, graph, symbol_table, call_graph
    )

    if not context_chunks:
        yield "data:No context found.\n\n"
        return

    formatted_chunks = [
        f"[FILE: {file}]\n{chunk}" for chunk, file in context_chunks
    ]

    ranked_chunks = rank_chunks(query, formatted_chunks)
    context = "\n\n".join(ranked_chunks[:6])
    graph_info = get_relevant_graph_info(graph, retrieved_files)

    prompt = f"""
You are a helpful code assistant.

RULES: 
- Use the provided code context as the primary source
- You MAY combine information across files
- Do NOT invent functions or endpoints not present
- If unsure, say "Not enough information"
- Keep answers clear and structured
- Mention file names clearly 
- Mention function names explicitly 


FORMAT RULES: 
- Use proper paragraphs 
- Use headings when needed 
- Use bullet points 
- DO NOT overuse code blocks 
- Break response into multiple paragraphs
- Each paragraph must have 4-5 sentences MAX
- Use bullet points when listing steps
- Use headings when explaining sections
- Avoid long continuous paragraphs
- Keep responses clean and spaced
- Always respond in a structured and readable format


Files:
{file_index}

Structure:
{graph_info}

Code:
{context}

Question:
{query}

Answer:
"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": True},
            stream=True
        )

        full_answer = ""

        for line in response.iter_lines():
            if line:
                try:
                    token = json.loads(line.decode())["response"]
                    full_answer += token
                    yield f"data:{token}\n\n"
                except:
                    continue

        # 🔥 FILE EXTRACTION + FALLBACK
        file_function_pairs = extract_file_function_pairs(
            full_answer, graph, files
        )
        print("FILES SENT:", file_function_pairs)

        if not file_function_pairs:
            file_function_pairs = [
                {"file": f, "function": None}
                for f in retrieved_files[:5]
            ]
        print("FILES SENT:", file_function_pairs)
        yield f"data:__FILES__{json.dumps(file_function_pairs)}\n\n"

        chat_history.append(f"User: {query}")
        chat_history.append(f"Assistant: {full_answer}")
        last_user_query = query

        with open("memory.json", "w") as f:
            json.dump(chat_history[-10:], f)

    except Exception as e:
        yield f"data:Error: {str(e)}\n\n"

# -------------------------------
# FILE VIEWER
# -------------------------------
@router.get("/file-content")
def get_file_content(path: str = Query(...)):
    try:
        if path.endswith(".ipynb"):
            content = parse_ipynb(path)
        else:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        return {"path": path, "content": content}
    except Exception as e:
        return {"path": path, "content": str(e)}

# -------------------------------
# UPLOAD ZIP
# -------------------------------
@router.post("/upload-zip")
async def upload_zip(file: UploadFile = File(...)):
    repo_name = file.filename.replace(".zip", "")
    path = os.path.join(UPLOAD_DIR, repo_name)

    if os.path.exists(path):
        shutil.rmtree(path)

    os.makedirs(path, exist_ok=True)

    zip_path = os.path.join(path, file.filename)

    with open(zip_path, "wb") as f:
        f.write(await file.read())

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(path)

    os.remove(zip_path)

    # flatten nested folder
    inner = os.listdir(path)
    if len(inner) == 1:
        inner_path = os.path.join(path, inner[0])
        if os.path.isdir(inner_path):
            for f in os.listdir(inner_path):
                shutil.move(os.path.join(inner_path, f), path)
            shutil.rmtree(inner_path)

    load_repository(path)
    return {"status": f"{repo_name} loaded"}

# -------------------------------
# UPLOAD GITHUB
# -------------------------------
@router.post("/upload-github")
async def upload_github(data: dict):
    url = data.get("repo_url")

    name = url.split("/")[-1].replace(".git", "")
    path = os.path.join(UPLOAD_DIR, name)

    if os.path.exists(path):
        shutil.rmtree(path)

    subprocess.run(["git", "clone", url, path])

    load_repository(path)
    return {"status": f"{name} loaded"}


@router.get("/repo-status")
def repo_status():
    return {
        "loaded": current_repo["path"] is not None,
        "path": current_repo["path"]
    }
# -------------------------------
# CHAT ROUTE
# -------------------------------
@router.post("/chat-stream")
async def chat_stream(data: dict):
    return StreamingResponse(
        stream_answer(data.get("query", "")),
        media_type="text/event-stream"
    )

# -------------------------------
# SUMMARIZE (FIXED)
# -------------------------------
@router.post("/summarize-stream")
async def summarize_stream():

    repo = current_repo
    files = repo["files"]
    graph = repo["graph"]

    summary_context = ""
    if not files:
        return StreamingResponse(
            iter(["data:Please upload a repository first.\n\n"]),
            media_type="text/event-stream"
    )

    for file in files[:10]:
        summary_context += f"\nFile: {file}"

        if file in graph:
            summary_context += f"\nFunctions: {graph[file]['functions']}"
            summary_context += f"\nImports: {graph[file]['imports']}\n"

    prompt = f"""
You are an expert software engineer analyzing a codebase.

Your task is to generate a structured summary of the repository based on the provided files, functions, and imports.

### Instructions:
- Be concise but informative
- Do NOT hallucinate missing details
- Infer architecture where possible
- Focus on functionality and design

### Output Format:

## 📌 Project Overview
(What this project does in 2-3 sentences)

## 🧱 Architecture / Structure
(Explain how the project is organized based on files)

## ⚙️ Key Components
(List important files and what they do)

## 🔗 Dependencies & Imports
(What libraries/frameworks are used)

## 🧠 Observations
(Any patterns, design choices, or issues)

### Additional Requirements:
- Highlight main entry points if identifiable
- Mention possible tech stack (e.g., FastAPI, React, etc.)
- Identify relationships between files if possible
---

### Codebase Data:
{summary_context}
"""

    def generate():
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": True},
            stream=True
        )

        for line in response.iter_lines():
            if line:
                try:
                    token = json.loads(line.decode())["response"]
                    yield f"data:{token}\n\n"
                except:
                    continue

    return StreamingResponse(generate(), media_type="text/event-stream")