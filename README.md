# CodebaseAI - AI-Powered Codebase Explorer

CodebaseAI is an intelligent, production-ready RAG (Retrieval-Augmented Generation) system that enables developers to **intelligently chat with, analyze, and navigate large code repositories**. It combines state-of-the-art semantic search with BM25 keyword matching to retrieve the most relevant code snippets, then streams AI-powered insights using advanced LLMs. Perfect for code understanding, documentation generation, bug hunting, and rapid codebase navigation across projects of any size.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![React](https://img.shields.io/badge/React-18+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)

### 🌐 Live Demo
**[CodebaseAI - Beta](https://codebase-ai-beta.vercel.app)** - Try the live deployment now!

## 🚀 Features

- **🔍 Hybrid Search Engine**: Combines semantic search (70% weight) + BM25 keyword search (30% weight) for highly accurate code retrieval
- **🧠 Advanced Embeddings**: Supports Gemini Embeddings and Cohere Embeddings for powerful semantic understanding, paired with FAISS for lightning-fast vector similarity matching
- **🌳 Multi-AST Parser**: Language-aware code chunking using AST parsing for 20+ file types (Python, JavaScript, TypeScript, Java, Go, Rust, C++, C#, PHP, Ruby, SQL, etc.) with intelligent fallback to regex
- **🤖 LLM Integrations**: Dual LLM support with Gemini (primary) and Groq (fallback) for robust AI responses with streaming capabilities
- **Multi-Language Support**: Intelligent parsing of code from 20+ languages with appropriate syntax highlighting
- **AI-Powered Responses**: Streams responses using Google Gemini with automatic failover to Groq
- **Code Analysis Features**: 
  - Explain files and functions
  - Find function definitions
  - Trace call chains
  - List all functions in a file
- **Interactive UI**: React-based chat interface with file explorer and code viewer
- **Repository Indexing**: Automatic FAISS vector indexing for lightning-fast semantic search
- **Context Expansion**: Intelligently expands search results with related code chunks

## 🏗️ Architecture

### Data Processing Pipeline
```
      ┌──────────────────────────────────────────────────────────────┐
      │                  📤 FILE UPLOAD & INDEXING                   │
      └──────────────────────────────────────────────────────────────┘
                            ↓
      ┌──────────────────────────────────────────────────────────────┐
      │    2️⃣  CODE CHUNKING WITH MULTI-AST PARSER 🌳               │
      │  • Language-aware AST parsing (Python, JS, TS, Java, etc.)   │
      │  • Intelligent code splitting respecting syntax boundaries   │
      │  • Regex fallback for unsupported file types                 │
      │  • Preserves context and semantic meaning                    │
      └──────────────────────────────────────────────────────────────┘
                            ↓
      ┌──────────────────────────────────────────────────────────────┐
      │        3️⃣  EMBEDDINGS GENERATION & STORAGE 🧠               │
      │  • Gemini Embeddings or Cohere Embeddings encoding           │
      │  • Batch processing for efficiency                           │
      │  • FAISS vector index creation                               │
      │  • Metadata storage (file paths, line numbers)               │
      └──────────────────────────────────────────────────────────────┘
                            ↓
      ┌──────────────────────────────────────────────────────────────┐
      │              📊 HYBRID SEARCH & RETRIEVAL 🔍                 │
      │     ┌─────────────────────────────────────────────────┐      │
      │     │ Semantic Search (70%) - FAISS Vector Matching  │      │
      │     │ + Keyword Search (30%) - BM25 Ranking          │      │
      │     │ = Combined Ranked Results (Top-K)              │      │
      │     └─────────────────────────────────────────────────┘      │
      └──────────────────────────────────────────────────────────────┘
                            ↓
      ┌──────────────────────────────────────────────────────────────┐
      │   4️⃣  CONTEXT EXPANSION & PROMPT BUILDING                   │
      │  • Retrieve top code chunks matching query                   │
      │  • Expand context with related code                          │
      │  • Build comprehensive prompt for LLM                        │
      └──────────────────────────────────────────────────────────────┘
                            ↓
      ┌──────────────────────────────────────────────────────────────┐
      │       5️⃣  LLM INTEGRATION & RESPONSE GENERATION 🤖           │
      │  • Primary: Google Gemini API                                │
      │  • Fallback: Groq API (if Gemini fails)                      │
      │  • Stream response chunks for real-time feedback             │
      │  • Support for follow-up context                             │
      └──────────────────────────────────────────────────────────────┘
                            ↓
      ┌──────────────────────────────────────────────────────────────┐
      │          6️⃣  CHAT STREAM & USER INTERFACE 💬               │
      │  • FastAPI /chat-stream endpoint (Server-Sent Events)        │
      │  • Real-time response streaming to React frontend            │
      │  • Markdown rendering with syntax highlighting               │
      │  • File viewer with code context                             │
      └──────────────────────────────────────────────────────────────┘
```

### System Architecture
```
┌──────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                       │
│         Chat.jsx | FileExplorer.jsx | FileViewer.jsx            │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP/SSE Stream
┌────────────────────────▼─────────────────────────────────────────┐
│                   FastAPI Backend (main.py)                      │
│               /chat-stream, /upload-repo routes                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
   │ Code      │  │  Hybrid   │  │ LLM Stream  │
   │ Processing│  │  Search   │  │ Integration │
   │           │  │           │  │             │
   │• multi_ast│  │• FAISS    │  │• Gemini     │
   │• Chunking │  │ (70%)     │  │• Groq       │
   │• Embedding│  │• BM25     │  │• Streaming  │
   │  (model)  │  │ (30%)     │  │             │
   └───────────┘  │• Retrieval│  └─────────────┘
                  └───────────┘
```

## ⚡ Quick Start

### Backend Setup

1. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or: source .venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file in the `codebase-chat` directory:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   COHERE_API_KEY=your_api_key
   PORT=8000
   ```

4. **Run the backend:**
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to UI directory:**
   ```bash
   cd ../codebase-ui
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```
   The UI will be available at `http://localhost:5173`

## 🎯 Usage

1. Open the application in your browser (frontend URL above)
2. Upload a repository or select one from the file explorer
3. Ask questions about the codebase in the chat interface
4. View relevant code files and their relationships

### Example Queries

- "What does the main authentication module do?"
- "Find all API endpoints in this repository"
- "Explain how the payment processing works"
- "Show me the call chain for the user registration flow"
- "List all database models and their relationships"

## 📁 Project Structure

```
codebase-chat/                    # Python Backend
├── main.py                        # FastAPI entry point
├── chat.py                        # Core orchestrator
├── hybrid_search.py               # Semantic + keyword search
├── vector_store.py                # FAISS vector indexing
├── file_loader.py                 # Code file discovery
├── features.py                    # Code analysis helpers
├── code_graph.py                  # Call graph builder (optional)
├── multi_ast.py                   # Language-specific AST parsing
├── model_loader.py                # Embedding model management
├── requirements.txt               # Python dependencies
└── data/                          # Runtime data
    ├── uploaded_repos/            # User-uploaded repositories
    └── faiss_index/               # Vector indexes

codebase-ui/                      # React Frontend
├── src/
│   ├── App.jsx                   # Main application shell
│   ├── components/
│   │   ├── Chat.jsx              # Chat interface
│   │   ├── FileExplorer.jsx       # File browser
│   │   ├── FileViewer.jsx         # Code viewer
│   │   └── GraphView.jsx          # Graph visualization
│   ├── main.jsx                  # React entry point
│   └── App.css                   # Styling
├── package.json                  # Node dependencies
├── vite.config.js                # Vite configuration
└── tailwind.config.js            # Tailwind CSS config
```

## 🔧 Core Modules

### chat.py
- **Primary coordinator** for the entire system
- Manages global state (current repo, FAISS index, files)
- Orchestrates search → LLM response pipeline
- Handles repository uploads and indexing

### hybrid_search.py
- Implements **weighted hybrid search**: 70% semantic + 30% keyword
- Uses FAISS for semantic similarity matching
- Uses BM25 for keyword-based ranking
- Returns combined ranked results

### vector_store.py
- Creates and manages FAISS indexes
- Handles batch embedding generation
- Persistently stores metadata and indexes

### file_loader.py
- Walks repository directories
- Identifies code files across 20+ languages
- Filters out non-text files and dependencies

### multi_ast.py
- Language-specific code chunking using AST
- Supports Python, JavaScript, TypeScript, Java, Go, Rust, C++, SQL, etc.
- Falls back to regex-based chunking for unsupported languages

### features.py
- `explain_file()` - Summarize file purpose
- `list_all_functions()` - Extract all functions/classes
- `find_definition()` - Locate symbol definitions
- `get_call_chain()` - Trace function call paths

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/chat-stream` | Stream LLM response for a query |
| POST | `/upload-repo` | Upload and index a new repository |
| GET | `/repo-files` | List files in current repository |
| POST | `/set-repo` | Switch active repository |
| GET | `/features` | Get available code analysis features |

## 🤖 Supported Languages

Python, JavaScript, TypeScript, Java, Go, Rust, C++, C#, PHP, Ruby, SQL, HTML, CSS, JSON, XML, YAML, and more via regex fallback.

## ⚙️ Configuration

### Environment Variables

```bash
# API Keys
GEMINI_API_KEY=your_key         # Required: Google Gemini API
GROQ_API_KEY=your_key           # Fallback: Groq API
COHERE_API_KEY=your_api_key     # Fallback: Cohere API     

# Server
PORT=8000                       # Backend server port
CORS_ORIGINS=*                  # CORS allowed origins

# Search
SEARCH_TOP_K=10                 # Number of results to retrieve
CONTEXT_EXPANSION=true          # Enable context expansion

# Model
EMBEDDING_MODEL=gemini           # Gemini Embeddings or cohere
CHUNK_SIZE=1000                 # Code chunk size
```

## 🧪 Testing

Run the backend with test queries:

```bash
python -c "from chat import query_codebase; print(query_codebase('What does this repo do?'))"
```

##  Troubleshooting

| Issue | Solution |
|-------|----------|
| FAISS index not found | Re-upload the repository or rebuild index |
| API key errors | Check `.env` file and verify API credentials |
| Out of memory | Reduce `SEARCH_TOP_K` or `CHUNK_SIZE` |
| Slow search | Ensure FAISS index exists in `data/faiss_index/` |
| LLM timeouts | Switch to Groq or increase timeout settings |


## 📧 Support

For issues, questions, or suggestions, please open an issue on the repository.

---

**Happy coding with CodebaseAI! 🚀**
