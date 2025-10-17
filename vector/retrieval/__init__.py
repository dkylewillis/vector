"""Retrieval pipeline module.

Provides composable RAG orchestration separate from chat agent logic.

Key Components:
- Pipeline: Orchestrates retrieval steps
- PipelineStep: Abstract base for custom steps
- RetrievalContext: Shared state across pipeline

Ready-to-use Steps:
- QueryExpansionStep: Expand queries with AI
- SearchStep: Vector similarity search
- ScoreFilter: Filter by score threshold
- DiagnosticsStep: Add metadata

Example:
    >>> from vector.retrieval import Pipeline, SearchStep, ScoreFilter, DiagnosticsStep
    >>> from vector.search.service import SearchService
    >>> 
    >>> search_service = SearchService(embedder, store)
    >>> 
    >>> pipeline = Pipeline()
    >>> pipeline.add_step(SearchStep(search_service, top_k=12))
    >>> pipeline.add_step(ScoreFilter(min_score=0.5))
    >>> pipeline.add_step(DiagnosticsStep())
    >>> 
    >>> context = RetrievalContext(session, message, query)
    >>> result = pipeline.run(context)
"""

from .pipeline import Pipeline, PipelineStep, RetrievalContext
from .steps import QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep

__all__ = [
    # Core components
    "Pipeline",
    "PipelineStep",
    "RetrievalContext",
    # Concrete steps
    "QueryExpansionStep",
    "SearchStep",
    "ScoreFilter",
    "DiagnosticsStep",
]
