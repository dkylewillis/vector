# Context Building Architecture

## Layer Dependencies

```
┌─────────────────────────────────────────────────────┐
│                    vector.ui                         │
│  ┌──────────────────────────────────────────────┐  │
│  │ • Session Management                         │  │
│  │ • Conversation History                       │  │
│  │ • User Interface (Gradio)                    │  │
│  │ • Orchestrates context building + chat       │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│                 vector.agent                         │
│  ┌──────────────────────────────────────────────┐  │
│  │ • ChatService (stateless chat)               │  │
│  │ • PydanticAI Agents                          │  │
│  │ • Response Generation                        │  │
│  │ • Prompting Utilities                        │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│                vector.context                        │
│  ┌──────────────────────────────────────────────┐  │
│  │ Context Building Pipelines                   │  │
│  │ ├─ QueryExpansionStep (AI-powered)          │  │
│  │ ├─ SearchStep (pure retrieval)              │  │
│  │ ├─ ScoreFilter (filtering)                  │  │
│  │ └─ DiagnosticsStep (metadata)               │  │
│  │                                               │  │
│  │ • ContextPipeline (executor)                 │  │
│  │ • ContextOrchestrator (high-level)           │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│           vector.search / vector.stores              │
│  ┌──────────────────────────────────────────────┐  │
│  │ • SearchService (vector search)              │  │
│  │ • VectorStore (Qdrant)                       │  │
│  │ • Embedders                                   │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Context Building Flow

```
User Message
     │
     ↓
┌────────────────────────────────────┐
│  UI Layer (vector.ui.service)     │
│  • Get/create session              │
│  • Load conversation history       │
└────────────────┬───────────────────┘
                 │
                 ↓
┌────────────────────────────────────┐
│  Context Builder                   │
│  (vector.context.ContextOrchestrator) │
│                                    │
│  1. QueryExpansionStep             │
│     └─ Uses AI to enhance query    │
│                                    │
│  2. SearchStep                     │
│     └─ Vector similarity search    │
│                                    │
│  3. ScoreFilter                    │
│     └─ Filter by threshold         │
│                                    │
│  4. DiagnosticsStep                │
│     └─ Add metadata                │
└────────────────┬───────────────────┘
                 │
                 ↓
          ContextBuildResult
          (query, results, metadata)
                 │
                 ↓
┌────────────────────────────────────┐
│  Chat Generator                    │
│  (vector.agent.chat_service)       │
│  • Build prompt with context       │
│  • Generate response               │
│  • Track usage metrics             │
└────────────────┬───────────────────┘
                 │
                 ↓
┌────────────────────────────────────┐
│  UI Layer                          │
│  • Update session history          │
│  • Display response to user        │
│  • Show diagnostics                │
└────────────────────────────────────┘
```

## Key Concepts

### Context Building
**Purpose:** Gather relevant information for answering a question

**Can include:**
- AI operations (query expansion, reranking)
- Pure retrieval (vector search, filtering)
- Enrichment (metadata, diagnostics)

**Result:** `ContextBuildResult` with query, results, and metadata

### Chat Generation
**Purpose:** Generate a response using the built context

**Process:**
- Takes context + conversation history
- Builds prompt
- Calls LLM
- Returns response

**Result:** Chat message with usage metrics

### Session Management
**Purpose:** Track conversation state over multiple turns

**Handled by:** UI layer (`vector.ui.service`)

**State:**
- Message history
- User preferences
- Session metadata

## Why This Structure?

### 1. Separation of Concerns
- **Context building** = Information gathering
- **Chat generation** = Response creation
- **Session management** = State tracking

### 2. Flexibility
- Can build context without generating response
- Can use different context building strategies
- Can swap out components independently

### 3. Testability
- Each layer can be tested independently
- Mock dependencies easily
- Clear interfaces

### 4. Industry Standard
This matches patterns from:
- **LangChain:** Retrievers + Chains
- **LlamaIndex:** Query Engines + Response Synthesizers
- **Haystack:** Pipelines + Nodes

### 5. No Circular Dependencies
```
ui → agent → context → search
```
Clean one-way dependency flow.

## Example: Custom Context Builder

```python
from vector.context import ContextPipeline, ContextStep, ContextBuildResult
from vector.agent.models import RetrievalResult

class CustomFilter(ContextStep):
    """Custom filtering step."""
    
    def __call__(self, context: ContextBuildResult) -> ContextBuildResult:
        # Filter results by custom logic
        context.results = [
            r for r in context.results 
            if "important" in r.text.lower()
        ]
        return context

# Build custom pipeline
pipeline = ContextPipeline()
pipeline.add_step(QueryExpansionStep(ai_model))
pipeline.add_step(SearchStep(search_service, top_k=20))
pipeline.add_step(CustomFilter())  # Your custom step
pipeline.add_step(ScoreFilter(min_score=0.7))
pipeline.add_step(DiagnosticsStep())

# Use it
orchestrator = ContextOrchestrator(ai_model, search_service)
bundle, metrics = orchestrator.build_context(
    session=session,
    user_message="important regulations",
    pipeline=pipeline  # Use custom pipeline
)
```

## Migration from Old Code

### Before (vector.retrieval)
```python
from vector.retrieval import RetrievalOrchestrator

orchestrator = RetrievalOrchestrator(model, service)
bundle, metrics = orchestrator.retrieve(session, message)
```

### After (vector.context)
```python
from vector.context import ContextOrchestrator

orchestrator = ContextOrchestrator(model, service)
bundle, metrics = orchestrator.build_context(session, message)
```

### Backward Compatible
```python
# Both still work!
from vector.retrieval import RetrievalOrchestrator  # → ContextOrchestrator
from vector.agent import Retriever  # → ContextOrchestrator
```

---

**This architecture makes it clear:** We're building context (which may use agents) to support chat, not doing retrieval in isolation.
