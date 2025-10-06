# Vector

## About

Vector is a document research application that implements a Retrieval-Augmented Generation (RAG) pipeline to provide grounded context to large language models (LLMs). It uses IBM's open‑source Docling library to parse source files into structured Docling Document objects (Pydantic models) that preserve hierarchy (pages, sections, tables, figures) alongside clean text. After parsing, text is segmented with Docling's hybrid chunker, and both chunks and extracted artifacts (e.g., tables, figures) are embedded using Sentence Transformers and stored in a Qdrant vector database. Vector supplies both a command-line interface (CLI) and a Gradio web application for ingesting documents, performing semantic search, AI-assisted Q&A, and managing document lifecycle operations.

Vector is currently an early-stage proof of concept; I plan to refine it and continue adding features. 


## Goals

- Accelerate research by enabling users to query one or many documents and receive AI‑assisted, source‑grounded summaries.
- Remain LLM‑agnostic so embedding and generation models can be swapped through configuration.
- Provide transparent, tunable behavior by exposing configurable system and user prompt templates.

## Vector Web Interface

The Vector Web Interface provides a user-friendly Gradio-based web application for document processing, search, and management.

### Starting the Web Interface

The web interface is available after installing the package:

```bash
# Install the package in development mode
pip install -e .

# Configure environment (copy example and add your key)
copy .env.example .env   # Windows PowerShell / CMD
# or (PowerShell alternative)
Copy-Item .env.example .env

# Edit .env and set:
# OPENAI_API_KEY=sk-...your key...

# Start the web interface (Method 1 - using entry point)
vector-web

# Start the web interface (Method 2 - using module)
python -m vector.web

# Start the web interface (Method 3 - using standalone script)
python vector_web.py
```

## Concepts

Vector is split into two cooperating layers:

1. Core (deterministic document processing & storage)
2. Agent (AI-assisted retrieval, reasoning, and interaction)

This separation keeps ingestion repeatable and transparent, while allowing flexible AI behavior on top of a stable data substrate.

## Vector-Core
The Core layer is responsible for turning raw source files into structured, queryable vector data plus a registry of document metadata.

### Responsibilities
- File conversion (multi-format) using Docling (`DocumentConverter`)
- Hybrid structural + token-based chunking (`DocumentChunker` / Docling HybridChunker)
- Artifact extraction (tables, figures, images) and association with referencing chunks
- Text & artifact contextualization (adds headings and surrounding structure)
- Embedding generation via Sentence Transformers (default: `sentence-transformers/all-MiniLM-L6-v2`)
- Vector insertion into Qdrant collections (default collections: `chunks`, `artifacts`)
- Persistent storage of:
	- Converted document JSON (with embedded image refs)
	- Artifact images & thumbnails (`artifacts/` subdirectory)
	- Registry records (document id, display name, counts, tags, collection names)
- Safe deletion of documents (vectors + files + registry cleanup)

### Processing Pipeline (High-Level Flow)

After conversion, the pipeline performs two complementary passes: (1) chunk extraction using Docling's Hybrid Chunker, which produces contextualized text segments while preserving a list of referenced document item `self_ref` identifiers (tables, pictures, etc.) so those relationships can be embedded as payload metadata; (2) an artifact extraction pass over the full Docling document that materializes each referenced figure/table as a PNG image, builds an `Artifact` object (caption, headings, before/after surrounding text), and records the image and thumbnail file paths. Each artifact's path is then linked back onto any chunk that referenced it, enabling either chunk‑centric or artifact‑centric retrieval strategies. Both representations are intentionally retained—even if partially redundant—to compare strengths and weaknesses (rich narrative context vs. focused structured visual context). The remaining steps embed chunks and artifacts, upsert vectors into their respective Qdrant collections, and register document metadata in the registry.


![pipeline.run()](./core-pipeline.png)

