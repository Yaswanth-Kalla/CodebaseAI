"""
multi_ast.py — Deep AST-based chunking for all supported file types.

Strategy per language:
  - Python / JS / Java / C / C++  → tree-sitter: extract functions, classes, methods
  - HTML / EJS                    → tag-aware block splitting (script/style/body sections)
  - XML                           → element-level chunks
  - SQL                           → statement-level chunks (CREATE, SELECT, INSERT …)
  - CSS                           → rule-block chunks
  - Jupyter (.ipynb)              → cell-level chunks (handled upstream in chat.py)

For every language the chunk dict always carries:
  { type, name, file, code, language, start_line, end_line }

`name` is the human-readable identifier (function/class name, tag, statement type …).
This rich metadata is used by vector_store.py and context_expander.py to build better
embeddings and graph information for non-Python files.
"""

import re

# ── optional tree-sitter ────────────────────────────────────────────────────
try:
    from tree_sitter_languages import get_parser as _ts_get_parser   # renamed to avoid collision
    _TS_AVAILABLE = True
except Exception:
    _TS_AVAILABLE = False

MAX_CHARS = 3000        # hard cap per chunk
CONTEXT_WINDOW = 400   # bytes of surrounding context to include


# ════════════════════════════════════════════════════════════════════════════
# LANGUAGE MAP
# ════════════════════════════════════════════════════════════════════════════

LANGUAGE_MAP = {
    ".py":   "python",
    ".js":   "javascript",
    ".ts":   "typescript",
    ".jsx":  "javascript",
    ".tsx":  "typescript",
    ".java": "java",
    ".c":    "c",
    ".cpp":  "cpp",
    ".cc":   "cpp",
    ".cs":   "c_sharp",
    ".go":   "go",
    ".rb":   "ruby",
    ".rs":   "rust",
    ".php":  "php",
    ".html": "html",
    ".ejs":  "html",          # tree-sitter-html parses EJS fine
    ".xml":  "xml",
    ".sql":  "sql",
    ".css":  None,            # no good tree-sitter-css in tree_sitter_languages
}

# node types that represent top-level "interesting" blocks per language
_TS_NODE_TYPES = {
    "python":     {"function_definition", "class_definition", "decorated_definition"},
    "javascript": {"function_declaration", "arrow_function", "function_expression",
                   "method_definition", "class_declaration"},
    "typescript": {"function_declaration", "arrow_function", "function_expression",
                   "method_definition", "class_declaration", "interface_declaration",
                   "type_alias_declaration"},
    "java":       {"method_declaration", "class_declaration", "interface_declaration",
                   "constructor_declaration"},
    "c":          {"function_definition", "struct_specifier", "enum_specifier"},
    "cpp":        {"function_definition", "class_specifier", "struct_specifier",
                   "namespace_definition", "template_declaration"},
    "c_sharp":    {"method_declaration", "class_declaration", "interface_declaration",
                   "constructor_declaration", "property_declaration"},
    "go":         {"function_declaration", "method_declaration", "type_declaration"},
    "ruby":       {"method", "singleton_method", "class", "module"},
    "rust":       {"function_item", "impl_item", "struct_item", "trait_item",
                   "enum_item", "mod_item"},
    "php":        {"function_definition", "method_declaration", "class_declaration"},
    "html":       {"element", "script_element", "style_element"},
    "xml":        {"element"},
    "sql":        {"select_statement", "create_table_statement",
                   "insert_statement", "update_statement",
                   "delete_statement", "create_function_statement",
                   "create_procedure_statement"},
}


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _ext(file_path: str) -> str:
    return "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""


def _line_of(code: str, byte_offset: int) -> int:
    return code[:byte_offset].count("\n") + 1


def _get_ts_parser(file_path: str):
    if not _TS_AVAILABLE:
        return None, None

    lang = LANGUAGE_MAP.get(_ext(file_path))
    if not lang:
        return None, None

    try:
        parser = _ts_get_parser(lang)

        # Handle tuple return
        if isinstance(parser, tuple):
            parser = parser[0]

        # 🔥 CRITICAL FIX for new versions
        if not hasattr(parser, "parse"):
            return None, None

        return parser, lang

    except Exception as e:
        print(f"[multi_ast] Parser unavailable for {file_path}: {e}")
        return None, None

