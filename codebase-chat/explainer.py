import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


def explain_code(code, question="Explain this code"):
    prompt = f"""
You are a senior software engineer.

Explain the following code clearly.

RULES:
- Explain purpose first
- Then explain step-by-step logic
- Keep it simple and structured
- Do NOT assume missing parts

Code:
{code}

Question:
{question}

Explanation:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    if "response" in data:
        return data["response"]
    else:
        return f"Error: {data}"