### Key Components
- `DocumentConverter`: Normalizes multiple formats (PDF, DOCX, PPTX, HTML, MD, CSV, images, Docling JSON) and optionally uses a VLM pipeline for richer artifact image generation.
- `DocumentChunker`: Applies a hybrid approach (hierarchical + token-aware) with a custom serializer to mark image placeholders, ensuring chunk text keeps structural cues.
- `Embedder`: Wraps Sentence Transformers for batch embedding; exposes embedding dimension.
- `VectorStore`: Thin Qdrant abstraction (create/list/insert/search/delete + document filtering).
- `VectorPipeline`: Orchestrates end‑to‑end ingestion (`run()`), saves converted doc JSON, artifact images, thumbnails, registers the document, embeds & stores vectors, and links artifacts to their referencing chunks.
- `VectorRegistry` (via `document_registry`): Tracks document metadata (ids, names, collections, counts, tags, artifact presence) for later retrieval and deletion.

### Typical Ingestion (Programmatic)
```python
from vector.core.pipeline import VectorPipeline

pipeline = VectorPipeline()
document_id = pipeline.run("./data/source_documents/zoning_chapter_14.pdf", tags=["zoning", "setbacks"])
print("Ingested document id:", document_id)
```

### Deletion Semantics
- Removes chunk & artifact vectors (if present)
- Optionally deletes saved JSON + artifact image folder (unless `cleanup_files=False`)
- Removes registry record (atomic intent; logs partial failures)

### Why Dual Collections?
Separating `chunks` (narrative text) and `artifacts` (structured visuals) improves search control. The Agent can:
- Query only text for dense semantic reasoning
- Query only artifacts for tabular or figure-focused questions
- Merge both result sets for comprehensive answers

## Vector-Agent
The Agent layer provides semantic search, multi-source context assembly, AI question answering, and conversational (multi‑turn) sessions over the data prepared by Core.

### Responsibilities
- Query construction & enhancement (expands or reformulates user queries)
- Dual / unified retrieval across chunk & artifact collections
- Relevance ranking & context window assembly
- Prompt construction (system + user templates configurable)
- AI answer generation (provider‑agnostic: OpenAI, Anthropic, local-compatible)
- Multi-turn chat session management (context memory, summarization, pruning)
- Metadata filtering (e.g., by `source`, `filename`, path) before or after vector search
- Response length adaptation (short / medium / long policies)

### Search Modes
- Chunks: Narrative / textual context
- Artifacts: Tables, figures, diagrams (caption + surrounding text synthesized into embedding text)
- Both: Merged result set (often higher recall for complex regulatory queries)

### Chat Session Lifecycle
1. Start session → unique session id
2. User messages accumulate → agent retrieves & augments context
3. Automatic summarization triggers after configured message threshold (prevents token overflow)
4. Rolling recent context + compressed history maintained
5. End session → memory discarded (currently in‑memory only)

## Chat Pipeline
On each chat turn, the raw user message is passed to a query-expansion LLM, producing an optimized semantic search query. Retrieved vectors (chunks + artifacts) are ranked, distilled into context, and injected into a structured prompt (system + history + user intent + sources) sent to the answer-generation LLM.

![Chat Pipeline](./agent-pipeline.png)

### Example CLI Usage
```bash
# One-off semantic search (both chunks & artifacts)
python -m vector.agent search "setback requirements for corner lots" --type both --top-k 12

# Filter by metadata (e.g., only ordinances)
python -m vector.agent search "parking minimums" --filter source=ordinances

# Start a multi-turn chat
python -m vector.agent chat --start
# Use returned session id in subsequent turns
python -m vector.agent chat --session <SESSION_ID> --message "Summarize R-1 height restrictions"
python -m vector.agent chat --session <SESSION_ID> --message "How do they differ for R-2?" --length medium
```

### Response Length Profiles
- Short: Key bullet or sentence summary
- Medium (default): Balanced explanation with citations
- Long: Comprehensive, sectioned answer (useful for memo drafting)

### Provider Agnosticism
Configuration selects model providers per role (search vs answer). This allows lighter / faster models for query expansion and heavier models for answer generation while preserving cost efficiency.

### When to Use Core vs Agent
- Use Core alone for batch ingestion pipelines, exporting structured JSON, or low‑level vector operations.
- Use Agent when you need intent-aware search, enriched prompts, multi-turn dialogue, or automatic context blending of text + artifacts.

## Example Usage Video