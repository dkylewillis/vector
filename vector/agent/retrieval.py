"""Retrieval orchestration using pluggable pipeline."""

from typing import Optional, List, Tuple
from ..core.services.search import SearchService
from .models import ChatSession, RetrievalBundle, UsageMetrics, AggregatedUsageMetrics
from .pipeline import Pipeline, RetrievalContext
from .steps import QueryExpansionStep, SearchStep, ScoreFilter, DiagnosticsStep


class Retriever:
    """Orchestrates retrieval using a pluggable pipeline."""
    
    def __init__(self, search_model, search_service: SearchService):
        """Initialize the retriever.
        
        Args:
            search_model: Optional AI model for query expansion (or None)
            search_service: SearchService instance for document retrieval
        """
        self.search_model = search_model
        self.search_service = search_service
    
    def retrieve(
        self,
        session: ChatSession,
        user_message: str,
        top_k: int = 12,
        search_type: str = "both",
        document_ids: Optional[List[str]] = None,
        window: int = 0,
        min_score: Optional[float] = None,
        custom_pipeline: Optional[Pipeline] = None
    ) -> Tuple[RetrievalBundle, AggregatedUsageMetrics]:
        """Perform retrieval using pipeline.
        
        Args:
            session: Current chat session
            user_message: User's current message
            top_k: Number of results to retrieve
            search_type: Type of search ('chunks', 'artifacts', or 'both')
            document_ids: Optional list of document IDs to filter
            window: Number of surrounding chunks to include (0 = disabled)
            min_score: Optional minimum score threshold for filtering
            custom_pipeline: Optional custom pipeline (uses default if None)
            
        Returns:
            Tuple of (retrieval_bundle, aggregated_usage_metrics)
        """
        # Use custom or build default pipeline
        if custom_pipeline:
            pipeline = custom_pipeline
        else:
            pipeline = self._build_pipeline(
                top_k=top_k,
                search_type=search_type,
                document_ids=document_ids,
                window=window,
                min_score=min_score
            )
        
        # Create initial context
        context = RetrievalContext(
            session=session,
            user_message=user_message,
            query=user_message
        )
        
        # Execute pipeline
        context = pipeline.run(context)
        
        # Build retrieval bundle
        retrieval_bundle = RetrievalBundle(
            original_query=user_message,
            expanded_query=context.metadata.get("expanded_query", user_message),
            keyphrases=context.metadata.get("keyphrases", []),
            results=context.results,
            diagnostics=context.metadata
        )
        
        # Aggregate usage metrics and preserve for breakdown
        if context.usage_metrics:
            # Create aggregated metrics from pipeline operations
            aggregated = AggregatedUsageMetrics.from_operations(context.usage_metrics)
            # Return as aggregated to preserve breakdown
            return retrieval_bundle, aggregated
        else:
            # Return empty aggregated metrics
            return retrieval_bundle, AggregatedUsageMetrics()
    
    def _build_pipeline(
        self,
        top_k: int = 12,
        search_type: str = "both",
        document_ids: Optional[List[str]] = None,
        window: int = 0,
        min_score: Optional[float] = None
    ) -> Pipeline:
        """Build default retrieval pipeline.
        
        Args:
            top_k: Number of results to retrieve
            search_type: Type of search
            document_ids: Optional document filter
            window: Chunk window size
            min_score: Optional score threshold
            
        Returns:
            Configured pipeline
        """
        pipeline = Pipeline()
        
        # Add query expansion step
        pipeline.add_step(QueryExpansionStep(self.search_model))
        
        # Add search step
        pipeline.add_step(SearchStep(
            self.search_service,
            top_k=top_k,
            search_type=search_type,
            document_ids=document_ids,
            window=window
        ))
        
        # Add optional score filter
        if min_score is not None:
            pipeline.add_step(ScoreFilter(min_score))
        
        # Add diagnostics step
        pipeline.add_step(DiagnosticsStep())
        
        return pipeline
