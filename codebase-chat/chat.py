
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

print("🔥 CHAT FILE LOADED (SAFE)")


# from vector_store import main
def run_vector_store(repo_path):
    from vector_store import main
    return main(repo_path)
def run_hybrid_search(*args, **kwargs):
    from hybrid_search import hybrid_search,build_bm25
    return hybrid_search(*args, **kwargs)
# from hybrid_search import hybrid_search, build_bm25
# from file_loader import get_code_files
# from context_expander import expand_context
def load_files(repo_path):
    from file_loader import get_code_files
    return get_code_files(repo_path)

def expand_ctx(*args):
    from context_expander import expand_context
    return expand_context(*args)
# ── build_code_graph is OPTIONAL ────────────────────────────────────────────
# It adds symbol_table + call_graph context for Python files.
# Non-Python heavy repos work perfectly without it.
# If code_graph.py is absent or fails, we degrade gracefully.
try:
    from code_graph import build_code_graph
    _CODE_GRAPH_AVAILABLE = True
except ImportError:
    _CODE_GRAPH_AVAILABLE = False
    print("[chat] code_graph not found — graph features disabled.")

from features import (
    explain_file,
    list_all_functions,
    find_definition,
    get_call_chain,
    extract_api_endpoints
)
from dotenv import load_dotenv
load_dotenv()

# -------------------------------
# API CONFIGURATION
# -------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL   = "llama-3.3-70b-versatile"

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:streamGenerateContent?alt=sse&key={GEMINI_API_KEY}"
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"

router = APIRouter()
UPLOAD_DIR = "uploaded_repos"

# -------------------------------
# GLOBAL STATE
# -------------------------------
current_repo = {
    "path":         None,
    "index":        None,
    "chunks":       None,
    "metadata":     None,
    "bm25":         None,
    "files":        None,
    "graph":        None,
    "symbol_table": None,
    "call_graph":   None,
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

    index, chunks, metadata = run_vector_store(repo_path)
    bm25 = build_bm25(chunks)

    raw_files = load_files(repo_path)
    files = []
    file_contents_override = {}

    for f in raw_files:
        if f.endswith(".ipynb"):
            content = parse_ipynb(f)
            if content.strip():
                files.append(f)
                file_contents_override[f] = content
        elif os.path.isfile(f):
            files.append(f)

    # Deduplicate
    files = list(dict.fromkeys(files))
    print("Loaded files count:", len(files))

    FILES_CACHE = "repo_files.json"
    with open(FILES_CACHE, "w") as f:
        json.dump(files, f)

    # ── code graph (optional) ───────────────────────────────────────────
    if _CODE_GRAPH_AVAILABLE:
        graph, symbol_table, call_graph = build_code_graph(files)
    else:
        graph        = {}
        symbol_table = {}
        call_graph   = {}

    current_repo = {
        "path":         repo_path,
        "index":        index,
        "chunks":       chunks,
        "metadata":     metadata,
        "bm25":         bm25,
        "files":        files,
        "graph":        graph,
        "symbol_table": symbol_table,
        "call_graph":   call_graph,
    }

    print("Repo stored in memory:", len(current_repo["files"]))

# -------------------------------
# LLM ABSTRACTION — Gemini → Groq fallback
# -------------------------------
def stream_llm(prompt: str):
    gemini_ok = bool(GEMINI_API_KEY)
    groq_ok   = bool(GROQ_API_KEY)

    if gemini_ok:
        try:
            yield from _stream_gemini(prompt)
            return
        except _QuotaExceeded:
            print("Gemini quota exceeded — switching to Groq.")
        except Exception as e:
            print(f"Gemini error: {e} — switching to Groq.")

    if groq_ok:
        yield from _stream_groq(prompt)
        return

    raise RuntimeError("No LLM API keys configured. Set GEMINI_API_KEY or GROQ_API_KEY.")


class _QuotaExceeded(Exception):
    pass


def _stream_gemini(prompt: str):
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        },
    }

    response = requests.post(GEMINI_URL, headers=headers, json=body, stream=True, timeout=60)

    if response.status_code == 429:
        raise _QuotaExceeded()
    if response.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {response.status_code}: {response.text[:200]}")

    for raw_line in response.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if not line.startswith("data:"):
            continue
        data_str = line[len("data:"):].strip()
        if not data_str or data_str == "[DONE]":
            continue
        try:
            data  = json.loads(data_str)
            token = (
                data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
            )
            if token:
                yield token
        except Exception:
            continue


