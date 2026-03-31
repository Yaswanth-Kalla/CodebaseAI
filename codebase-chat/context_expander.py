def expand_context(results, graph, symbol_table, call_graph):
    context_chunks = []
    retrieved_files = set()
    visited_functions = set()

    for item in results:

        # 🔥 YOUR ACTUAL FORMAT
        chunk = item.get("chunk")
        file = item.get("file")

        if not chunk:
            continue

        context_chunks.append((chunk, file))

        if file:
            retrieved_files.add(file)

            file_info = graph.get(file, {})
            functions = file_info.get("functions", [])

            # 🔥 Call graph expansion
            for func in functions:
                if func in call_graph and func not in visited_functions:
                    visited_functions.add(func)

                    for called in call_graph[func]:
                        if called in symbol_table:
                            dep_file = symbol_table[called]
                            retrieved_files.add(dep_file)

    return context_chunks, list(retrieved_files)