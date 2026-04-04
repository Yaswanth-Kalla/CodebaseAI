def load_code_snippet(file_path, start, end):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[start:end])
    except:
        return ""


def expand_context(results, graph, symbol_table, call_graph, max_extra_files=3):
    context_chunks  = []
    retrieved_files = []
    seen_files      = set()
    visited_funcs   = set()
    extra_files     = 0

    def _add_file(f):
        if f and f not in seen_files:
            seen_files.add(f)
            retrieved_files.append(f)

    for item in results:
        meta = item.get("meta")
        if not meta:
            continue

        file = meta.get("file")

        # 🔥 LOAD ACTUAL CODE FROM FILE
        snippet = load_code_snippet(
            file,
            meta.get("start_line", 0),
            meta.get("start_line", 0) + 100
        )

        if not snippet.strip():
            continue

        context_chunks.append((snippet, file))
        _add_file(file)

        # 🔥 CALL GRAPH EXPANSION (unchanged logic)
        if not graph or not symbol_table or not call_graph:
            continue

        file_info = graph.get(file, {})
        for func in file_info.get("functions", []):
            if func in visited_funcs:
                continue
            visited_funcs.add(func)

            for called in call_graph.get(func, []):
                if extra_files >= max_extra_files:
                    break

                dep_file = symbol_table.get(called)

                if dep_file and dep_file not in seen_files:
                    dep_snippet = load_code_snippet(dep_file, 0, 200)

                    if dep_snippet.strip():
                        context_chunks.append((dep_snippet, dep_file))
                        _add_file(dep_file)
                        extra_files += 1

    return context_chunks, retrieved_files
