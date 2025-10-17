# Vector Project - Complete Setup Guide

## 🎯 Overview

The **Vector** project is a production-ready RAG (Retrieval-Augmented Generation) system with:
- **FastAPI REST API** for programmatic access
- **Gradio Web UI** for interactive use
- **Qdrant Vector Store** for semantic search
- **Document Ingestion Pipeline** for PDF/DOCX processing
- **Modular Architecture** for easy extension

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/vector.git
cd vector

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install package
pip install -e .
```

### Start the Server

```bash
# Start unified server (API + UI)
vector-api
```

### Access

- **Web UI**: http://localhost:8000/ui
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## 📚 Architecture

### Directory Structure

```
vector/
├── api/                    # FastAPI REST endpoints
│   ├── app.py             # Main FastAPI app (mounts Gradio at /ui)
│   ├── deps.py            # Dependency injection
│   ├── schemas.py         # Pydantic models
│   └── routers/
│       ├── vectorstore.py # Collection/document CRUD
│       ├── ingestion.py   # File upload & processing
│       └── retrieval.py   # Semantic search
│
├── ui/                    # Gradio web interface
│   ├── app.py            # Gradio app factory
│   ├── service.py        # VectorWebService
│   ├── components.py     # UI components
│   └── handlers.py       # Event handlers
│
├── retrieval/            # RAG pipeline (NEW!)
│   ├── pipeline.py       # Pluggable orchestration
│   └── steps.py          # Search, filter, expand steps
│
├── stores/               # Vector store backends
│   ├── base.py          # Abstract interface
│   ├── qdrant.py        # Qdrant implementation
│   └── factory.py       # Store factory
│
├── search/              # Search service layer
│   ├── service.py       # SearchService
│   ├── dsl.py           # Provider-agnostic DSL
│   └── utils.py         # Utilities (chunk windows)
│
├── pipeline/            # Document ingestion
│   ├── ingestion.py     # IngestionPipeline
│   ├── converter.py     # Document conversion (Docling)
│   ├── chunker.py       # Text chunking
│   └── docling_adapter.py
│
├── embedders/           # Text embedding models
│   └── sentence_transformer.py
│
├── ai/                  # AI model providers
│   ├── base.py
│   ├── openai.py
│   └── factory.py
│
├── agent/              # Chat agent (optional, deprecated path)
│   ├── pipeline.py     # Re-exports from retrieval/
│   ├── steps.py        # Re-exports from retrieval/
│   └── ...
│
└── models.py           # Core domain models
```

---

## 🔧 CLI Commands

```bash
# Main commands
vector-api          # Start FastAPI + Gradio UI (port 8000)
vector-ui           # Start standalone Gradio UI (port 7860)
vector-core         # Core CLI utilities
vector-agent        # Agent CLI (deprecated, use retrieval)

# Development
uvicorn vector.api.app:app --reload    # Auto-reload on changes
```

---

## 🌐 API Endpoints

### VectorStore (`/vectorstore`)
- `GET /collections` - List all collections
- `POST /collections` - Create a collection
- `DELETE /collections/{name}` - Delete a collection
- `POST /points` - Upsert a point
- `GET /documents` - List documents
- `DELETE /documents/{id}` - Delete document

### Ingestion (`/ingestion`)
- `POST /ingest` - Upload and ingest document
  - Supports: PDF, DOCX, TXT, JSON
  - Returns: Statistics (chunks, artifacts, duration)

### Retrieval (`/retrieval`)
- `POST /search` - Semantic search (JSON body)
- `GET /search` - Semantic search (query params)
- `GET /context/{chunk_id}` - Get surrounding chunks

### System
- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc
- `GET /ui` - Gradio web interface

---

## 💻 Usage Examples

### Python API Client

```python
import httpx

# Search documents
response = httpx.post(
    "http://localhost:8000/retrieval/search",
    json={
        "query": "zoning requirements for commercial buildings",
        "top_k": 10,
        "window": 2  # Include surrounding chunks
    }
)

results = response.json()
for result in results['results']:
    print(f"{result['score']:.3f}: {result['text'][:100]}")
```

### Document Ingestion

```python
# Upload and ingest a document
with open("document.pdf", "rb") as f:
    response = httpx.post(
        "http://localhost:8000/ingestion/ingest",
        files={"file": ("document.pdf", f, "application/pdf")},
        data={"document_id": "my_doc_001"}
    )

result = response.json()
print(f"Indexed {result['chunks_indexed']} chunks in {result['duration_seconds']:.2f}s")
```

### Retrieval Pipeline (Programmatic)

```python
from vector.retrieval import Pipeline, SearchStep, ScoreFilter, DiagnosticsStep
from vector.search.service import SearchService
from vector.stores.factory import create_store
from vector.embedders.sentence_transformer import SentenceTransformerEmbedder

# Setup
embedder = SentenceTransformerEmbedder()
store = create_store("qdrant", db_path="./qdrant_db")
search_service = SearchService(embedder, store)

