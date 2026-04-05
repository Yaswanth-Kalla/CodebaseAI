def expand_context(results, graph, symbol_table, call_graph, max_extra_files=3):
    """
    Build context chunks + the set of files they came from.

    Changes vs original:
    - Deduplicates chunks (same text can appear via both semantic and keyword paths)
    - Caps call-graph expansion to `max_extra_files` so the prompt doesn't balloon
    - Handles missing graph / symbol_table gracefully (non-Python repos)
    """
    context_chunks  = []
    seen_chunks     = set()
    retrieved_files = []
    seen_files      = set()
    visited_funcs   = set()
    extra_files     = 0

    def _add_file(f):
        if f and f not in seen_files:
            seen_files.add(f)
            retrieved_files.append(f)

    for item in results:
        chunk = item.get("chunk")
        file  = item.get("file")

        if not chunk:
            continue

        # Deduplicate identical chunk text
        chunk_key = chunk.strip()
        if chunk_key in seen_chunks:
            continue
        seen_chunks.add(chunk_key)

        context_chunks.append((chunk, file))
        _add_file(file)

        # Call-graph expansion (Python only — graph may be empty for other langs)
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
                    _add_file(dep_file)
                    extra_files += 1

    return context_chunks, retrieved_files