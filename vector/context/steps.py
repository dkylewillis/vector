"""Context building pipeline steps.

Provides ready-to-use pipeline steps for building context:
- QueryExpansionStep: Expand queries using AI and conversation context
- SearchStep: Vector similarity search on chunks
- ScoreFilter: Filter results by minimum similarity score
- DiagnosticsStep: Add diagnostic metadata

Context building can include both AI-powered operations (agents) and 
pure retrieval operations.
"""

import time
from typing import Optional, List

from .pipeline import ContextStep, ContextBuildResult
from vector.agent.models import UsageMetrics, RetrievalResult
from vector.agent.prompting import build_expansion_prompt, render_recent_messages
from vector.search.service import SearchService


class QueryExpansionStep(ContextStep):
    """Expands query using conversation context and AI model.
    
    This is an AI-powered context building step that enhances
    the user's query before retrieval.
    
    Example:
        >>> from vector.context import QueryExpansionStep
        >>> from vector.ai.factory import create_model
        >>> 
        >>> ai_model = create_model("openai", model_name="gpt-3.5-turbo")
        >>> step = QueryExpansionStep(ai_model)
    """
    
    def __init__(self, ai_model):
        """Initialize query expansion step.
        
        Args:
            ai_model: AI model for query expansion (or None to skip expansion)
        """
        self.ai_model = ai_model
    
    def __call__(self, context: ContextBuildResult) -> ContextBuildResult:
        """Expand query using conversation history.
        
        Args:
            context: Current context
            
        Returns:
            Context with expanded query
        """
        if not self.ai_model:
            context.add_metadata("query_expanded", False)
            return context
        
        # Build expansion context from recent history
        history = render_recent_messages(context.session, limit=6)
        prompt = build_expansion_prompt(history, context.user_message)
        
        try:
            response_text, metrics_dict = self.ai_model.generate_response(
                prompt=prompt,
                system_prompt="You output only comma-separated keyphrases for document retrieval. No explanations.",
                max_tokens=96,
                operation="search"
            )
            
            # Track usage
            context.add_usage(UsageMetrics(**metrics_dict))
            
            # Parse keyphrases
            keyphrases = [kp.strip() for kp in response_text.split(",") if kp.strip()]
            
            # Update query if we got keyphrases
            if keyphrases:
                context.query = ", ".join(keyphrases)
            
            # Store metadata
            context.add_metadata("query_expanded", True)
            context.add_metadata("keyphrases", keyphrases)
            context.add_metadata("expanded_query", context.query)
            
        except Exception as e:
            print(f"Warning: Query expansion failed: {e}")
            context.add_metadata("query_expanded", False)
            context.add_metadata("keyphrases", [])
        
        return context


class SearchStep(ContextStep):
    """Performs vector similarity search to build context.
    
    Uses SearchService to find semantically similar content.
    Optionally includes surrounding chunks for additional context.
    
    Example:
        >>> from vector.context import SearchStep
        >>> from vector.search.service import SearchService
        >>> 
        >>> search_service = SearchService(embedder, store)
        >>> step = SearchStep(search_service, top_k=12, window=2)
    """
    
    def __init__(
        self,
        search_service: SearchService,
        top_k: int = 12,
        document_ids: Optional[List[str]] = None,
        window: int = 0
    ):
        """Initialize search step.
        
        Args:
            search_service: SearchService instance
            top_k: Number of results to retrieve
            document_ids: Optional list of document IDs to filter
            window: Number of surrounding chunks to include
        """
        self.search_service = search_service
        self.top_k = top_k
        self.document_ids = document_ids
        self.window = window
    
    def __call__(self, context: ContextBuildResult) -> ContextBuildResult:
        """Perform vector search.
        
        Args:
            context: Current context
            
        Returns:
            Context with search results
        """
        start_time = time.time()
        
        # Perform search (chunks only)
        search_results = self.search_service.search(
            query=context.query,
            top_k=self.top_k,
            document_ids=self.document_ids,
            window=self.window
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Convert SearchResult to RetrievalResult
        for sr in search_results:
            collection = "chunks"
            context.results.append(RetrievalResult(
                filename=sr.filename,
                doc_id=sr.id,
                type=sr.type,
                score=sr.score,
                text=sr.text,
                collection=collection,
                chunk=sr.chunk,
                artifact=sr.artifact
            ))
        
        # Store metadata
        context.add_metadata("search_latency_ms", round(latency_ms, 2))
        context.add_metadata("window", self.window)
        
        return context


class ScoreFilter(ContextStep):
    """Filters context results by minimum score threshold.
    
    Removes results with similarity scores below the threshold.
    
    Example:
        >>> from vector.context import ScoreFilter
        >>> 
        >>> step = ScoreFilter(min_score=0.5)
    """
    
    def __init__(self, min_score: float = 0.5):
        """Initialize score filter.
        
        Args:
            min_score: Minimum score threshold (0.0 to 1.0)
        """
        self.min_score = min_score
    
    def __call__(self, context: ContextBuildResult) -> ContextBuildResult:
        """Filter results by score.
        
        Args:
            context: Current context
            
        Returns:
            Context with filtered results
        """
        original_count = len(context.results)
        context.results = [r for r in context.results if r.score >= self.min_score]
        filtered_count = original_count - len(context.results)
        
        context.add_metadata("score_threshold", self.min_score)
        context.add_metadata("filtered_by_score", filtered_count)
        
        return context


class DiagnosticsStep(ContextStep):
    """Adds diagnostic metadata about context building.
    
    Enriches context with statistics about the context building operation.
    
    Example:
        >>> from vector.context import DiagnosticsStep
        >>> 
        >>> step = DiagnosticsStep()
    """
    
    def __call__(self, context: ContextBuildResult) -> ContextBuildResult:
        """Add diagnostics to context.
        
        Args:
            context: Current context
            
        Returns:
            Context with diagnostic metadata
        """
        context.add_metadata("result_count", len(context.results))
        
        # Add result breakdown by type
        if context.results:
            type_counts = {}
            for r in context.results:
                type_counts[r.type] = type_counts.get(r.type, 0) + 1
            context.add_metadata("results_by_type", type_counts)
        
        # Add query expansion status
        if "query_expanded" not in context.metadata:
            context.add_metadata("query_expanded", False)
        
        if "keyphrases" in context.metadata:
            context.add_metadata("keyphrase_count", len(context.metadata["keyphrases"]))
        
        return context
