"""Context building orchestration using pluggable pipelines.

This module provides high-level context building coordination that combines
search infrastructure with AI-powered query expansion and result filtering.
"""

from typing import Optional, List, Tuple
from vector.search.service import SearchService
from vector.agent.models import ChatSession, RetrievalBundle, AggregatedUsageMetrics
from .pipeline import ContextPipeline, ContextBuildResult
from .steps import QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep


class ContextOrchestrator:
    """Orchestrates context building using configurable pipelines.
    
    This class provides a flexible framework for building context workflows
    by composing pipeline steps. It handles query expansion, vector search,
    filtering, and result aggregation.
    
    Example:
        >>> from vector.context import ContextOrchestrator
        >>> from vector.search import SearchService
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
    
    def __init__(self, search_model, search_service: SearchService):
        """Initialize the orchestrator.
        
        Args:
            search_model: Optional AI model for query expansion (or None)
            search_service: SearchService instance for document retrieval
        """
        self.search_model = search_model
        self.search_service = search_service
    
    def build_context(
        self,
        session: ChatSession,
        user_message: str,
        top_k: int = 12,
        document_ids: Optional[List[str]] = None,
        window: int = 0,
        min_score: Optional[float] = None,
        pipeline: Optional[ContextPipeline] = None
    ) -> Tuple[RetrievalBundle, AggregatedUsageMetrics]:
        """Build context using pipeline.
        
        Args:
            session: Current chat session with conversation history
            user_message: User's current message/query
            top_k: Number of results to retrieve
            document_ids: Optional list of document IDs to filter by
            window: Number of surrounding chunks to include (0 = disabled)
            min_score: Optional minimum similarity score threshold
            pipeline: Optional custom pipeline (uses default if None)
            
        Returns:
            Tuple of (retrieval_bundle, aggregated_usage_metrics)
            
        Example:
            >>> # Basic context building
            >>> bundle, metrics = orchestrator.build_context(
            ...     session=session,
            ...     user_message="height limits",
            ...     top_k=10
            ... )
            >>> 
            >>> # With filtering and context
            >>> bundle, metrics = orchestrator.build_context(
            ...     session=session,
            ...     user_message="setback requirements",
            ...     document_ids=["doc_123"],
            ...     min_score=0.5,
            ...     window=2
            ... )
        """
        # Use custom or build default pipeline
        if pipeline:
            execution_pipeline = pipeline
        else:
            execution_pipeline = self.build_default_pipeline(
                top_k=top_k,
                document_ids=document_ids,
                window=window,
                min_score=min_score
            )
        
        # Create initial context
        context = ContextBuildResult(
            session=session,
            user_message=user_message,
            query=user_message
        )
        
        # Execute pipeline
        context = execution_pipeline.run(context)
        
        # Build retrieval bundle from results
        bundle = RetrievalBundle(
            original_query=user_message,
            expanded_query=context.metadata.get("expanded_query", user_message),
            keyphrases=context.metadata.get("keyphrases", []),
            results=context.results,
            diagnostics=context.metadata
        )
        
        # Aggregate usage metrics
        if context.usage_metrics:
            metrics = AggregatedUsageMetrics.from_operations(context.usage_metrics)
            return bundle, metrics
        else:
            return bundle, AggregatedUsageMetrics()
    
    def build_default_pipeline(
        self,
        top_k: int = 12,
        document_ids: Optional[List[str]] = None,
        window: int = 0,
        min_score: Optional[float] = None
    ) -> ContextPipeline:
        """Build default context building pipeline.
        
        The default pipeline includes:
        1. Query expansion (if AI model available)
        2. Vector similarity search
        3. Score filtering (if min_score specified)
        4. Diagnostics and metadata
        
        Args:
            top_k: Number of results to retrieve
            document_ids: Optional document filter
            window: Chunk window size for context
            min_score: Optional score threshold
            
        Returns:
            Configured pipeline ready for execution
        """
        pipeline = ContextPipeline()
        
        # Step 1: Query expansion
        pipeline.add_step(QueryExpansionStep(self.search_model))
        
        # Step 2: Vector search
        pipeline.add_step(SearchStep(
            self.search_service,
            top_k=top_k,
            document_ids=document_ids,
            window=window
        ))
        
        # Step 3: Optional filtering
        if min_score is not None:
            pipeline.add_step(ScoreFilter(min_score))
        
        # Step 4: Diagnostics
        pipeline.add_step(DiagnosticsStep())
        
        return pipeline


# Backward compatibility aliases
RetrievalOrchestrator = ContextOrchestrator
Retriever = ContextOrchestrator