def _name_from_node(node, code: str) -> str:
    """Best-effort: extract the identifier/name of a tree-sitter node."""
    # Walk immediate children looking for an 'identifier' or 'name' node
    for child in node.children:
        if child.type in ("identifier", "name", "type_identifier",
                          "property_identifier", "field_identifier"):
            return code[child.start_byte:child.end_byte]
    # Fallback: use node type
    return node.type


def _make_chunk(node, code: str, file_path: str, lang: str) -> dict:
    start = node.start_byte
    end   = node.end_byte
    snippet = code[start:end]
    before  = code[max(0, start - CONTEXT_WINDOW): start]
    after   = code[end: end + CONTEXT_WINDOW]
    full    = (before + snippet + after)[:MAX_CHARS * 2]

    return {
        "type":       node.type,
        "name":       _name_from_node(node, code),
        "file":       file_path,
        "language":   lang,
        "code":       full,
        "start_line": _line_of(code, start),
        "end_line":   _line_of(code, end),
    }


# ════════════════════════════════════════════════════════════════════════════
# TREE-SITTER CHUNKER  (Python, JS/TS, Java, C/C++, Go, Rust, Ruby …)
# ════════════════════════════════════════════════════════════════════════════

def chunk_with_ast(file_path: str) -> list:
    """
    Use tree-sitter to extract meaningful top-level blocks.
    Returns [] if tree-sitter is unavailable or the language is unsupported.
    """
    parser, lang = _get_ts_parser(file_path)
    if parser is None:
        return []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except Exception:
        return []

    tree = parser.parse(code.encode("utf-8"))
    root  = tree.root_node
    target_types = _TS_NODE_TYPES.get(lang, set())
    chunks: list = []

    def _walk(node):
        if node.type in target_types:
            chunks.append(_make_chunk(node, code, file_path, lang))
            # still descend — e.g. nested classes in Python
        for child in node.children:
            _walk(child)

    _walk(root)
    return chunks


# ════════════════════════════════════════════════════════════════════════════
# HTML / EJS CHUNKER  — section-aware
# ════════════════════════════════════════════════════════════════════════════

# Sections we care about in HTML/EJS
_HTML_SECTION_RE = re.compile(
    r'(<(script|style|head|body|header|footer|main|nav|section|article|form|table)'
    r'[\s>].*?</\2>)',
    re.DOTALL | re.IGNORECASE
)

def chunk_html_like(file_path: str) -> list:
    """
    Split HTML/EJS into meaningful sections (script, style, body, …).
    Falls back to fixed-size sliding window if no sections found.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return []

    chunks = []

    # 1. Try tree-sitter HTML first
    if _TS_AVAILABLE:
        ts_chunks = chunk_with_ast(file_path)
        if ts_chunks:
            return ts_chunks

    # 2. Regex section extraction
    for m in _HTML_SECTION_RE.finditer(text):
        tag   = m.group(2).lower()
        block = m.group(1)[:MAX_CHARS * 2]
        line  = text[:m.start()].count("\n") + 1
        chunks.append({
            "type":       f"html_{tag}",
            "name":       tag,
            "file":       file_path,
            "language":   "html",
            "code":       block,
            "start_line": line,
            "end_line":   line + block.count("\n"),
        })

    if chunks:
        return chunks

    # 3. Fixed-size fallback
    for i in range(0, len(text), MAX_CHARS*2):
        part = text[i: i + MAX_CHARS*2]
        chunks.append({
            "type":       "html_block",
            "name":       f"block_{i}",
            "file":       file_path,
            "language":   "html",
            "code":       part,
            "start_line": text[:i].count("\n") + 1,
            "end_line":   text[:i + len(part)].count("\n") + 1,
        })

    return chunks


# ════════════════════════════════════════════════════════════════════════════
# CSS CHUNKER  — rule-block aware
# ════════════════════════════════════════════════════════════════════════════

_CSS_RULE_RE = re.compile(r'([^{}]+\{[^{}]*\})', re.DOTALL)

def chunk_css(file_path: str) -> list:
    """Split CSS into individual rule blocks."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return []

    chunks = []
    for m in _CSS_RULE_RE.finditer(text):
        block    = m.group(1).strip()[:MAX_CHARS*2]
        selector = block.split("{")[0].strip()[:80]
        line     = text[:m.start()].count("\n") + 1
        chunks.append({
            "type":       "css_rule",
            "name":       selector,
            "file":       file_path,
            "language":   "css",
            "code":       block,
            "start_line": line,
            "end_line":   line + block.count("\n"),
        })

    return chunks or _chunk_plain(file_path, "css")


