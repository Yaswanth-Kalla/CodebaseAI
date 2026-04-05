import ast

def build_code_graph(files):
    graph = {}
    symbol_table = {}
    call_graph = {}

    for file in files:
        graph[file] = {"functions": [], "imports": []}

        if not file.endswith(".py"):
            continue

        try:
            with open(file, "r", encoding="utf-8") as f:
                code = f.read()

            tree = ast.parse(code)

            for node in ast.walk(tree):

                # FUNCTIONS
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name.strip().lower()

                    graph[file]["functions"].append(func_name)
                    symbol_table[func_name] = file
                    call_graph[func_name] = []

                    # FIND CALLS
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Call):

                            called = None

                            if isinstance(sub.func, ast.Name):
                                called = sub.func.id.lower()

                            elif isinstance(sub.func, ast.Attribute):
                                called = sub.func.attr.lower()

                            if called:
                                call_graph[func_name].append(called)

                # IMPORTS
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        graph[file]["imports"].append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        graph[file]["imports"].append(alias.name)

        except:
            continue

    # 🔥 FILTER CALL GRAPH → ONLY INTERNAL FUNCTIONS
    for func in call_graph:
        call_graph[func] = [
            f for f in call_graph[func] if f in symbol_table
        ]

    return graph, symbol_table, call_graph