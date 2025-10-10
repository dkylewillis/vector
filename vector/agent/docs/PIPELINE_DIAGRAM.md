# Pipeline Architecture Diagram

## File Structure
```
vector/agent/
├── __init__.py           # Module exports
├── agent.py              # Main ResearchAgent class
├── retrieval.py          # Retriever (uses pipeline)
├── pipeline.py           # Pipeline framework (NEW)
├── steps.py              # Concrete pipeline steps (NEW)
├── models.py             # Data models
├── prompting.py          # Prompt templates
├── memory.py             # Session memory management
├── cli.py                # CLI interface
├── README.md             # Main documentation
├── ARCHITECTURE.md       # Architecture details
├── PIPELINE_USAGE.md     # Pipeline usage guide (NEW)
├── PIPELINE_SUMMARY.md   # Implementation summary (NEW)
└── example_pipeline.py   # Working examples (NEW)
```

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ResearchAgent.chat()                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Retriever.retrieve()                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              _build_pipeline()                        │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Pipeline.run()                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  RetrievalContext                                  │    │
│  │  • session: ChatSession                            │    │
│  │  • user_message: str                               │    │
│  │  • query: str (modifiable)                         │    │
│  │  • results: List[RetrievalResult]                  │    │
│  │  • metadata: Dict[str, Any]                        │    │
│  │  • usage_metrics: List[UsageMetrics]               │    │
│  └────────────────────────────────────────────────────┘    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 1: QueryExpansionStep                        │    │
│  │  → Expands query using AI model                    │    │
│  │  → Updates context.query                           │    │
│  │  → Adds context.metadata['keyphrases']            │    │
│  └────────────────────────────────────────────────────┘    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 2: SearchStep                                │    │
│  │  → Performs vector search                          │    │
│  │  → Populates context.results                       │    │
│  │  → Adds context.metadata['search_latency_ms']     │    │
│  └────────────────────────────────────────────────────┘    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 3: ScoreFilter (optional)                    │    │
│  │  → Filters context.results by score                │    │
│  │  → Adds context.metadata['filtered_by_score']     │    │
│  └────────────────────────────────────────────────────┘    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 4: DiagnosticsStep                           │    │
│  │  → Adds result counts and breakdowns               │    │
│  │  → Adds context.metadata['results_by_type']       │    │
│  └────────────────────────────────────────────────────┘    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Final RetrievalContext                            │    │
│  │  • Expanded query                                  │    │
│  │  • Filtered results                                │    │
│  │  • Complete metadata                               │    │
│  │  • Aggregated metrics                              │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    RetrievalBundle                          │
│  • original_query                                           │
│  • expanded_query                                           │
│  • keyphrases                                               │
│  • results                                                  │
│  • diagnostics (metadata)                                   │
└─────────────────────────────────────────────────────────────┘
```

## Custom Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Retriever.retrieve()                       │
│                                                              │
│  custom_pipeline = Pipeline()                               │
│      .add_step(QueryExpansionStep(model))                   │
│      .add_step(SearchStep(service, top_k=20))               │
│      .add_step(MyCustomStep())  ◄── Your custom logic      │
│      .add_step(DiagnosticsStep())                           │
│                                                              │
│  context = pipeline.run(context)                            │
└─────────────────────────────────────────────────────────────┘
```

## Step Interface

```python
class PipelineStep(ABC):
    """Simple interface: just implement __call__"""
    
    @abstractmethod
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        """
        Process context and return modified context.
        
        You can:
        - Modify context.query
        - Filter/rerank context.results
        - Add context.metadata
        - Track context.usage_metrics
        """
        pass
```

## Example Custom Step

```python
class DiversityReranker(PipelineStep):
    """Promote document diversity in results."""
    
    def __init__(self, diversity_weight: float = 0.3):
        self.diversity_weight = diversity_weight
    
    def __call__(self, context: RetrievalContext) -> RetrievalContext:
        # Track document frequency
        doc_counts = {}
        reranked = []
        
        for result in sorted(context.results, key=lambda r: r.score, reverse=True):
            doc_counts[result.doc_id] = doc_counts.get(result.doc_id, 0) + 1
            
            # Apply diversity penalty
            penalty = doc_counts[result.doc_id] * self.diversity_weight
            adjusted_score = result.score * (1 - penalty)
            
            reranked.append((result, adjusted_score))
        
        # Sort by adjusted score
        reranked.sort(key=lambda x: x[1], reverse=True)
        context.results = [r for r, _ in reranked]
        
        # Add metadata
        context.add_metadata("reranked_for_diversity", True)
        
        return context
```

## Benefits

✅ **Simple** - Just ~150 lines of core framework code  
✅ **Flexible** - Add/remove/reorder steps easily  
✅ **Testable** - Test each step independently  
✅ **Extensible** - Create custom steps in minutes  
✅ **Clear** - Easy to understand execution flow  
✅ **Backward Compatible** - Existing code still works  

## Usage

```python
# Default pipeline (automatic)
bundle, metrics = retriever.retrieve(session, message)

# With score filtering
bundle, metrics = retriever.retrieve(session, message, min_score=0.4)

# Custom pipeline
pipeline = Pipeline()
pipeline.add_step(QueryExpansionStep(model))
pipeline.add_step(SearchStep(service, top_k=20))
pipeline.add_step(MyCustomStep())
pipeline.add_step(DiagnosticsStep())

bundle, metrics = retriever.retrieve(
    session, message,
    custom_pipeline=pipeline
)
```
