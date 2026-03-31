def print_retrieval_debug(retrieved_files, graph):
    print("\n📂 Retrieved Files:")
    for f in retrieved_files:
        print(" -", f)

    print("\n🔗 Dependencies:")
    for f in retrieved_files:
        if f in graph:
            print(f"\n{f}")
            print("Imports:", graph[f]["imports"])


def check_missing_dependencies(retrieved_files, graph, symbol_table):
    missing = []

    for file in retrieved_files:
        imports = graph[file]["imports"]

        for imp in imports:
            # ✅ skip external libs (simple heuristic)
            if imp[0].islower():  # numpy, pandas, sklearn
                continue

            # ✅ check only internal symbols
            if imp not in symbol_table:
                missing.append(imp)

    return list(set(missing))