# Build pipeline
pipeline = Pipeline()
pipeline.add_step(SearchStep(search_service, top_k=20))
pipeline.add_step(ScoreFilter(min_score=0.6))
pipeline.add_step(DiagnosticsStep())

# Run retrieval
from vector.retrieval import RetrievalContext
from vector.agent.models import ChatSession

session = ChatSession(id="test", system_prompt="")
context = RetrievalContext(session, "user query", "user query")
result = pipeline.run(context)

# Access results
print(f"Found {len(result.results)} results")
print(f"Metadata: {result.metadata}")
```

---

## 🧪 Testing

```bash
# Test API endpoints
python test_api.py

# Test unified server
python test_unified_server.py

# Run unit tests
pytest tests/

# Test imports
python -c "from vector.api import app; print('✓ API works')"
python -c "from vector.ui import create_gradio_app; print('✓ UI works')"
```

---

## 📦 Dependencies

Core:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `gradio` - Web UI framework
- `qdrant-client` - Vector database
- `sentence-transformers` - Embeddings
- `docling` - Document conversion
- `pydantic` - Data validation
- `pydantic-ai` - AI framework

Optional:
- `openai` - OpenAI models
- `httpx` - HTTP client
- `pytest` - Testing

---

## 🔑 Configuration

Create `config.yaml` in project root:

```yaml
ai_models:
  search:
    name: gpt-3.5-turbo
    max_tokens: 4000
    temperature: 0.7
    provider: openai
  answer:
    name: gpt-4
    max_tokens: 15000
    temperature: 0.7
    provider: openai

vector_database:
  local_path: ./qdrant_db

storage:
  converted_documents_dir: ./data/converted_documents
  registry_dir: ./vector_registry
```

Set environment variables:

```bash
# .env file
OPENAI_API_KEY=sk-...
VECTOR_STORE_PROVIDER=qdrant
```

---

## 🚢 Deployment

### Development
```bash
uvicorn vector.api.app:app --reload --port 8000
```

### Production

**Option 1: Uvicorn (Single Worker)**
```bash
uvicorn vector.api.app:app --host 0.0.0.0 --port 8000 --workers 1
```

**Note:** Use only 1 worker when mounting Gradio (event system requires sticky sessions).

**Option 2: Docker**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "vector.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t vector-api .
docker run -p 8000:8000 -v ./qdrant_db:/app/qdrant_db vector-api
```

**Option 3: Docker Compose**

```yaml
version: '3.8'
services:
  vector-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./qdrant_db:/app/qdrant_db
      - ./data:/app/data
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

---

## 📖 Documentation

- **[FASTAPI_IMPLEMENTATION_COMPLETE.md](FASTAPI_IMPLEMENTATION_COMPLETE.md)** - FastAPI setup
- **[FASTAPI_GRADIO_MIGRATION_COMPLETE.md](FASTAPI_GRADIO_MIGRATION_COMPLETE.md)** - Gradio migration
- **[vector/retrieval/RETRIEVAL_GUIDE.md](vector/retrieval/RETRIEVAL_GUIDE.md)** - Pipeline guide
- **API Docs**: http://localhost:8000/docs (when server is running)

---

## 🎓 Key Concepts

### 1. Retrieval Pipeline
Composable steps for RAG:
- Query expansion
- Vector search
- Score filtering
- Diagnostics

### 2. Dependency Injection
Singleton pattern in `vector/api/deps.py`:
- Config, Store, Embedder, SearchService, IngestionPipeline

### 3. Unified Server
FastAPI mounts Gradio at `/ui`:
- Single server, two interfaces
- Shared resources, better performance

---

## 🔄 Migration Notes

### From `vector.agent` to `vector.retrieval`
```python
# Old (still works via re-export)
from vector.agent.pipeline import Pipeline, SearchStep

# New (recommended)
from vector.retrieval import Pipeline, SearchStep
```

### Removed Directories
- `apps/gradio/` - Duplicate with broken imports
- `vector/web/` - Duplicate of `vector/ui/`

---

## 🆘 Troubleshooting

**Import Error:**
```bash
# Reinstall in editable mode
pip install -e .
```

**Port Already in Use:**
```bash
# Use different port
uvicorn vector.api.app:app --port 8001
```

**Gradio Not Mounting:**
```bash
# Check gradio is installed
pip install gradio

# Check imports
python -c "from vector.ui import create_gradio_app"
```

---

## 📞 Support

- **Issues**: https://github.com/yourusername/vector/issues
- **Docs**: http://localhost:8000/docs

---

## 🎉 Summary

**What You Have:**
- ✅ Production-ready REST API
- ✅ Interactive Gradio UI
- ✅ Unified deployment
- ✅ Clean architecture
- ✅ Modular & extensible
- ✅ Well documented

**Start using:**
```bash
vector-api
# Then visit: http://localhost:8000/ui
```

Enjoy! 🚀
