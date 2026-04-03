print("🔥 MAIN STARTING...")
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# 🔥 IMPORTANT: import dynamic state instead
from chat import stream_answer
from chat import router as chat_router
import chat

print("🔥 IMPORTS DONE")


app = FastAPI()
print("🔥 FASTAPI CREATED")

# -------------------------------
# CORS
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://codebase-ai-seven.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# REQUEST MODEL
# -------------------------------
class QueryRequest(BaseModel):
    query: str

# -------------------------------
# STREAM CHAT
# -------------------------------
@app.post("/chat-stream")
async def chat_stream(req: QueryRequest):
    return StreamingResponse(
        stream_answer(req.query),
        media_type="text/event-stream"
    )

# -------------------------------
# FILES LIST (FIXED)
# -------------------------------
@app.get("/files")
# @app.get("/files")
def get_files():
    repo = chat.current_repo

    if not repo or not repo.get("files"):
        print("FILES EMPTY DEBUG:", repo)
        return []

    return [
        {"file": f, "function": None}
        for f in repo["files"]
    ]

# -------------------------------
# FILE CONTENT (FIXED FOR IPYNB)
# -------------------------------
@app.get("/file-content")
def get_file_content(path: str):
    from chat import parse_ipynb  # reuse your function

    try:
        if path.endswith(".ipynb"):
            content = parse_ipynb(path)
        else:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        return {"content": content}

    except Exception as e:
        return {"content": str(e)}

# -------------------------------
# INCLUDE CHAT ROUTES
# -------------------------------
app.include_router(chat_router)

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)




# from fastapi import FastAPI

# print("🔥 APP STARTING")

# app = FastAPI()

# @app.get("/")
# def root():
#     return {"status": "working"}