# ════════════════════════════════════════════════════════════════════════════
# SQL CHUNKER  — statement-aware
# ════════════════════════════════════════════════════════════════════════════

# Split on statement boundaries (semicolons or GO keyword)
_SQL_STMT_RE = re.compile(r'(.*?)(;|\bGO\b)', re.DOTALL | re.IGNORECASE)

def chunk_sql(file_path: str) -> list:
    """Split SQL into individual statements."""
    # Try tree-sitter first
    if _TS_AVAILABLE:
        ts_chunks = chunk_with_ast(file_path)
        if ts_chunks:
            return ts_chunks

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return []

    chunks = []
    for m in _SQL_STMT_RE.finditer(text):
        stmt = (m.group(1) + m.group(2)).strip()
        if len(stmt) < 5:
            continue
        # derive a human name from the first meaningful keyword + object
        name_match = re.match(
            r'(CREATE\s+(?:TABLE|FUNCTION|PROCEDURE|VIEW|INDEX)'
            r'|SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|DROP\s+\w+)'
            r'\s+(\S+)?',
            stmt, re.IGNORECASE
        )
        name = name_match.group(0)[:60] if name_match else "sql_statement"
        line = text[:m.start()].count("\n") + 1
        chunks.append({
            "type":       "sql_statement",
            "name":       name.strip(),
            "file":       file_path,
            "language":   "sql",
            "code":       stmt[:MAX_CHARS*2],
            "start_line": line,
            "end_line":   line + stmt.count("\n"),
        })

    return chunks or _chunk_plain(file_path, "sql")


# ════════════════════════════════════════════════════════════════════════════
# PLAIN / FALLBACK CHUNKER
# ════════════════════════════════════════════════════════════════════════════

def _chunk_plain(file_path: str, language: str = "text") -> list:
    """Fixed-size sliding window — last resort."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except Exception:
        return []

    chunks = []
    for i in range(0, len(code), MAX_CHARS*2):
        part = code[i: i + MAX_CHARS*2]
        chunks.append({
            "type":       "partial",
            "name":       f"part_{i}",
            "file":       file_path,
            "language":   language,
            "code":       part,
            "start_line": code[:i].count("\n") + 1,
            "end_line":   code[:i + len(part)].count("\n") + 1,
        })
    return chunks


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

def chunk_file(file_path: str) -> list:
    """
    Main dispatcher. Returns a list of chunk dicts for *any* supported file.

    Priority:
      1. tree-sitter AST  (Python, JS/TS, Java, C/C++, Go, Rust, Ruby, PHP, HTML, XML, SQL)
      2. Language-specific regex chunker  (HTML/EJS, CSS, SQL fallback)
      3. Fixed-size plain fallback
    """
    ext = _ext(file_path)

    # ── files with direct tree-sitter support ────────────────────────────
    if ext in (".py", ".js", ".ts", ".jsx", ".tsx",
               ".java", ".c", ".cpp", ".cc",
               ".cs", ".go", ".rb", ".rs", ".php",
               ".xml"):
        chunks = chunk_with_ast(file_path)
        if chunks:
            return chunks
        # tree-sitter unavailable → plain fallback
        return _chunk_plain(file_path, LANGUAGE_MAP.get(ext, "text"))

    # ── HTML / EJS ────────────────────────────────────────────────────────
    if ext in (".html", ".ejs"):
        return chunk_html_like(file_path)

    # ── CSS ───────────────────────────────────────────────────────────────
    if ext == ".css":
        return chunk_css(file_path)

    # ── SQL ───────────────────────────────────────────────────────────────
    if ext == ".sql":
        return chunk_sql(file_path)

    # ── everything else (plain text fallback) ────────────────────────────
    return _chunk_plain(file_path, "text")