def _stream_groq(prompt: str):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream":    True,
        "temperature": 0.2,
        "max_tokens":  2048,
    }

    response = requests.post(GROQ_URL, headers=headers, json=body, stream=True, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(f"Groq HTTP {response.status_code}: {response.text[:200]}")

    for raw_line in response.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if not line.startswith("data:"):
            continue
        data_str = line[len("data:"):].strip()
        if not data_str or data_str == "[DONE]":
            continue
        try:
            data  = json.loads(data_str)
            token = (
                data.get("choices", [{}])[0]
                    .get("delta", {})
                    .get("content", "")
            )
            if token:
                yield token
        except Exception:
            continue


# -------------------------------
# GRAPH INFO  (works with or without build_code_graph)
# -------------------------------
def get_relevant_graph_info(graph, retrieved_files, metadata_lookup=None):
    """
    Build a concise graph/metadata block for the LLM prompt.

    For Python files we show functions + imports from the code graph.
    For non-Python files we fall back to metadata collected by multi_ast
    (language, chunk names / types) so the LLM still gets structural context.
    """
    graph_info = ""

    for file in retrieved_files:
        graph_info += f"\nFile: {file}\n"

        if file in graph and graph[file]:
            info = graph[file]
            graph_info += f"  Functions : {info.get('functions', [])}\n"
            graph_info += f"  Imports   : {info.get('imports',   [])}\n"
        elif metadata_lookup:
            # Build a mini-summary from chunk metadata for this file
            file_meta = [m for m in metadata_lookup if m.get("file") == file]
            if file_meta:
                lang   = file_meta[0].get("language", "unknown")
                names  = [m["name"] for m in file_meta if m.get("name") and m["name"] != m.get("type")]
                types  = list({m.get("type", "") for m in file_meta})
                graph_info += f"  Language  : {lang}\n"
                graph_info += f"  Block types: {types}\n"
                if names:
                    graph_info += f"  Identifiers: {names[:15]}\n"   # cap to 15

    return graph_info


# -------------------------------
# RANK CHUNKS
# -------------------------------
def rank_chunks(query, chunks):
    scored = []
    query_words = set(query.lower().split())

    for chunk in chunks:
        score = 0
        text  = chunk.lower()
        for word in query_words:
            if word in text:
                score += 2
        if "def " in text or "function " in text or "class " in text:
            score += 1
        scored.append((score, chunk))

    scored.sort(reverse=True)
    return [c for _, c in scored]

# -------------------------------
# FILE EXTRACTION
# -------------------------------
def extract_file_function_pairs(answer, graph, files):
    results     = []
    answer_lower = answer.lower()

    function_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', answer)
    function_matches = list(set(func.lower() for func in function_matches))

    for file in files:
        filename = file
        basename = re.split(r'[\\/]', file)[-1].lower()
        if basename not in answer_lower:
            continue

        graph_functions  = graph.get(file, {}).get("functions", [])
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
    seen   = set()
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
except Exception:
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

    index        = repo["index"]
    chunks       = repo["chunks"]
    metadata     = repo["metadata"]
    bm25         = repo["bm25"]
    files        = repo["files"]
    graph        = repo["graph"]
    symbol_table = repo["symbol_table"]
    call_graph   = repo["call_graph"]

    file_index = "\n".join([re.split(r'[\\/]', f)[-1] for f in files])

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
    results = run_hybrid_search(query, index, chunks, metadata, bm25)

    if not results or results[0]["score"] < 0.25:
        yield "data:Not enough relevant information.\n\n"
        return

    context_chunks, retrieved_files = expand_ctx(
        results, graph, symbol_table, call_graph
    )

    if not context_chunks:
        yield "data:No context found.\n\n"
        return

    # ── build formatted chunks with language hint ────────────────────────
    # metadata is a list of dicts; build a file→language lookup
    file_lang_map = {}
    for m in metadata:
        fpath = m.get("file", "")
        if fpath and "language" in m:
            file_lang_map[fpath] = m["language"]

    formatted_chunks = []
    for chunk, file in context_chunks:
        lang  = file_lang_map.get(file, "")
        label = f"[FILE: {file}]" + (f" [{lang.upper()}]" if lang else "")
        formatted_chunks.append(f"{label}\n{chunk}")

    ranked_chunks = rank_chunks(query, formatted_chunks)

    def limit_context(chunks, max_chars=3500):
        result = []
        total  = 0
        for chunk in chunks:
            if total + len(chunk) > max_chars:
                break
            result.append(chunk)
            total += len(chunk)
        return result

    selected_chunks = limit_context(ranked_chunks)
    context         = "\n\n".join(selected_chunks)

    # Pass metadata to graph-info builder so non-Python files also get structure
    graph_info = get_relevant_graph_info(
        graph,
        retrieved_files[:2],
        metadata_lookup=metadata
    )[:1200]

    prompt = f"""
You are an expert code assistant. Answer the user's question about their codebase clearly, accurately, and in a well-structured manner.

────────────────────────────────────
## 🧠 CORE BEHAVIOR
────────────────────────────────────
- Use ONLY the provided code context. Do NOT invent functions, files, or logic.
- If the answer is not present, say:
  "I don't have enough information to answer that."
- Always mention the file where a function/class is defined.
- Resolve references like "this", "that", "it" using conversation history.
- Each code chunk is labelled with its FILE and LANGUAGE (e.g. [FILE: app/index.js] [JAVASCRIPT]).
  Use the language label to interpret syntax correctly — do NOT assume Python for everything.

────────────────────────────────────
## ✨ RESPONSE STYLE (ChatGPT-like)
────────────────────────────────────
- Write in clean, natural paragraphs (4–6 sentences each).
- Use headings ONLY when needed.
- Keep answers structured but not robotic.

────────────────────────────────────
## 📝 FORMATTING RULES (STRICT)
────────────────────────────────────

### 1. Inline Highlighting
Use backticks ONLY for: function names, class names, file names, variables, libraries.

### 2. Code Blocks
Use fenced code blocks ONLY when showing actual code.
ALWAYS specify the correct language in the fence:

~~~javascript
function example() {{}}
~~~

~~~sql
SELECT * FROM users WHERE id = 1;
~~~

~~~html
<section class="hero">...</section>
~~~

STRICT RULES:
- NEVER wrap explanations inside code blocks
- NEVER use ~~~plaintext for normal text
- Choose the fence language to match the source file's language

### 3. Lists
Use bullet points ONLY when listing multiple items (3+).

────────────────────────────────────
## 🚫 COMMON MISTAKES (AVOID THESE)
────────────────────────────────────
❌ Assuming HTML/CSS/SQL/JS code is Python
❌ Wrapping explanations inside code fences
❌ Dumping raw code without explanation

✅ CORRECT:
The `getUserById` function in `routes/users.js` queries the database using a parameterised SQL statement.

────────────────────────────────────
## 🎯 OUTPUT GOAL
────────────────────────────────────
Your answer should look like a ChatGPT response:
- Clean paragraphs, minimal highlighting
- Code only where necessary, with the correct language fence
- Easy to read and professional

Conversation history:
{chr(10).join(chat_history[-6:])}

Codebase structure:
{graph_info}

Relevant code:
{context}

User question: {query}

Answer:
"""

    try:
        full_answer = ""

        for token in stream_llm(prompt):
            full_answer += token
            yield f"data:{token}\n\n"

        yield f"data:\n\n---\n\n\n\n"

        file_function_pairs = extract_file_function_pairs(full_answer, graph, files)
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

        try:
            with open("memory.json", "w") as f:
                json.dump(chat_history[-10:], f)
        except Exception:
            pass

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

    inner = os.listdir(path)
    if len(inner) == 1:
        inner_path = os.path.join(path, inner[0])
        if os.path.isdir(inner_path):
            for item in os.listdir(inner_path):
                shutil.move(os.path.join(inner_path, item), path)
            shutil.rmtree(inner_path)

    load_repository(path)
    return {"status": f"{repo_name} loaded"}

# -------------------------------
# UPLOAD GITHUB
# -------------------------------
@router.post("/upload-github")
async def upload_github(data: dict):
    url  = data.get("repo_url")
    name = url.split("/")[-1].replace(".git", "")
    path = os.path.join(UPLOAD_DIR, name)

    if os.path.exists(path):
        print("Repo already exists, reusing...")
    else:
        subprocess.run(["git", "clone", url, path], check=True)

    load_repository(path)
    return {"status": f"{name} loaded"}

# -------------------------------
# REPO STATUS
# -------------------------------
@router.get("/repo-status")
def repo_status():
    return {
        "loaded": current_repo["path"] is not None,
        "path":   current_repo["path"],
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
# SUMMARIZE
# -------------------------------
@router.post("/summarize-stream")
async def summarize_stream():
    repo  = current_repo
    files = repo["files"]
    graph = repo["graph"]

    if not files:
        return StreamingResponse(
            iter(["data:Please upload a repository first.\n\n"]),
            media_type="text/event-stream",
        )

    summary_context = ""
    for file in files[:10]:
        summary_context += f"\nFile: {file}"
        if file in graph and graph[file]:
            summary_context += f"\nFunctions: {graph[file].get('functions', [])}"
            summary_context += f"\nImports  : {graph[file].get('imports',   [])}\n"
        else:
            # non-Python: pull from metadata
            file_meta = [m for m in repo.get("metadata", []) if m.get("file") == file]
            if file_meta:
                lang  = file_meta[0].get("language", "unknown")
                names = [m["name"] for m in file_meta if m.get("name")][:10]
                summary_context += f"\nLanguage: {lang} | Identifiers: {names}\n"

    prompt = f"""
You are an expert code assistant. Generate a clear, structured summary of the given codebase.

────────────────────────────────────
## 🧠 CORE BEHAVIOR
────────────────────────────────────
- Use ONLY the provided code context. Do NOT invent files, modules, or logic.
- If information is missing, state:
  "Some parts of the codebase are not available in the provided context."
- Focus on explaining how the system works overall (not line-by-line code).

────────────────────────────────────
## ✨ RESPONSE STYLE (ChatGPT-like)
────────────────────────────────────
- Write in clean, natural paragraphs (4–6 sentences each).
- Use headings to organize sections clearly.

────────────────────────────────────
## 📝 FORMATTING RULES (STRICT)
────────────────────────────────────

### 1. Structure (REQUIRED)
## Overview
## Main Components
## Data Flow
## Key Technologies
## Notable Logic
## Observations (Optional)

### 2. Inline Highlighting
Use backticks ONLY for: function names, class names, file names, variables, libraries.

### 3. Code Blocks
RARELY needed in summaries. When used, always specify the correct language.

────────────────────────────────────
## 🎯 OUTPUT GOAL
────────────────────────────────────
Your summary should feel like a professional technical overview written by a senior developer.

Codebase data:
{summary_context}
"""

    def generate():
        try:
            for token in stream_llm(prompt):
                yield f"data:{token}\n\n"
        except Exception as e:
            yield f"data:Error: {str(e)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
