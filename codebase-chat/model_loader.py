import os
import google.generativeai as genai
import cohere

# -------------------------------
# GLOBAL SWITCH
# -------------------------------
USE_GEMINI = True

# -------------------------------
# INIT CLIENTS
# -------------------------------

def init_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("❌ GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)


co = cohere.Client(os.getenv("COHERE_API_KEY"))

# -------------------------------
# EMBEDDING FUNCTION
# -------------------------------

def embed_texts(texts):
    global USE_GEMINI

    # 🔥 TRY GEMINI ONLY IF ENABLED
    if USE_GEMINI:
        try:
            init_gemini()

            res = genai.embed_content(
                model="models/gemini-embedding-001",
                content=texts
            )

            return res["embedding"]

        except Exception as e:
            error_str = str(e)
            print("⚠️ Gemini embedding failed:", error_str)

            if "quota" in error_str.lower() or "429" in error_str:
                print("🚫 Disabling Gemini for this session...")
                USE_GEMINI = False   # 🔥 KEY FIX
            else:
                raise e

    # 🔥 FALLBACK TO COHERE (DIRECTLY)
    try:
        print("🔁 Using Cohere embeddings...")

        response = co.embed(
            texts=texts,
            model="embed-english-v3.0",
            input_type="search_document"
        )

        return response.embeddings

    except Exception as cohere_error:
        print("❌ Cohere embedding failed:", cohere_error)

        # 🔥 FINAL SAFE FALLBACK
        dim = 1024
        return [[0.0] * dim for _ in texts]
