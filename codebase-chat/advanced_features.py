# advanced_features.py

def merge_flow_and_explanation(flow, explanation):
    return f"""
🔗 Execution Flow:
{flow}

🧠 Explanation:
{explanation}
"""


def merge_multiple_flows(flows):
    output = "🔗 Combined Execution Flow:\n"
    for f in flows:
        output += f"- {f}\n"
    return output


def highlight_code(context_chunks):
    snippets = []

    for chunk in context_chunks[:3]:
        lines = chunk.split("\n")
        if len(lines) > 1:
            code = "\n".join(lines[1:6])
            snippets.append(code)

    return "\n\n".join(snippets)


def detect_possible_issues(context_chunks):
    issues = []
    text = " ".join(context_chunks).lower()

    if "train_model" in text and "predict" in text:
        issues.append("⚠️ Training logic mixed with prediction")

    if "smote" in text and "test" in text:
        issues.append("⚠️ Possible data leakage (SMOTE before split)")

    if not issues:
        return "✅ No obvious issues detected"

    return "\n".join(issues)


def build_ascii_flow(flow):
    parts = flow.split(" → ")
    graph = ""

    for i, p in enumerate(parts):
        graph += p
        if i < len(parts) - 1:
            graph += "\n   ↓\n"

    return graph