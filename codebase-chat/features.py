import re

# -------------------------------
# Show Code References
# -------------------------------
def show_code_references(context_chunks):
    refs = []
    for chunk in context_chunks:
        if "[FILE:" in chunk:
            file = chunk.split("]")[0].replace("[FILE:", "").strip()
            lines = chunk.split("\n")
            if len(lines) > 1:
                first_line = lines[1]
                refs.append(f"- {file} → {first_line}")
    return list(set(refs))


# -------------------------------
# Explain File
# -------------------------------
def explain_file(graph, file, all_files):
    matches = [f for f in all_files if file.lower() in f.lower()]

    if not matches:
        return "File not found in codebase."

    file = matches[0]

    if file not in graph:
        return "File not found in graph."

    info = graph[file]

    return f"""
File: {file}

Functions:
{info['functions']}

Imports:
{info['imports']}
"""


# -------------------------------
# List Functions
# -------------------------------
def list_all_functions(graph):
    output = []

    for file, info in graph.items():
        if info["functions"]:
            output.append(f"\n{file}:")
            for fn in info["functions"]:
                output.append(f"  - {fn}")

    return "\n".join(output)


# -------------------------------
# Find Definition (FIXED)
# -------------------------------
def find_definition(symbol_table, name):
    import re

    name = name.lower()
    name = re.sub(r'[^a-zA-Z0-9_ ]', '', name)
    name = name.replace(" ", "_").strip()

    # direct match
    if name in symbol_table:
        return f"{name} → {symbol_table[name]}"

    # partial match
    for func in symbol_table:
        if name in func:
            return f"{func} → {symbol_table[func]}"

    for func in symbol_table:
        if func in name:
            return f"{func} → {symbol_table[func]}"

    return "Not found in codebase."


# -------------------------------
# Call Chain
# -------------------------------
def get_call_chain(func, call_graph):
    func = func.strip().lower()

    func = re.sub(r'[^a-zA-Z0-9_]', '', func)

    if func not in call_graph:
        return "Function not found."

    visited = set()
    chain = []

    def dfs(f):
        if f in visited:
            return
        visited.add(f)
        chain.append(f)

        for c in call_graph.get(f, []):
            dfs(c)

    dfs(func)

    return " → ".join(chain)


# -------------------------------
# API Extractor
# -------------------------------
def extract_api_endpoints(files):
    endpoints = []

    for file in files:
        if not file.endswith(".py"):
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                code = f.read()

            for line in code.splitlines():
                line = line.strip()
                if "@app.get" in line or "@app.post" in line:
                    endpoints.append(f"{file} → {line}")

        except:
            continue

    return "\n".join(endpoints) if endpoints else "No APIs found."