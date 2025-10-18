"""Context building orchestration layer.

This module provides mid-level context building orchestration between the low-level
search infrastructure (vector/search/) and high-level application logic.

Context building pipelines can include both AI-powered operations (agents) 
and pure retrieval operations to prepare context for chat responses.

Components:
- ContextPipeline: Pluggable step execution framework
- ContextStep: Abstract base for custom steps
- ContextBuildResult: Shared state across pipeline
- ContextOrchestrator: High-level context building coordination
- Steps: Query expansion (AI), search, filtering, diagnostics

Example - Direct Pipeline Usage:
    >>> from vector.context import ContextPipeline, SearchStep, ScoreFilter
    >>> from vector.search.service import SearchService
    >>> 
    >>> search_service = SearchService(embedder, store)
    >>> 
    >>> pipeline = ContextPipeline()
    >>> pipeline.add_step(SearchStep(search_service, top_k=12))
    >>> pipeline.add_step(ScoreFilter(min_score=0.5))
    >>> 
    >>> context = ContextBuildResult(session, message, query)
    >>> result = pipeline.run(context)

Example - Orchestrator Usage:
    >>> from vector.context import ContextOrchestrator
    >>> 
    >>> orchestrator = ContextOrchestrator(
    ...     search_model=ai_model,
    ...     search_service=search_service
    ... )
    >>> 
    >>> bundle, metrics = orchestrator.build_context(
    ...     session=session,
    ...     user_message="zoning requirements",
    ...     top_k=12
    ... )
"""

# Import pipeline components first (no dependencies)
from .pipeline import ContextPipeline, ContextStep, ContextBuildResult

# Then import steps (depends on pipeline)
from .steps import QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep

# Finally import orchestrator (depends on everything)
from .orchestrator import ContextOrchestrator, RetrievalOrchestrator, Retriever

__all__ = [
    # Pipeline framework
    "ContextPipeline",
    "ContextStep",
    "ContextBuildResult",
    
    # Pipeline steps
    "QueryExpansionStep",
    "SearchStep",
    "ScoreFilter",
    "DiagnosticsStep",
    
    # Orchestration
    "ContextOrchestrator",
    
    # Backward compatibility aliases
    "RetrievalOrchestrator",
    "Retriever",
    "Pipeline",  # Alias for ContextPipeline
    "PipelineStep",  # Alias for ContextStep
    "RetrievalContext",  # Alias for ContextBuildResult
]

# Add backward compatibility aliases
Pipeline = ContextPipeline
PipelineStep = ContextStep
RetrievalContext = ContextBuildResult
